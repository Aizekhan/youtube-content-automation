# Manual Deploy Instructions

## Файли для деплою на сервер

Потрібно завантажити наступні файли на сервер `n8n-creator.space`:

### Оновлені файли:
1. **index.html** → `/var/www/youtube-automation/index.html`
   - Додано картку "Series Manager"

2. **channels.html** → `/var/www/youtube-automation/channels.html`
   - Оновлено cache-busting для channels-unified.js (v=1771901600)

3. **series-manager.html** → `/var/www/youtube-automation/series-manager.html`
   - НОВА сторінка для управління серіалами

## Опція 1: Через FTP/SFTP

```bash
# З'єднання:
Host: n8n-creator.space
User: root (або інший користувач з доступом)
Port: 22 (SFTP) або 21 (FTP)
Path: /var/www/youtube-automation/

# Файли для завантаження:
E:\youtube-content-automation\index.html
E:\youtube-content-automation\channels.html
E:\youtube-content-automation\series-manager.html
```

## Опція 2: Через SSH (якщо є доступ)

```bash
scp index.html root@n8n-creator.space:/var/www/youtube-automation/
scp channels.html root@n8n-creator.space:/var/www/youtube-automation/
scp series-manager.html root@n8n-creator.space:/var/www/youtube-automation/
```

## Опція 3: Через Git Pull на сервері

```bash
# SSH до сервера
ssh root@n8n-creator.space

# Перейти в папку проекту
cd /var/www/youtube-automation

# Зробити git pull
git pull origin master

# Готово!
```

## Після деплою:

1. Відкрити https://n8n-creator.space/
2. Побачити нову картку "Series Manager"
3. Клікнути на неї → відкриється series-manager.html
4. На channels.html оновиться версія JS (видалить помилку infoBox)

## Що нового:

### Index.html:
- Додана картка "Series Manager" з іконкою 🎬
- Опис: "Управління серіалами: персонажі, сюжетні лінії, напруга епізодів"

### Channels.html:
- Виправлено cache-busting параметр для channels-unified.js
- Тепер `?v=1771901600` (раніше було `?v=1771809237`)
- Це усуне помилку "Identifier 'infoBox' has already been declared"

### Series-manager.html:
- Нова сторінка для Series Manager
- UI для управління:
  - Персонажами (імена, голоси, візуальні характеристики)
  - Сюжетними лініями (відкриті/закриті нитки)
  - Рівнем напруги епізодів (1-10 шкала)
  - Архетипами (щоб не повторювати)

---

**Коміт:** `2d4620c`
**Дата:** 2026-02-24
**Status:** Готово до деплою ✅
