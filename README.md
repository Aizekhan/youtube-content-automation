# YouTube Content Automation 🎥🤖

Автоматична система генерації контенту для YouTube каналів з використанням AI.

## 🚀 Швидкий старт

### Доступ до сайту
- **URL**: https://n8n-creator.space/
- **Авторизація**: Google OAuth (AWS Cognito)

### Головні розділи
- **Home** (`/`) - головна сторінка з навігацією
- **Channels** (`/channels.html`) - управління каналами
- **Dashboard** (`/dashboard.html`) - моніторинг процесів
- **Content** (`/content.html`) - перегляд контенту
- **Costs** (`/costs.html`) - аналітика витрат
- **Prompts** (`/prompts-editor.html`) - редагування AI промптів

## 📋 Що робить система

1. **Генерує теми** для відео (AI через OpenAI GPT-4o)
2. **Створює наративи** з детальними сценами
3. **Генерує аудіо** для кожної сцени (AWS Polly)
4. **Готує промпти** для генерації зображень (SDXL)
5. **Відстежує витрати** на всі AI сервіси

## 🎯 Основні функції

### Channels (Канали)
- **Overview**: Перегляд всіх каналів, статус активності
- **Configurations**: Налаштування TTS, тривалості, стилю контенту

### Costs (Витрати)
- **Month-to-Date**: Загальні витрати за місяць
- **Daily Average**: Середні витрати на день
- **Today**: Витрати за сьогодні
- Графіки по сервісах та операціях

### Dashboard (Моніторинг)
- Статус Step Functions виконань
- CloudWatch логи
- Auto-refresh кожні 30 секунд

## 🔧 Технічний стек

- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js
- **Backend**: AWS Lambda (Python 3.11), Step Functions
- **Database**: DynamoDB (4 таблиці)
- **Storage**: S3
- **AI**: OpenAI GPT-4o, AWS Polly
- **Server**: Nginx + PHP-FPM (Docker), Ubuntu 20.04

## 📖 Документація

### Основна
- [TECHNICAL-ARCHITECTURE-2025-11.md](./docs/TECHNICAL-ARCHITECTURE-2025-11.md)
- [MULTI-TENANT-VIDEO-ASSEMBLY-FIX-2025-11-29.md](./docs/MULTI-TENANT-VIDEO-ASSEMBLY-FIX-2025-11-29.md)
- [CHANGELOG-2025-11-29.md](./CHANGELOG-2025-11-29.md)

## 🆕 Recent Update (29.11.2025)

✅ Multi-Tenant Video Assembly - Всі баги виправлені, система працює end-to-end

---

**Version**: 2.0 | **Last Update**: 29.11.2025
