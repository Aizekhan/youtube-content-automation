# CSP Headers Deployment - Покрокова Інструкція

**Дата:** 2025-12-01
**Файл:** nginx-security-headers-v2.conf
**Цільовий сервер:** nginx web server

---

## 📋 Передумови

Перед початком переконайтеся:
- ✅ У вас є SSH доступ до сервера
- ✅ У вас є sudo права
- ✅ nginx встановлений і працює
- ✅ Ви знаєте IP адресу або домен сервера

---

## 🚀 Швидкий Deployment (5 хвилин)

### Крок 1: Upload файлу на сервер

**Варіант A: SCP (Рекомендовано)**
```bash
# З вашого локального комп'ютера
scp E:/youtube-content-automation/nginx-security-headers-v2.conf ubuntu@YOUR_SERVER_IP:/tmp/

# Приклад:
scp E:/youtube-content-automation/nginx-security-headers-v2.conf ubuntu@3.75.97.188:/tmp/
```

**Варіант B: Manual Copy-Paste**
Якщо SCP не працює:
1. SSH до сервера: `ssh ubuntu@YOUR_SERVER_IP`
2. Створити файл: `sudo nano /tmp/nginx-security-headers-v2.conf`
3. Відкрити локальний файл `nginx-security-headers-v2.conf`
4. Скопіювати весь вміст
5. Вставити у nano (Ctrl+Shift+V у деяких терміналах)
6. Зберегти: Ctrl+O, Enter, Ctrl+X

---

### Крок 2: Встановити security headers config

```bash
# SSH до сервера
ssh ubuntu@YOUR_SERVER_IP

# Перемістити файл у nginx config directory
sudo mv /tmp/nginx-security-headers-v2.conf /etc/nginx/conf.d/security-headers.conf

# Перевірити, що файл на місці
ls -la /etc/nginx/conf.d/security-headers.conf
```

**Очікуваний output:**
```
-rw-r--r-- 1 root root 3456 Dec  1 16:50 /etc/nginx/conf.d/security-headers.conf
```

---

### Крок 3: Знайти nginx site configuration

```bash
# Знайти основний config файл
sudo nginx -t

# Зазвичай це один з:
# - /etc/nginx/sites-available/default
# - /etc/nginx/nginx.conf
# - /etc/nginx/conf.d/default.conf
```

**Приклад output:**
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

---

### Крок 4: Додати include до site config

**Відкрити site config:**
```bash
# Для Ubuntu/Debian
sudo nano /etc/nginx/sites-available/default

# АБО для інших систем
sudo nano /etc/nginx/nginx.conf
```

**Знайти блок `server { ... }` і додати include:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 👇 ДОДАТИ ЦЕЙ РЯДОК (після listen/server_name, перед location)
    include /etc/nginx/conf.d/security-headers.conf;

    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

**⚠️ ВАЖЛИВО:**
- Додати `include` ОДИН РАЗ у блок `server { }`
- НЕ додавати у `location { }` блоки
- Зберегти: Ctrl+O, Enter, Ctrl+X

---

### Крок 5: Перевірити nginx configuration

```bash
# Перевірити синтаксис
sudo nginx -t
```

**Очікуваний output:**
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

**❌ Якщо є помилки:**
```
nginx: [emerg] unknown directive "some-directive"
```
- Перевірити, що include рядок правильний
- Перевірити, що security-headers.conf файл існує
- Виправити синтаксичні помилки

---

### Крок 6: Reload nginx

```bash
# Reload nginx (БЕЗ downtime)
sudo systemctl reload nginx

# Перевірити статус
sudo systemctl status nginx
```

**Очікуваний output:**
```
● nginx.service - A high performance web server
   Loaded: loaded (/lib/systemd/system/nginx.service)
   Active: active (running)
```

---

## ✅ Верифікація Deployment

### Тест 1: Перевірити headers у відповіді

```bash
# З вашого локального комп'ютера
curl -I http://YOUR_SERVER_IP/

# АБО з доменом
curl -I https://your-domain.com/
```

**Очікуваний output (має містити):**
```
HTTP/1.1 200 OK
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' ...
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), ...
```

---

### Тест 2: Перевірити у браузері

1. Відкрити http://YOUR_SERVER_IP/ у браузері
2. Відкрити DevTools (F12)
3. Перейти на Network tab
4. Оновити сторінку (F5)
5. Клікнути на першому request (зазвичай document)
6. Перейти на Headers tab
7. Шукати Response Headers

**Має бути:**
- ✅ Content-Security-Policy
- ✅ X-Content-Type-Options
- ✅ X-Frame-Options
- ✅ Referrer-Policy
- ✅ Permissions-Policy

---

### Тест 3: Перевірити, що сайт працює

**Відкрити всі сторінки:**
1. index.html - головна
2. login.html - логін
3. dashboard.html - дашборд
4. channels.html - канали
5. content.html - контент
6. costs.html - витрати
7. prompts-editor.html - редактор
8. settings.html - налаштування

**Перевірити:**
- ✅ Сторінки завантажуються
- ✅ Немає помилок у Console (F12 → Console)
- ✅ Google OAuth працює (якщо є)
- ✅ API calls працюють

---

### Тест 4: Security Headers Score

**Online тест:**
1. Перейти на https://securityheaders.com/
2. Ввести YOUR_DOMAIN
3. Натиснути "Scan"

**Очікувана оцінка:**
- 🎯 **Grade A** або **A+**

---

## 🔧 Troubleshooting

### Проблема 1: Headers не з'являються

**Симптом:** `curl -I` не показує security headers

**Рішення:**
```bash
# Перевірити, що include додано
sudo nano /etc/nginx/sites-available/default
# Має бути: include /etc/nginx/conf.d/security-headers.conf;

# Перевірити, що файл існує
ls -la /etc/nginx/conf.d/security-headers.conf

# Reload nginx
sudo systemctl reload nginx
```

