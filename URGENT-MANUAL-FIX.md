# ⚠️ ТЕРМІНОВЕ РУЧНЕ ВИПРАВЛЕННЯ

## Проблема
GitHub Actions НЕ деплоїть файли на production сервер.
Файли на https://n8n-creator.space ЗАСТАРІЛІ!

## Підтвердження проблеми
```bash
# На production зараз СТАРИЙ код:
curl -k https://n8n-creator.space/js/topics-manager.js | grep -A2 "localStorage"
# Показує: localStorage.getItem('user_id') ❌ СТАРИЙ КОД!

# Має бути: AuthManager + cookies ✅
```

## РІШЕННЯ: Вручну скопіювати файли на сервер

### Варіант 1: Якщо у вас є SSH доступ до сервера

```bash
# 1. Підключитись до сервера
ssh ubuntu@3.75.97.188
# АБО через AWS консоль EC2 -> Connect -> Session Manager

# 2. На сервері перейти в папку
cd /home/ubuntu/web-admin/html

# 3. Створити backup
sudo cp -r /home/ubuntu/web-admin/html /home/ubuntu/web-admin/html.backup.$(date +%Y%m%d-%H%M)

# 4. Завантажити НОВІ файли з GitHub
cd /tmp
git clone https://github.com/Aizekhan/youtube-content-automation.git
cd youtube-content-automation

# 5. Скопіювати оновлені файли
sudo cp js/navigation.js /home/ubuntu/web-admin/html/js/
sudo cp js/topics-manager.js /home/ubuntu/web-admin/html/js/
sudo cp js/auth.js /home/ubuntu/web-admin/html/js/
sudo cp topics-manager.html /home/ubuntu/web-admin/html/

# Оновити HTML з новими версіями
sudo cp index.html dashboard.html channels.html content.html \
        costs.html audio-library.html settings.html \
        /home/ubuntu/web-admin/html/

# 6. Перевірити права доступу
sudo chown -R ubuntu:ubuntu /home/ubuntu/web-admin/html
sudo chmod -R 755 /home/ubuntu/web-admin/html

# 7. Перевірити що файли оновились
grep -A2 "AuthManager" /home/ubuntu/web-admin/html/js/topics-manager.js
# Має показати: const authManager = new AuthManager();

grep "topics-manager" /home/ubuntu/web-admin/html/js/navigation.js
# Має показати: <a href="topics-manager.html"

# 8. Очистити кеш Nginx (якщо є)
sudo nginx -s reload
```

### Варіант 2: Через AWS Console (якщо немає SSH ключа)

1. Відкрийте AWS Console: https://eu-central-1.console.aws.amazon.com/ec2/home?region=eu-central-1#Instances:
2. Знайдіть instance **i-0f3cfc5f7f4845984** (n8n-server)
3. Натисніть **Connect** -> **Session Manager** -> **Connect**
4. Виконайте команди з Варіанту 1 (починаючи з кроку 2)

### Варіант 3: Виправити GitHub Actions SSH ключ

Можливо проблема в тому що SSH_KEY в GitHub Secrets застарів:

1. Підключитись до сервера (через AWS Console)
2. Згенерувати новий SSH ключ:
```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/github_deploy -N ""
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/github_deploy  # СКОПІЮЙТЕ ЦЕЙ КЛЮЧ!
```

3. Оновити GitHub Secret:
   - Йдіть на: https://github.com/Aizekhan/youtube-content-automation/settings/secrets/actions
   - Знайдіть `SSH_KEY`
   - Натисніть **Update**
   - Вставте ПРИВАТНИЙ ключ (вміст ~/.ssh/github_deploy)
   - Save

4. Запустіть workflow вручну:
   - https://github.com/Aizekhan/youtube-content-automation/actions/workflows/deploy-production.yml
   - Run workflow -> master -> Run workflow

## Перевірка після виправлення

```bash
# 1. Перевірити Topics Queue в меню
curl -k https://n8n-creator.space/js/navigation.js | grep -A2 "topics-manager"

# Має показати:
# <a href="topics-manager.html" class="nav-link">
#     <i class="bi bi-list-check"></i> Topics Queue
# </a>

# 2. Перевірити AuthManager
curl -k https://n8n-creator.space/js/topics-manager.js | grep -A5 "DOMContentLoaded"

# Має показати:
# const authManager = new AuthManager();
# const isAuthenticated = await authManager.initialize();

# 3. Перевірити auth.js імпорт
curl -k https://n8n-creator.space/topics-manager.html | grep "auth.js"

# Має показати:
# <script src="js/auth.js?v=20260221-0459"></script>
```

## Відкрити в браузері

Після виправлення:
1. Відкрити https://n8n-creator.space/dashboard.html
2. Натиснути **Ctrl+F5** (очистити кеш)
3. **"Topics Queue"** має з'явитись в верхньому меню
4. Натиснути на Topics Queue
5. Має НЕ вибивати з акаунту ✅

## Якщо все ще не працює

Напишіть в чат що саме бачите:
- Скріншот GitHub Actions logs
- Скріншот браузера (F12 -> Console)
- Результат команд перевірки вище
