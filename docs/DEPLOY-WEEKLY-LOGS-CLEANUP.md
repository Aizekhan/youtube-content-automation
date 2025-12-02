# 🧹 Автоматичне Очищення Логів - Інструкція

**Мета:** Налаштувати автоматичне очищення System Logs кожної неділі о 3:00 ранку

**Проблема:** Логи ростуть на 2GB/місяць (найшвидший ріст кешу)

**Рішення:** Cron job для автоматичного видалення логів старше 7 днів

---

## 🚀 Швидке Налаштування (2 хвилини)

### Варіант 1: Автоматичний деплой (Рекомендовано)

```bash
# 1. Завантажити setup script на EC2
scp -i /tmp/aws-key.pem E:/youtube-content-automation/aws/setup-weekly-logs-cleanup.sh ubuntu@<INSTANCE_IP>:~/

# 2. SSH на EC2
ssh -i /tmp/aws-key.pem ubuntu@<INSTANCE_IP>

# 3. Запустити setup
bash ~/setup-weekly-logs-cleanup.sh

# Готово! Cleanup буде запускатись кожної неділі о 3:00
```

**Примітка:** Замініть `<INSTANCE_IP>` на IP адресу SD3.5 інстансу

---

### Варіант 2: Ручне налаштування

**1. SSH на EC2:**
```bash
ssh -i /tmp/aws-key.pem ubuntu@<INSTANCE_IP>
```

**2. Створити cleanup script:**
```bash
cat > ~/ec2-sd35-logs-cleanup.sh << 'EOF'
#!/bin/bash
echo "🧹 SD3.5 Logs Cleanup - $(date)"

# Clean journalctl (keep 7 days)
sudo journalctl --vacuum-time=7d

# Clean old log files
sudo find /var/log -type f -name "*.log" -mtime +7 -delete
sudo find /var/log -type f -name "*.gz" -mtime +14 -delete

# Clean API logs (if exist)
find ~/sd35-api/logs -type f -mtime +7 -delete 2>/dev/null

echo "✅ Cleanup completed"
EOF

chmod +x ~/ec2-sd35-logs-cleanup.sh
```

**3. Додати cron job (кожної неділі о 3:00):**
```bash
(crontab -l 2>/dev/null; echo "# SD3.5 Weekly logs cleanup"; echo "0 3 * * 0 ~/ec2-sd35-logs-cleanup.sh >> ~/logs-cleanup.log 2>&1") | crontab -
```

**4. Перевірити:**
```bash
crontab -l
```

Має показати:
```
# SD3.5 Weekly logs cleanup
0 3 * * 0 /home/ubuntu/ec2-sd35-logs-cleanup.sh >> /home/ubuntu/logs-cleanup.log 2>&1
```

---

## 🧪 Тестування

### Запустити cleanup зараз (не чекаючи неділі):

```bash
ssh -i /tmp/aws-key.pem ubuntu@<INSTANCE_IP>
~/ec2-sd35-logs-cleanup.sh
```

**Очікуваний результат:**
```
🧹 SD3.5 Weekly Logs Cleanup - Mon Nov 18 20:15:43 UTC 2025
==================================================

BEFORE cleanup:
Disk: 48G / 100G (48% used)

📊 Current log sizes:
   /var/log: 1.2G
   journalctl: 2.5 GB
   API logs: 320M

🗑️  Cleaning journalctl (keeping last 7 days)...
   journalctl: 2500MB → 800MB

🗑️  Cleaning /var/log (removing files >7 days)...
   Deleted 47 old .log files

🗑️  Cleaning compressed logs (removing .gz >14 days)...
   Deleted 23 old .gz files

...

AFTER cleanup:
Disk: 45G / 100G (45% used)

📊 Current log sizes:
   /var/log: 450M
   journalctl: 800 MB
   API logs: 120M

==================================================
✅ Weekly logs cleanup completed
==================================================
```

**Звільнено:** ~750MB - 1.7GB (залежно від накопичення)

---

## 📊 Моніторинг

### Перевірити історію cleanup:

```bash
ssh -i /tmp/aws-key.pem ubuntu@<INSTANCE_IP>
tail -50 ~/logs-cleanup.log
```

### Перевірити розмір логів:

```bash
# System logs
sudo du -sh /var/log

# Journalctl
sudo journalctl --disk-usage

# API logs
du -sh ~/sd35-api/logs
```