---

### Проблема 2: nginx не reload'иться

**Симптом:** `sudo systemctl reload nginx` дає помилку

**Рішення:**
```bash
# Перевірити синтаксис
sudo nginx -t

# Якщо є помилки - виправити їх у config файлі
# Потім reload знову
sudo systemctl reload nginx
```

---

### Проблема 3: Сайт не працює після deployment

**Симптом:** Білий екран або помилки у Console

**Швидкий rollback:**
```bash
# SSH до сервера
ssh ubuntu@YOUR_SERVER_IP

# Видалити include з config
sudo nano /etc/nginx/sites-available/default
# Видалити або закоментувати: # include /etc/nginx/conf.d/security-headers.conf;

# Reload
sudo systemctl reload nginx
```

**Потім перевірити:**
- Відкрити Console у браузері (F12)
- Шукати CSP violations: "Refused to load..."
- Записати URL блокованого ресурсу
- Додати його до CSP policy у security-headers.conf

---

### Проблема 4: Google OAuth не працює

**Симптом:** Login popup блокується

**Рішення:**
Перевірити, що у CSP є:
```nginx
script-src 'self' 'unsafe-inline' https://accounts.google.com;
frame-src 'self' https://accounts.google.com;
```

Якщо немає - додати і reload nginx.

---

### Проблема 5: API calls не працюють

**Симптом:** Fetch/XHR requests blocked

**Рішення:**
Перевірити, що у CSP є ваші Lambda URLs:
```nginx
connect-src 'self'
    https://*.lambda-url.eu-central-1.on.aws
    https://s3.eu-central-1.amazonaws.com
    https://*.s3.eu-central-1.amazonaws.com;
```

---

## 📊 CSP Violations - Як знайти і виправити

### Крок 1: Відкрити Console

1. Відкрити сайт у браузері
2. F12 → Console tab
3. Шукати червоні помилки з текстом "Content Security Policy"

### Крок 2: Читати повідомлення

**Приклад CSP violation:**
```
Refused to load the script 'https://cdn.example.com/lib.js'
because it violates the following Content Security Policy directive:
"script-src 'self' https://cdn.jsdelivr.net".
```

**Це означає:**
- Blocked URL: `https://cdn.example.com/lib.js`
- Current policy: дозволено лише `'self'` і `https://cdn.jsdelivr.net`
- Потрібно: додати `https://cdn.example.com` до `script-src`

### Крок 3: Оновити CSP policy

```bash
# SSH до сервера
ssh ubuntu@YOUR_SERVER_IP

# Відкрити security headers
sudo nano /etc/nginx/conf.d/security-headers.conf

# Знайти відповідну директиву (script-src, style-src, img-src, etc.)
# Додати новий домен до списку

# Приклад ДО:
script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;

# Приклад ПІСЛЯ:
script-src 'self' 'unsafe-inline'
    https://cdn.jsdelivr.net
    https://cdn.example.com;

# Зберегти: Ctrl+O, Enter, Ctrl+X

# Reload nginx
sudo systemctl reload nginx
```

---

## 🎯 Рекомендований Deployment Plan

### Phase 1: Staging/Test Environment (Якщо є)
1. Deploy CSP headers на test server
2. Протестувати всі сторінки
3. Записати всі CSP violations
4. Виправити CSP policy
5. Re-test

### Phase 2: Production - Permissive Mode
1. Deploy поточну CSP policy (з 'unsafe-inline', 'unsafe-eval')
2. Моніторити Console violations 1-2 дні
3. Записувати всі нові violations
4. Додавати потрібні домени до whitelist

### Phase 3: Production - Strict Mode (Майбутнє)
1. Видалити 'unsafe-inline' зі script-src
2. Видалити 'unsafe-eval'
3. Використовувати nonces або hashes для inline scripts
4. Найвищий рівень безпеки

---

## 📝 Checklist Deployment

**Pre-Deployment:**
- [ ] Зробити backup nginx config (`cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup`)
- [ ] Перевірити, що є SSH доступ
- [ ] Перевірити, що nginx працює

**Deployment:**
- [ ] Upload security-headers.conf на сервер
- [ ] Move до /etc/nginx/conf.d/
- [ ] Додати include до site config
- [ ] Перевірити nginx -t
- [ ] Reload nginx

**Post-Deployment:**
- [ ] curl -I перевірка headers
- [ ] Браузер DevTools перевірка
- [ ] Тест всіх сторінок (11 pages)
- [ ] Console - немає CSP violations
- [ ] securityheaders.com - Grade A/A+

**Якщо проблеми:**
- [ ] Rollback (видалити include)
- [ ] Записати CSP violations
- [ ] Виправити policy
- [ ] Re-deploy

---

## ✅ Success Criteria

Deployment вважається успішним, коли:
1. ✅ `curl -I` показує всі 6 security headers
2. ✅ Всі 11 HTML сторінок завантажуються без помилок
3. ✅ Console не має CSP violation errors
4. ✅ Google OAuth працює (login/logout)
5. ✅ API calls до Lambda працюють
6. ✅ securityheaders.com дає Grade A або A+

---

## 📞 Support

**Якщо щось не працює:**
1. Перевірити nginx error log: `sudo tail -f /var/log/nginx/error.log`
2. Перевірити access log: `sudo tail -f /var/log/nginx/access.log`
3. Перевірити browser console (F12)
4. Rollback за допомогою backup

**Backup location:**
```
/etc/nginx/sites-available/default.backup
```

---

**Generated:** 2025-12-01
**Estimated Time:** 10-15 minutes
**Difficulty:** Medium
**Risk:** Low (easy rollback)
