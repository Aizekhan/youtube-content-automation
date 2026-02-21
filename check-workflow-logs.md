# Як перевірити чому деплой не працює

## Крок 1: Відкрийте останній workflow run
1. Йдіть на: https://github.com/Aizekhan/youtube-content-automation/actions/workflows/deploy-production.yml
2. Знайдіть Run #65 (commit 6095ff6) або Run #76
3. Натисніть на нього

## Крок 2: Перевірте job "detect-changes"
У списку jobs знайдіть "Detect Changed Files" і відкрийте

**Шукайте рядки:**
```
lambda=true або lambda=false
frontend=true або frontend=false
```

## Крок 3: Перевірте чи запускався job "deploy-frontend"
- Якщо НЕ запустився → означає frontend=false (не виявив зміни!)
- Якщо запустився але failed → дивіться помилку (ймовірно SSH)

## Крок 4: Якщо deploy-frontend запустився
Шукайте в логах:
- "Deploying frontend files to production..."
- "Changed files:" (список файлів)
- "scp ... ubuntu@3.75.97.188" (команди копіювання)
- Будь-які ЧЕРВОНІ помилки

## Можливі проблеми:

### Проблема A: frontend=false (не виявив зміни)
**Причина:** `git diff HEAD^ HEAD` не знаходить файли
**Рішення:** Змінити логіку детекції на `git diff origin/master~5..HEAD`

### Проблема B: SSH Permission denied
**Причина:** secrets.SSH_KEY застарів або неправильний
**Рішення:** Оновити SSH_KEY в GitHub Secrets

### Проблема C: scp: /home/ubuntu/web-admin/html/: No such file or directory
**Причина:** Неправильний шлях на сервері
**Рішення:** Перевірити де насправді лежать файли

## ШВИДКЕ РІШЕННЯ (якщо не хочете чекати):

Запустіть deploy-now.sh якщо маєте SSH доступ:
```bash
cd E:/youtube-content-automation
chmod +x deploy-now.sh
./deploy-now.sh
```

АБО скопіюйте файли вручну через SCP якщо знаєте пароль/ключ.