### Перевірити коли буде наступний cleanup:

```bash
# Показати всі cron jobs
crontab -l

# Показати останній запуск
ls -lh ~/logs-cleanup.log
```

---

## 📅 Розклад Роботи

```
Кожної неділі о 3:00 ранку (UTC):
├─ Видаляє journalctl логи старше 7 днів
├─ Видаляє /var/log/*.log старше 7 днів
├─ Видаляє /var/log/*.gz старше 14 днів
├─ Видаляє API логи старше 7 днів
└─ Записує результати в ~/logs-cleanup.log
```

**Чому неділя о 3:00?**
- Найменше навантаження на інстанс
- Якщо інстанс stopped - cleanup запуститься при наступному старті
- Уникнення конфлікту з production генерацією

---

## 🎯 Очікувані Результати

### Без автоматичного cleanup:

| Час | Логи | Диск | Статус |
|-----|------|------|--------|
| Зараз | 1GB | 48GB/100GB | ✅ OK |
| Через місяць | 3GB | 50GB/100GB | ✅ OK |
| Через 3 місяці | 7GB | 54GB/100GB | ✅ OK |
| Через 6 місяців | 13GB | 60GB/100GB | ⚠️ WARNING |
| Через рік | 25GB | 72GB/100GB | 🔴 CRITICAL |

### З автоматичним cleanup (кожного тижня):

| Час | Логи | Диск | Статус |
|-----|------|------|--------|
| Завжди | 500MB-1GB | 46-48GB/100GB | ✅ OK |

**Економія:** ~20-24GB за рік!

---

## ⚙️ Налаштування

### Змінити розклад (наприклад, кожної п'ятниці о 2:00):

```bash
crontab -e
```

Змінити рядок:
```
0 3 * * 0  →  0 2 * * 5
```

### Змінити період зберігання логів (наприклад, 14 днів):

```bash
nano ~/ec2-sd35-logs-cleanup.sh
```

Змінити:
```bash
sudo journalctl --vacuum-time=7d  →  sudo journalctl --vacuum-time=14d
find ... -mtime +7  →  find ... -mtime +14
```

### Вимкнути автоматичний cleanup:

```bash
crontab -e
# Видалити рядки з "SD3.5" або закоментувати їх символом #
```

---

## 🔍 Troubleshooting

### Cleanup не запускається автоматично

**Перевірити статус cron:**
```bash
sudo systemctl status cron
```

**Запустити cron якщо stopped:**
```bash
sudo systemctl start cron
sudo systemctl enable cron
```

### Cleanup запускається але нічого не видаляє

**Причина:** Логів старше 7 днів немає

**Перевірка:**
```bash
# Показати логи старше 7 днів
sudo find /var/log -type f -name "*.log" -mtime +7 -ls
```

**Якщо пусто:** Це нормально, cleanup працює коректно!

### Помилка "Permission denied"

**Причина:** Cleanup потребує sudo прав

**Рішення:** Переконатись що в скрипті є `sudo` перед командами:
```bash
sudo journalctl --vacuum-time=7d
sudo find /var/log ...
```

### Не створюється logs-cleanup.log

**Причина:** Шлях до лог-файлу неправильний

**Перевірка:**
```bash
crontab -l | grep cleanup
```

Має бути:
```
~/ec2-sd35-logs-cleanup.sh >> ~/logs-cleanup.log 2>&1
```

Не:
```
~/ec2-sd35-logs-cleanup.sh  (без >> ~/logs-cleanup.log)
```

---

## 📞 Контакти

**Документація:** https://n8n-creator.space/docs/EC2-SD35-CACHE-MANAGEMENT.md

**EC2 Instance:** i-0a71aa2e72e9b9f75 (eu-central-1)

**Support:** Перевірити повну документацію в розділі "EC2 Cache Management"

---

## ✅ Checklist Деплою

- [ ] Setup script завантажено на EC2
- [ ] Setup script запущено успішно
- [ ] Cron job додано (перевірено через `crontab -l`)
- [ ] Cleanup script виконується вручну без помилок
- [ ] Лог-файл ~/logs-cleanup.log створюється
- [ ] Перший cleanup запланований на наступну неділю

**Якщо всі пункти виконані - система налаштована! 🎉**

---

**Дата створення:** 2025-11-18
**Версія:** 1.0
**Статус:** ✅ Production Ready
