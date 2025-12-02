# Backup Strategy - YouTube Content Automation

Повна документація backup стратегії системи.

**Дата створення:** 2025-12-02
**Версія:** 1.0
**Статус:** Production

---

## Огляд Backup Систем

### Що резервується:

- DynamoDB Tables - Point-in-Time Recovery (35 днів)
- S3 Buckets - Versioning + Lifecycle policies
- Lambda Functions - Git repository + GitHub Actions
- Terraform State - S3 versioning + DynamoDB locking
- Infrastructure Code - Git repository

### Retention Periods:

| Ресурс | Retention | Метод |
|--------|-----------|-------|
| DynamoDB | 35 днів | PITR |
| S3 Objects (current) | Безстроково | Versioning |
| S3 Objects (old versions) | 30 днів | Lifecycle policy |
| Lambda Code | Безстроково | Git |
| Terraform State | Безстроково | S3 Versioning |

---

## DynamoDB Backups

### Point-in-Time Recovery (PITR)

Всі критичні таблиці мають увімкнений PITR:

**Таблиці з PITR:**
- GeneratedContent - основний контент
- ChannelConfigs - конфігурації каналів
- CostTracking - трекінг витрат
- EC2InstanceLocks - блокування EC2
- SystemSettings - системні налаштування (Telegram credentials)

**Параметри:**
- Recovery Period: 35 днів
- Recovery Time Objective (RTO): ~15-30 хвилин
- Recovery Point Objective (RPO): До 5 хвилин

### Як відновити DynamoDB таблицю:

```bash
# Перевірити доступні точки відновлення
aws dynamodb describe-continuous-backups \
  --table-name GeneratedContent \
  --region eu-central-1

# Відновити таблицю до певного часу
aws dynamodb restore-table-to-point-in-time \
  --source-table-name GeneratedContent \
  --target-table-name GeneratedContent-restored \
  --restore-date-time 2025-12-02T10:00:00Z \
  --region eu-central-1

# Перевірити статус відновлення
aws dynamodb describe-table \
  --table-name GeneratedContent-restored \
  --region eu-central-1
```

---

## S3 Backups

### Versioning

Всі S3 buckets мають увімкнене versioning:

**Buckets:**
- youtube-automation-audio-files
- youtube-automation-images
- youtube-automation-final-videos
- youtube-automation-data-grucia
- youtube-automation-backups-grucia
- terraform-state-599297130956

### Lifecycle Policies

Застосовані lifecycle policies:

1. **DeleteOldVersions** - видаляє старі версії через 30 днів
2. **CleanupIncompleteUploads** - видаляє незавершені uploads через 7 днів

### Як відновити S3 об'єкт:

```bash
# Переглянути всі версії об'єкта
aws s3api list-object-versions \
  --bucket youtube-automation-audio-files \
  --prefix path/to/file.mp3

# Відновити попередню версію
aws s3api get-object \
  --bucket youtube-automation-audio-files \
  --key path/to/file.mp3 \
  --version-id VERSION_ID \
  restored-file.mp3
```

---

## Lambda Code Backups

### Git Repository

Весь Lambda код зберігається в Git: https://github.com/Aizekhan/youtube-content-automation

GitHub Actions автоматично деплоїть зміни при push на master.

### Як відновити Lambda функцію:

```bash
# Checkout попередньої версії з Git
git log aws/lambda/content-narrative/
git checkout COMMIT_HASH -- aws/lambda/content-narrative/

# Deploy через GitHub Actions
git add aws/lambda/content-narrative/
git commit -m "rollback: Restore to previous version"
git push
```

---

## Infrastructure Backups

### Terraform State

**Bucket:** terraform-state-599297130956
**Key:** production/terraform.tfstate

**Features:**
- Server-side encryption (AES256)
- Versioning enabled
- State locking via DynamoDB
- Lifecycle policy (30 днів)

### Як відновити Terraform State:

```bash
# Переглянути версії
aws s3api list-object-versions \
  --bucket terraform-state-599297130956 \
  --prefix production/terraform.tfstate

# Відновити версію
aws s3api get-object \
  --bucket terraform-state-599297130956 \
  --key production/terraform.tfstate \
  --version-id VERSION_ID \
  ./terraform-state-backup.tfstate
```

---

## Швидка перевірка Backup Status

```bash
# DynamoDB PITR
for table in GeneratedContent ChannelConfigs CostTracking EC2InstanceLocks SystemSettings; do
  aws dynamodb describe-continuous-backups \
    --table-name $table \
    --region eu-central-1 \
    --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus'
done

# S3 Versioning
for bucket in youtube-automation-audio-files youtube-automation-images; do
  aws s3api get-bucket-versioning --bucket $bucket
done
```

---

## Best Practices

### DO:
- Регулярно тестувати restoration procedures
- Зберігати критичні backups мінімум 30 днів
- Використовувати PITR для всіх production таблиць
- Версіонувати Terraform state
- Комітити код в Git перед deployment

### DON'T:
- Не вимикати versioning на production buckets
- Не зберігати sensitive data без encryption
- Не видаляти backup buckets вручну
- Не робити changes без Git history

---

**Останнє оновлення:** 2025-12-02
**Автор:** Claude Code
