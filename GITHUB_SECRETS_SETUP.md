# GitHub Secrets Setup для Auto-Deploy

## Необхідні Secrets для деплою на n8n-creator.space

### 1. Відкрити налаштування GitHub Secrets

Перейти: https://github.com/Aizekhan/youtube-content-automation/settings/secrets/actions

Або:
1. Відкрити репозиторій на GitHub
2. Settings → Secrets and variables → Actions
3. Натиснути "New repository secret"

### 2. Додати SSH Secrets

#### SSH_HOST
```
Назва: SSH_HOST
Значення: <IP адреса або домен сервера>
Приклад: 123.45.67.89
         або n8n-creator.space
```

#### SSH_USER
```
Назва: SSH_USER
Значення: <SSH користувач>
Приклад: root
         або ubuntu
         або www-data
```

#### SSH_KEY
```
Назва: SSH_KEY
Значення: <Приватний SSH ключ>

Як отримати:
1. На локальній машині (якщо вже є SSH доступ):
   cat ~/.ssh/id_rsa

2. Або на сервері згенерувати новий:
   ssh-keygen -t rsa -b 4096 -C "github-actions"
   cat ~/.ssh/id_rsa

3. Скопіювати ВСЬ текст включно з:
   -----BEGIN OPENSSH PRIVATE KEY-----
   ...весь ключ...
   -----END OPENSSH PRIVATE KEY-----

ВАЖЛИВО: Додати публічний ключ на сервер:
   cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
   або
   ssh-copy-id user@server
```

#### SSH_WEB_PATH
```
Назва: SSH_WEB_PATH
Значення: <Шлях до веб-файлів на сервері>

Типові варіанти:
- /var/www/n8n-creator.space
- /var/www/html
- /usr/share/nginx/html
- /home/user/website

Як знайти:
1. SSH на сервер: ssh user@server
2. Знайти конфіг nginx:
   sudo cat /etc/nginx/sites-available/n8n-creator.space
   або
   sudo cat /etc/nginx/nginx.conf

3. Знайти рядок "root":
   root /var/www/n8n-creator.space;
```

#### SSH_PORT (опціонально)
```
Назва: SSH_PORT
Значення: 22  (за замовчуванням)

Якщо SSH працює на іншому порту:
Значення: 2222  (або ваш порт)
```

### 3. Перевірити доступ SSH

Перед додаванням secrets, переконайтесь що SSH працює:

```bash
# З локальної машини
ssh user@server

# Якщо працює - можна додавати secrets
# Якщо НЕ працює - спочатку налаштуйте SSH доступ
```

### 4. Тестовий деплой

Після додавання всіх secrets:

1. Зробити будь-яку зміну в prompts-editor.html
2. Закомітити та запушити:
```bash
git add prompts-editor.html
git commit -m "Test deploy"
git push
```

3. Перевірити GitHub Actions:
   https://github.com/Aizekhan/youtube-content-automation/actions

4. Якщо успішно - файл з'явиться на:
   https://n8n-creator.space/prompts-editor.html

### 5. Ручний деплой (якщо GitHub Actions не працює)

```bash
# Варіант A: SCP
scp prompts-editor.html user@server:/var/www/n8n-creator.space/

# Варіант B: SFTP
sftp user@server
put prompts-editor.html /var/www/n8n-creator.space/
exit

# Варіант C: rsync
rsync -avz prompts-editor.html user@server:/var/www/n8n-creator.space/
```

## Існуючі Secrets (вже налаштовані)

Ці secrets вже додані для Lambda деплою:

- ✅ `AWS_ACCESS_KEY_ID` - для AWS Lambda
- ✅ `AWS_SECRET_ACCESS_KEY` - для AWS Lambda

## Troubleshooting

### Помилка: Permission denied (publickey)

**Проблема:** SSH ключ не доданий на сервер

**Рішення:**
```bash
# На локальній машині
ssh-copy-id user@server

# Або вручну на сервері
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys  # вставити публічний ключ
chmod 600 ~/.ssh/authorized_keys
```

### Помилка: Host key verification failed

**Проблема:** Сервер не в known_hosts

**Рішення:** Додати `StrictHostKeyChecking=no` в SSH команду
(вже додано в workflow)

### Помилка: Permission denied при chmod/chown

**Проблема:** Користувач не має прав

**Рішення:** Використовувати root користувача або додати sudo:
```yaml
script: |
  sudo chmod 644 prompts-editor.html
  sudo chown www-data:www-data prompts-editor.html
```

### Файл деплоїться але не відображається на сайті

**Проблема:** Неправильний шлях або права доступу

**Рішення:**
1. Перевірити nginx конфіг:
```bash
sudo nginx -t
sudo cat /etc/nginx/sites-available/n8n-creator.space
```

2. Перевірити права:
```bash
ls -la /var/www/n8n-creator.space/prompts-editor.html
```

3. Має бути:
```
-rw-r--r-- 1 www-data www-data 50000 Nov 3 00:00 prompts-editor.html
```

## Альтернативні варіанти деплою

### Варіант A: AWS S3 (якщо сайт на S3)

```yaml
- name: Deploy to S3
  run: |
    aws s3 cp prompts-editor.html s3://n8n-creator.space/ --acl public-read
```

Потрібні secrets: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY (вже є)

### Варіант B: GitHub Pages

1. Створити gh-pages бранч
2. Додати prompts-editor.html
3. Включити GitHub Pages в налаштуваннях
4. Доступ: https://aizekhan.github.io/youtube-content-automation/prompts-editor.html

### Варіант C: Netlify/Vercel

1. Підключити репозиторій до Netlify/Vercel
2. Вказати build command: `echo "No build needed"`
3. Вказати publish directory: `.`
4. Автодеплой при кожному пуші

## Перевірка що все працює

```bash
# 1. Перевірити що secrets додані
curl -H "Authorization: token YOUR_GITHUB_TOKEN" \
  https://api.github.com/repos/Aizekhan/youtube-content-automation/actions/secrets

# 2. Запустити workflow вручну
# GitHub → Actions → Deploy Website → Run workflow

# 3. Перевірити логи
# GitHub → Actions → останній run → Deploy HTML files to nginx server

# 4. Перевірити сайт
curl -I https://n8n-creator.space/prompts-editor.html
# Має показати 200 OK
```
