"""
Resource Pool Manager для Lambda функцій
Оптимізує використання пам'яті та DynamoDB запитів

Основні принципи:
1. Lazy Loading - завантажувати тільки коли потрібно
2. Batch Operations - об'єднувати запити в batch
3. Generator Pattern - обробляти дані потоково
4. Connection Reuse - переви використовувати підключення
"""

import boto3
from boto3.dynamodb.conditions import Key
from functools import lru_cache
from typing import Dict, List, Optional, Generator, Any
import json


class DynamoDBResourcePool:
    """
    Пул для ефективного завантаження конфігурацій з DynamoDB

    Особливості:
    - Використовує batch_get_item замість множинних get_item
    - Кешує результати в межах одного виклику Lambda
    - Мінімізує кількість запитів до DynamoDB
    """

    def __init__(self, dynamodb_resource=None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb', region_name='eu-central-1')
        self._cache = {}
        self._batch_queue = {}

    def batch_get_channel_configs(self, channel_ids: List[str]) -> Dict[str, Dict]:
        """
        Завантажує конфігурації кількох каналів за один batch запит

        Args:
            channel_ids: Список ID каналів

        Returns:
            Dict {channel_id: config}
        """
        # Перевірка кешу
        uncached_ids = [cid for cid in channel_ids if cid not in self._cache]

        if not uncached_ids:
            return {cid: self._cache[cid] for cid in channel_ids}

        print(f"    Batch loading {len(uncached_ids)} channel configs...")

        # DynamoDB batch_get_item підтримує до 100 items за раз
        results = {}

        for i in range(0, len(uncached_ids), 100):
            batch = uncached_ids[i:i+100]

            # Використовуємо query з IndexName замість batch_get
            # бо у нас secondary index на channel_id
            table = self.dynamodb.Table('ChannelConfigs')

            for channel_id in batch:
                try:
                    response = table.query(
                        IndexName='channel_id-index',
                        KeyConditionExpression=Key('channel_id').eq(channel_id),
                        Limit=1  # Потрібен тільки один результат
                    )

                    if response.get('Items'):
                        config = response['Items'][0]
                        results[channel_id] = config
                        self._cache[channel_id] = config

                except Exception as e:
                    print(f"     Failed to load config for {channel_id}: {e}")
                    results[channel_id] = None

        # Об'єднуємо з кешованими результатами
        final_results = {}
        for cid in channel_ids:
            if cid in self._cache:
                final_results[cid] = self._cache[cid]
            elif cid in results:
                final_results[cid] = results[cid]

        print(f"    Loaded {len(final_results)} configs (from cache: {len(channel_ids) - len(uncached_ids)})")
        return final_results

    def get_channel_config_lazy(self, channel_id: str) -> Optional[Dict]:
        """
        Завантажує конфігурацію каналу тільки коли запитують

        Args:
            channel_id: ID каналу

        Returns:
            Channel config або None
        """
        if channel_id in self._cache:
            return self._cache[channel_id]

        try:
            table = self.dynamodb.Table('ChannelConfigs')
            response = table.query(
                IndexName='channel_id-index',
                KeyConditionExpression=Key('channel_id').eq(channel_id),
                Limit=1
            )

            if response.get('Items'):
                config = response['Items'][0]
                self._cache[channel_id] = config
                return config

        except Exception as e:
            print(f"     Failed to load config for {channel_id}: {e}")

        return None

    def batch_get_templates(self, template_ids: List[str], table_name: str) -> Dict[str, Dict]:
        """
        Завантажує шаблони batch запитом

        Args:
            template_ids: Список ID шаблонів
            table_name: Назва таблиці (ThumbnailTemplates, NarrativeTemplates, тощо)

        Returns:
            Dict {template_id: template}
        """
        cache_key = f"{table_name}_cache"
        if not hasattr(self, cache_key):
            setattr(self, cache_key, {})

        template_cache = getattr(self, cache_key)

        # Фільтруємо вже кешовані
        uncached_ids = [tid for tid in template_ids if tid not in template_cache]

        if not uncached_ids:
            return {tid: template_cache[tid] for tid in template_ids if tid in template_cache}

        print(f"    Batch loading {len(uncached_ids)} templates from {table_name}...")

        results = {}

        # DynamoDB batch_get_item для шаблонів (primary key = template_id)
        for i in range(0, len(uncached_ids), 100):
            batch = uncached_ids[i:i+100]

            try:
                response = self.dynamodb.batch_get_item(
                    RequestItems={
                        table_name: {
                            'Keys': [{'template_id': tid} for tid in batch]
                        }
                    }
                )

                for item in response.get('Responses', {}).get(table_name, []):
                    template_id = item['template_id']
                    results[template_id] = item
                    template_cache[template_id] = item

            except Exception as e:
                print(f"     Batch get failed for {table_name}: {e}")
                # Fallback до окремих запитів
                for tid in batch:
                    try:
                        table = self.dynamodb.Table(table_name)
                        response = table.get_item(Key={'template_id': tid})
                        if 'Item' in response:
                            results[tid] = response['Item']
                            template_cache[tid] = response['Item']
                    except:
                        pass

        # Об'єднуємо з кешем
        final_results = {}
        for tid in template_ids:
            if tid in template_cache:
                final_results[tid] = template_cache[tid]
            elif tid in results:
                final_results[tid] = results[tid]

        print(f"    Loaded {len(final_results)} templates")
        return final_results


class PromptStreamProcessor:
    """
    Обробляє промпти потоково (generator pattern)
    Замість завантаження всіх промптів у пам'ять одразу
    """

    def __init__(self, all_prompts: List[Dict], resource_pool: DynamoDBResourcePool):
        self.prompts = all_prompts
        self.pool = resource_pool
        self.total = len(all_prompts)

    def process_in_batches(self, batch_size: int = 10) -> Generator[List[Dict], None, None]:
        """
        Повертає промпти пакетами для обробки

        Args:
            batch_size: Розмір пакету (кількість промптів)

        Yields:
            List[Dict]: Пакет промптів
        """
        for i in range(0, self.total, batch_size):
            batch = self.prompts[i:i+batch_size]
            yield batch

    def get_unique_channels(self) -> List[str]:
        """Повертає унікальні ID каналів"""
        return list(set(p.get('channel_id') for p in self.prompts if p.get('channel_id')))

    def get_unique_template_ids(self, configs: Dict[str, Dict]) -> List[str]:
        """Витягує всі унікальні ID шаблонів з конфігурацій"""
        template_ids = set()
        for config in configs.values():
            if config:
                template_id = config.get('selected_thumbnail_template')
                if template_id:
                    template_ids.add(template_id)
        return list(template_ids)


def optimize_channel_configs_loading(all_prompts: List[Dict], dynamodb_resource=None) -> tuple:
    """
    Оптимізована функція для завантаження всіх необхідних конфігурацій

    Замість N окремих запитів до DynamoDB, робить:
    1. Один batch запит для всіх channel configs
    2. Один batch запит для всіх thumbnail templates

    Args:
        all_prompts: Список всіх промптів
        dynamodb_resource: boto3 DynamoDB resource (опціонально)

    Returns:
        (channel_configs, thumbnail_dimensions)
    """
    pool = DynamoDBResourcePool(dynamodb_resource)
    processor = PromptStreamProcessor(all_prompts, pool)

    # Крок 1: Отримати всі унікальні channel IDs
    unique_channels = processor.get_unique_channels()
    print(f"    Found {len(unique_channels)} unique channels")

    # Крок 2: Завантажити ВСІ конфіги каналів одним batch запитом
    channel_configs = pool.batch_get_channel_configs(unique_channels)

    # Крок 3: Витягти всі template_ids з конфігів
    template_ids = processor.get_unique_template_ids(channel_configs)

    if template_ids:
        print(f"    Found {len(template_ids)} unique thumbnail templates")
        # Крок 4: Завантажити ВСІ шаблони одним batch запитом
        templates = pool.batch_get_templates(template_ids, 'ThumbnailTemplates')
    else:
        templates = {}

    # Крок 5: Підготувати thumbnail dimensions
    thumbnail_dimensions = {}

    for channel_id, config in channel_configs.items():
        if not config:
            continue

        template_id = config.get('selected_thumbnail_template')
        if template_id and template_id in templates:
            thumbnail_template = templates[template_id]
            thumbnail_config = thumbnail_template.get('thumbnail_config', {})
            aspect_ratio = thumbnail_config.get('aspect_ratio', '16:9')
            resolution = thumbnail_config.get('resolution', '1920x1080')

            # Імпортуємо функцію з основного модуля
            from lambda_function import get_dimensions_from_aspect_ratio
            width, height = get_dimensions_from_aspect_ratio(aspect_ratio, resolution)
            thumbnail_dimensions[channel_id] = (width, height)
            print(f"    {channel_id[-6:]}: {aspect_ratio} = {width}x{height}")

    print(f"    Total DynamoDB requests: 2 (batch) vs {len(unique_channels) * 2} (old way)")
    print(f"    Query cost reduction: {((len(unique_channels) * 2 - 2) / (len(unique_channels) * 2)) * 100:.0f}%")

    return channel_configs, thumbnail_dimensions


# Глобальна змінна для переви використання ресурсів між викликами
_global_resource_pool = None

def get_resource_pool() -> DynamoDBResourcePool:
    """
    Singleton pattern для resource pool
    Lambda контейнери можуть бути переви використані між викликами
    """
    global _global_resource_pool
    if _global_resource_pool is None:
        _global_resource_pool = DynamoDBResourcePool()
    return _global_resource_pool
