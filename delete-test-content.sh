#!/bin/bash

# Keep this record
KEEP_CHANNEL="UCRmO5HB89GW_zjX3dJACfzw"
KEEP_TIME="2025-11-03T00:32:03.644211Z"

# Delete all records except the one we want to keep
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"UCRmO5HB89GW_zjX3dJACfzw"},"created_at":{"S":"2025-10-31T22:53:12.111890Z"}}'
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"UCRmO5HB89GW_zjX3dJACfzw"},"created_at":{"S":"2025-11-03T00:30:10.804528Z"}}'
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"UC06Vnkv6D3fcUhWPoaMrdsA"},"created_at":{"S":"2025-10-31T22:53:12.138993Z"}}'
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"UCccEeD46xZiwmMPCY3JrBNw"},"created_at":{"S":"2025-10-31T22:53:12.206229Z"}}'
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"UC0Ynt0BpdzDeTKJwAySpU5w"},"created_at":{"S":"2025-10-31T22:53:12.145193Z"}}'
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"UCcX_Yu4XC9feeygScO0v1fg"},"created_at":{"S":"2025-10-31T22:53:12.111657Z"}}'
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"UCeTfv--alDifkRUpZcCarhA"},"created_at":{"S":"2025-10-31T22:53:12.174433Z"}}'
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"UCaxPNkUMQKqepAp0JbpVrrw"},"created_at":{"S":"2025-10-31T22:53:12.147643Z"}}'
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"UCpId7ndfjv4pHJUVzRbUYug"},"created_at":{"S":"2025-10-31T22:53:12.169181Z"}}'
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"test-channel-assistants-001"},"created_at":{"S":"2025-11-02T23:13:26.882535Z"}}'
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"UCfgKNiC2S7JkErHkoONIUVA"},"created_at":{"S":"2025-10-31T22:53:12.135040Z"}}'
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"test_channel_123"},"created_at":{"S":"2025-10-31T18:25:48.226375Z"}}'
aws dynamodb delete-item --table-name GeneratedContent --region eu-central-1 --key '{"channel_id":{"S":"UC9KUaoTY4vyGGHzCccqHnAA"},"created_at":{"S":"2025-10-31T22:53:12.154821Z"}}'

echo "✅ Deleted all test records"
echo "✅ Kept: The Forgotten Goddess of Destiny Threads"
