"""
Комплексна перевірка Variant B архітектури
Перевіряє:
1. DynamoDB configs - чи всі канали мають правильні пули
2. Різноманітність архетипів на одному каналі
3. Різниця між жанрами
"""
import boto3
import json
import time
from collections import Counter

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
lambda_client = boto3.client('lambda', region_name='eu-central-1')

def check_dynamodb_pools():
    """Перевірка архетипних пулів у DynamoDB"""
    print("="*80)
    print("1. ПЕРЕВІРКА DYNAMODB - Archetype Pools")
    print("="*80)

    table = dynamodb.Table('ChannelConfigs')
    response = table.scan()
    channels = response.get('Items', [])

    # Group by archetype pool
    pool_groups = {}
    for ch in channels:
        pool = str(ch.get('archetype_pool', []))
        if pool not in pool_groups:
            pool_groups[pool] = []
        pool_groups[pool].append({
            'name': ch.get('channel_name', 'Unknown'),
            'genre': ch.get('genre', 'Unknown')
        })

    print(f"\nВсього каналів: {len(channels)}")
    print(f"Унікальних пулів: {len(pool_groups)}\n")

    for pool, chs in pool_groups.items():
        print(f"\nПул: {pool}")
        print(f"Каналів: {len(chs)}")
        for ch in chs[:3]:  # Show first 3
            print(f"  - {ch['name']} ({ch['genre']})")
        if len(chs) > 3:
            print(f"  ... та ще {len(chs)-3}")

    # Check specific test channels
    print("\n" + "-"*80)
    print("Перевірка тестових каналів:")
    print("-"*80)

    test_channels = [
        'UCLFeJMO2Mbh-bwAQWya4-dw',  # LifeSeeds
        'UC9KUaoTY4vyGGHzCccqHnAA',  # NeuralTales
        'UCaxPNkUMQKqepAp0JbpVrrw'   # HorrorWhisper
    ]

    for ch_id in test_channels:
        response = table.scan(
            FilterExpression='channel_id = :cid',
            ExpressionAttributeValues={':cid': ch_id}
        )
        if response['Items']:
            ch = response['Items'][0]
            print(f"\n{ch.get('channel_name', 'Unknown')}:")
            print(f"  Genre: {ch.get('genre', 'N/A')}")
            print(f"  Pool: {ch.get('archetype_pool', [])}")
            print(f"  Complexity: {ch.get('complexity_level', 5)}")


