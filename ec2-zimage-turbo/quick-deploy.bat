@echo off
REM Quick deployment script for Windows

echo ==========================================
echo Z-Image-Turbo Quick Deploy
echo ==========================================
echo.

REM Configuration
set KEY_PATH=E:\youtube-content-automation\n8n-key.pem

REM Get EC2 IP from AWS
echo [1/4] Getting EC2 instance IP...
for /f "tokens=*" %%i in ('aws ec2 describe-instances --region eu-central-1 --instance-ids i-0a71aa2e72e9b9f75 --query "Reservations[0].Instances[0].PublicIpAddress" --output text') do set EC2_IP=%%i

if "%EC2_IP%"=="" (
    echo ERROR: Could not get EC2 IP. Is instance running?
    pause
    exit /b 1
)

echo    EC2 IP: %EC2_IP%
echo.

REM Upload files
echo [2/4] Uploading files to EC2...
scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no api_server.py ubuntu@%EC2_IP%:/tmp/
scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no deploy.sh ubuntu@%EC2_IP%:/tmp/
echo    Files uploaded
echo.

REM Run deployment
echo [3/4] Running deployment script on EC2...
echo    This will take 5-10 minutes...
ssh -i "%KEY_PATH%" -o StrictHostKeyChecking=no ubuntu@%EC2_IP% "chmod +x /tmp/deploy.sh && /tmp/deploy.sh"
echo.

REM Test API
echo [4/4] Testing API...
timeout /t 5 /nobreak > nul
curl -s http://%EC2_IP%:5000/health
echo.
echo.

echo ==========================================
echo Deployment Complete!
echo ==========================================
echo.
echo API Endpoints:
echo   Health: http://%EC2_IP%:5000/health
echo   Generate: http://%EC2_IP%:5000/generate
echo   Stats: http://%EC2_IP%:5000/stats
echo.
echo Check service logs:
echo   ssh -i "%KEY_PATH%" ubuntu@%EC2_IP% "sudo journalctl -u zimage-api -f"
echo.
pause
