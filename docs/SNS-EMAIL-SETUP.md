# SNS Email Notifications Setup

**Status:** ⏳ Requires manual action
**Topic ARN:** `arn:aws:sns:eu-central-1:599297130956:cloudwatch-alarms-critical`

---

## Overview

CloudWatch Alarms are configured to send notifications to SNS topic `cloudwatch-alarms-critical`. To receive email notifications when alarms trigger, you need to subscribe your email address to this topic.

---

## Setup Steps

### Option 1: AWS Console (Recommended)

1. **Open SNS Console:**
   ```
   https://console.aws.amazon.com/sns/v3/home?region=eu-central-1#/topics
   ```

2. **Find the topic:**
   - Search for: `cloudwatch-alarms-critical`
   - Click on the topic ARN

3. **Create subscription:**
   - Click **"Create subscription"** button
   - Protocol: Select **"Email"**
   - Endpoint: Enter your email address (e.g., `admin@example.com`)
   - Click **"Create subscription"**

4. **Confirm subscription:**
   - Check your email inbox
   - Look for email from: `no-reply@sns.amazonaws.com`
   - Subject: "AWS Notification - Subscription Confirmation"
   - Click the **"Confirm subscription"** link

5. **Verify:**
   - Go back to SNS Console → Topic → Subscriptions tab
   - Status should show: **"Confirmed"** ✅

---

### Option 2: AWS CLI

```bash
# Subscribe email to SNS topic
aws sns subscribe \
  --topic-arn arn:aws:sns:eu-central-1:599297130956:cloudwatch-alarms-critical \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region eu-central-1

# Check confirmation email and click the link

# Verify subscription
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:eu-central-1:599297130956:cloudwatch-alarms-critical \
  --region eu-central-1
```

---

## Notification Types

Once subscribed, you'll receive emails for:

### 1. Lambda Error Alarms
**When:** >5 errors in 5 minutes
**Functions monitored:**
- content-narrative
- content-audio-tts
- content-save-result
- content-theme-agent
- content-video-assembly
- ec2-sd35-control
- dashboard-content

**Example email:**
```
Subject: ALARM: "content-narrative-high-errors" in EU (Frankfurt)

You are receiving this email because your Amazon CloudWatch Alarm
"content-narrative-high-errors" in the EU (Frankfurt) region has
entered the ALARM state.

Reason for State Change:
Threshold Crossed: 1 datapoint [7.0 (11/12/24 10:35:00)] was greater
than the threshold (5.0).
```

### 2. Lambda Duration Alarms
**When:** Average duration exceeds 80% of timeout
**Example:** content-narrative taking >240s (timeout is 300s)

### 3. Step Functions Failures
**When:** >2 workflow failures in 1 hour

### 4. DynamoDB Throttles
**When:** >5 throttle events in 5 minutes

### 5. Cost Alerts
**When:** Estimated daily charges exceed $50

---

## Testing Notifications

### Trigger test alarm:
```bash
# Temporarily set alarm to ALARM state for testing
aws cloudwatch set-alarm-state \
  --alarm-name content-narrative-high-errors \
  --state-value ALARM \
  --state-reason "Testing SNS notifications" \
  --region eu-central-1

# Reset to OK after testing
aws cloudwatch set-alarm-state \
  --alarm-name content-narrative-high-errors \
  --state-value OK \
  --state-reason "Test complete" \
  --region eu-central-1
```

You should receive an email within 1-2 minutes.

---

## Multiple Email Addresses

To add more team members:

```bash
# Subscribe additional emails
aws sns subscribe \
  --topic-arn arn:aws:sns:eu-central-1:599297130956:cloudwatch-alarms-critical \
  --protocol email \
  --notification-endpoint team-member@example.com \
  --region eu-central-1
```

Each person will need to confirm their subscription.

---

## Telegram Integration (Optional)

For Telegram notifications:

1. **Create Telegram bot:**
   - Message @BotFather on Telegram
   - Send `/newbot` and follow instructions
   - Save the bot token

2. **Create Lambda function for Telegram:**
   ```python
   import json
   import requests

   def lambda_handler(event, context):
       message = event['Records'][0]['Sns']['Message']
       subject = event['Records'][0]['Sns']['Subject']

       bot_token = 'YOUR_BOT_TOKEN'
       chat_id = 'YOUR_CHAT_ID'

       text = f"🚨 {subject}\n\n{message}"

       requests.post(
           f'https://api.telegram.org/bot{bot_token}/sendMessage',
           json={'chat_id': chat_id, 'text': text}
       )

       return {'statusCode': 200}
   ```

3. **Subscribe Lambda to SNS:**
   ```bash
   aws sns subscribe \
     --topic-arn arn:aws:sns:eu-central-1:599297130956:cloudwatch-alarms-critical \
     --protocol lambda \
     --notification-endpoint arn:aws:lambda:eu-central-1:599297130956:function:telegram-notifier \
     --region eu-central-1
   ```

---

## Unsubscribe

To stop receiving notifications:

### Via email:
Look for "Unsubscribe" link at bottom of any SNS notification email

### Via AWS CLI:
```bash
# List subscriptions to find Subscription ARN
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:eu-central-1:599297130956:cloudwatch-alarms-critical \
  --region eu-central-1

# Unsubscribe
aws sns unsubscribe \
  --subscription-arn arn:aws:sns:eu-central-1:599297130956:cloudwatch-alarms-critical:SUBSCRIPTION-ID \
  --region eu-central-1
```

---

## Troubleshooting

### Issue: Confirmation email not received
**Solutions:**
1. Check spam/junk folder
2. Check email filters
3. Try different email address
4. Wait 5-10 minutes (AWS can be slow)

### Issue: Subscription shows "PendingConfirmation"
**Solutions:**
1. Check for confirmation email again
2. Delete subscription and recreate it
3. Use different email protocol (email vs email-json)

### Issue: Not receiving alarm notifications
**Solutions:**
1. Verify subscription status is "Confirmed"
2. Test with `set-alarm-state` command
3. Check CloudWatch Alarms are configured with correct SNS ARN
4. Verify alarms are triggering (check Alarm History)

---

## Cost

SNS notifications are **very cheap:**
- First 1,000 email notifications per month: **Free**
- Additional emails: **$2.00 per 100,000 emails**

Expected cost: **~$0.01/month** (assuming 10-20 alarms per month)

---

## Security Best Practices

1. **Don't use public email lists** - SNS notifications may contain sensitive info
2. **Use role-based emails** - e.g., devops@company.com instead of personal emails
3. **Enable MFA** on AWS account to prevent unauthorized SNS changes
4. **Monitor SNS access** in CloudTrail

---

## Next Steps

✅ Subscribe your email to SNS topic
✅ Test notifications with `set-alarm-state`
✅ Add team members if needed
✅ Consider Telegram integration for mobile notifications

---

**Status:** Setup requires ~5 minutes
**Difficulty:** Easy ⭐
**Impact:** High - proactive issue detection