def test_single_channel_variety():
    """Тест різноманітності на одному каналі"""
    print("\n\n" + "="*80)
    print("2. ТЕСТ РІЗНОМАНІТНОСТІ - Один канал, різні топіки")
    print("="*80)

    # NeuralTales (Sci-Fi) має пул: inversion_of_source, delayed_consequence, reluctant_transformation
    channel_id = 'UC9KUaoTY4vyGGHzCccqHnAA'

    topics = [
        'Колоністи на Марсі знаходять технологію яка покращує життя (VARIETY TEST 1)',
        'Самотній дослідник приймає рішення яке змінить все (VARIETY TEST 2)',
        'Космічна станція отримує сигнал з невідомого джерела (VARIETY TEST 3)',
    ]

    archetypes_used = []

    for i, topic in enumerate(topics, 1):
        print(f"\n[{i}/{len(topics)}] Топік: {topic[:50]}...")

        payload = {
            'topic_text': topic,
            'channel_id': channel_id,
            'user_id': 'c334d862-4031-7097-4207-84856b59d3ed'
        }

        try:
            response = lambda_client.invoke(
                FunctionName='content-narrative',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            result = json.loads(response['Payload'].read())

            if 'errorMessage' in result:
                print(f"  [ERROR] {result['errorMessage']}")
                continue

            nc = result.get('narrative_content', {})
            mech = nc.get('mechanics', {})
            archetype = mech.get('dominant_archetype', 'N/A')

            archetypes_used.append(archetype)
            print(f"  Архетип: {archetype}")
            print(f"  Surface: {mech.get('surface_truth', 'N/A')[:60]}...")

            time.sleep(2)  # Rate limit

        except Exception as e:
            print(f"  [ERROR] {str(e)}")

    print("\n" + "-"*80)
    print("ПІДСУМОК РІЗНОМАНІТНОСТІ:")
    print(f"  Всього топіків: {len(topics)}")
    print(f"  Унікальних архетипів: {len(set(archetypes_used))}")
    print(f"  Використані: {archetypes_used}")

    if len(set(archetypes_used)) > 1:
        print("  [OK] Система обирає різні архетипи для різних топіків")
    else:
        print("  [WARN] Всі топіки отримали однаковий архетип")


def test_cross_genre_difference():
    """Тест різниці між жанрами - один топік на різних каналах"""
    print("\n\n" + "="*80)
    print("3. ТЕСТ МІЖЖАНРОВОЇ РІЗНИЦІ - Один топік, різні канали")
    print("="*80)

    # Один абстрактний топік який підходить для всіх жанрів
    topic = "Людина приймає рішення яке змінює все назавжди (CROSS-GENRE TEST)"

    test_channels = [
        {
            'id': 'UCLFeJMO2Mbh-bwAQWya4-dw',
            'name': 'LifeSeeds Hub',
            'genre': 'Motivational / Parables',
            'expected_pool': ['reluctant_transformation', 'mistaken_identity_of_evil', 'protector_paradox']
        },
        {
            'id': 'UC9KUaoTY4vyGGHzCccqHnAA',
            'name': 'NeuralTales Station',
            'genre': 'Science Fiction',
            'expected_pool': ['inversion_of_source', 'delayed_consequence', 'reluctant_transformation']
        },
        {
            'id': 'UCaxPNkUMQKqepAp0JbpVrrw',
            'name': 'HorrorWhisper Studio',
            'genre': 'Horror',
            'expected_pool': ['inversion_of_source', 'protector_paradox', 'delayed_consequence']
        }
    ]

    results = []

    for i, channel in enumerate(test_channels, 1):
        print(f"\n[{i}/{len(test_channels)}] {channel['name']} ({channel['genre']})")
        print(f"  Очікуваний пул: {channel['expected_pool']}")

        payload = {
            'topic_text': topic,
            'channel_id': channel['id'],
            'user_id': 'c334d862-4031-7097-4207-84856b59d3ed'
        }

        try:
            response = lambda_client.invoke(
                FunctionName='content-narrative',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )

            result = json.loads(response['Payload'].read())

            if 'errorMessage' in result:
                print(f"  [ERROR] {result['errorMessage']}")
                continue

            nc = result.get('narrative_content', {})
            mech = nc.get('mechanics', {})
            archetype = mech.get('dominant_archetype', 'N/A')

            in_pool = archetype in channel['expected_pool']
            status = '[OK]' if in_pool else '[FAIL]'

            print(f"  Архетип: {archetype} {status}")
            print(f"  Surface: {mech.get('surface_truth', 'N/A')[:60]}...")
            print(f"  Hidden: {mech.get('hidden_truth', 'N/A')[:60]}...")

            results.append({
                'channel': channel['name'],
                'archetype': archetype,
                'in_pool': in_pool
            })

            time.sleep(2)

        except Exception as e:
            print(f"  [ERROR] {str(e)}")

    print("\n" + "-"*80)
    print("ПІДСУМОК МІЖЖАНРОВОЇ РІЗНИЦІ:")
    archetypes = [r['archetype'] for r in results]
    print(f"  Унікальних архетипів: {len(set(archetypes))}/{len(archetypes)}")
    print(f"  Архетипи: {archetypes}")

    in_pool_count = sum(1 for r in results if r['in_pool'])
    print(f"  Архетипи з правильного пулу: {in_pool_count}/{len(results)}")

    if len(set(archetypes)) == len(archetypes):
        print("  [OK] Кожен жанр обрав унікальний архетип")
    elif len(set(archetypes)) > 1:
        print("  [OK] Жанри обирають різні архетипи")
    else:
        print("  [FAIL] Всі жанри обрали однаковий архетип")


def main():
    print("\n")
    print("=" * 80)
    print(" " * 15 + "КОМПЛЕКСНА ПЕРЕВІРКА VARIANT B")
    print("=" * 80)

    # 1. Check DynamoDB
    check_dynamodb_pools()

    # 2. Test variety on single channel
    test_single_channel_variety()

    # 3. Test cross-genre difference
    test_cross_genre_difference()

    print("\n\n" + "="*80)
    print("ФІНАЛЬНИЙ ВИСНОВОК")
    print("="*80)
    print("""
Якщо всі 3 тести пройшли успішно:
✓ DynamoDB має різні пули для різних жанрів
✓ Один канал може обирати різні архетипи для різних топіків
✓ Різні жанри обирають різні архетипи для одного топіка

Тоді Variant B працює ідеально!
    """)


if __name__ == '__main__':
    main()
