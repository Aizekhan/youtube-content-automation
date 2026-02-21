# КРИТИЧНО: Синхронізація Git з Production
# Виконати ПЕРЕД налаштуванням GitHub Actions!
# Інакше CI/CD затре актуальний production код!

Write-Host "=" -NoNewline -ForegroundColor Red
Write-Host "=" * 70 -ForegroundColor Red
Write-Host "  КРИТИЧНО: Синхронізація Git з Production" -ForegroundColor Yellow
Write-Host "=" * 71 -ForegroundColor Red
Write-Host ""
Write-Host "Чому це важливо:" -ForegroundColor Cyan
Write-Host "  1. Production може мати НОВІШИЙ код ніж Git" -ForegroundColor White
Write-Host "  2. GitHub Actions deploy з Git → затре production зміни" -ForegroundColor White
Write-Host "  3. Треба СПОЧАТКУ синхронізувати, ПОТІМ CI/CD" -ForegroundColor White
Write-Host ""

# Перевірити поточний стан Git
Write-Host "Крок 1: Перевірка Git status..." -ForegroundColor Cyan
cd E:/youtube-content-automation
git status

Write-Host "`n" -NoNewline
Write-Host "Крок 2: Показати незакомічені зміни..." -ForegroundColor Cyan
$status = git status --short
if ($status) {
    Write-Host "Знайдено незакомічені зміни:" -ForegroundColor Yellow
    git status --short
} else {
    Write-Host "Немає незакомічених змін" -ForegroundColor Green
}

Write-Host "`n" -NoNewline
Write-Host "Крок 3: Перевірка останнього коміту..." -ForegroundColor Cyan
Write-Host "Останній commit:" -ForegroundColor White
git log -1 --oneline
Write-Host "Дата: " -NoNewline -ForegroundColor White
git log -1 --format=%cd

Write-Host "`n" -NoNewline
Write-Host "НАСТУПНІ КРОКИ (виконати вручну):" -ForegroundColor Yellow
Write-Host "=" * 71 -ForegroundColor Yellow

Write-Host "`n1. Переглянути зміни:" -ForegroundColor Cyan
Write-Host "   git status" -ForegroundColor White
Write-Host "   git diff" -ForegroundColor White

Write-Host "`n2. Додати ВСІ файли (включно з новими):" -ForegroundColor Cyan
Write-Host "   git add ." -ForegroundColor White

Write-Host "`n3. Створити commit з поточним production станом:" -ForegroundColor Cyan
Write-Host "   git commit -m 'Sync: Production state before CI/CD setup (2025-12-02)'" -ForegroundColor White

Write-Host "`n4. Push до GitHub:" -ForegroundColor Cyan
Write-Host "   git push" -ForegroundColor White

Write-Host "`n5. ТІЛЬКИ ПІСЛЯ цього налаштовувати GitHub Actions!" -ForegroundColor Cyan
Write-Host "   Інакше старий код затре production!" -ForegroundColor Red

Write-Host "`n" -NoNewline
Write-Host "ВАЖЛИВО:" -ForegroundColor Red
Write-Host "  Якщо є КРИТИЧНІ файли які НЕ треба комітити:" -ForegroundColor Yellow
Write-Host "    - .env файли з секретами" -ForegroundColor White
Write-Host "    - credentials.json" -ForegroundColor White
Write-Host "    - Додайте їх у .gitignore ПЕРЕД git add" -ForegroundColor White

Write-Host "`n" -NoNewline
Write-Host "Перевірити .gitignore:" -ForegroundColor Cyan
if (Test-Path .gitignore) {
    Write-Host "  .gitignore існує:" -ForegroundColor Green
    Get-Content .gitignore | Select-Object -First 10
} else {
    Write-Host "  .gitignore НЕ ЗНАЙДЕНО!" -ForegroundColor Red
    Write-Host "  Створіть .gitignore перед commit!" -ForegroundColor Yellow
}

Write-Host "`n" -NoNewline
Write-Host "=" * 71 -ForegroundColor Green
Write-Host "  Після синхронізації Git = Production можна безпечно CI/CD" -ForegroundColor Green
Write-Host "=" * 71 -ForegroundColor Green
