# Episode 1 Generation - Issues Summary

## Timeline
**Started**: 2026-02-25 00:09:00
**Multiple attempts**: 4 failed executions
**Current status**: FAILED at ExtractTopicData state

## Root Causes Found

### 1. ✅ FIXED: Wrong topic status
- **Problem**: Created topics with `status='pending'`
- **Expected**: GetNextTopic Lambda searches for `status='approved'` or `status='queued'`
- **Fix**: Updated all 10 episodes to `status='queued'`
- **Script**: `fix-episodes-status.py`

### 2. ✅ FIXED: Missing user_id
- **Problem**: Topics created without `user_id` field
- **Expected**: GetNextTopic filters topics by `user_id` for security
- **Fix**: Added `user_id='c334d862-4031-7097-4207-84856b59d3ed'` to all episodes
- **Script**: `add-user-id-to-episodes.py`

### 3. ✅ FIXED: Wrong channel_id
- **Problem**: Used `channel_id='UCwohlVtx4LVoo4qfrTIb6jw'` (non-existent channel)
- **Expected**: BeastCodeX channel = `UCq4jkW2gvAq_qUPcWzSgEig`
- **Context**: "Mask of Gods" is a SERIES on BeastCodeX channel, not a separate channel
- **Fix**: Moved all 10 episodes to correct channel_id
- **Script**: `fix-channel-id-for-series.py`

### 4. ❌ NOT FIXED: series_metadata structure mismatch
- **Problem**: GetNextTopic Lambda reads `next_topic.get('series_id')` but data is in `next_topic.get('series_metadata', {}).get('series_id')`
- **Error**: `JSONPath '$.topicResult.data.topic.series_id' could not be found`
- **Also affects**: `topic_text` is stored as `topic` field, not `topic_text`
- **Impact**: Step Functions ExtractTopicData state fails because series_id, episode_number missing from response
- **Needs**: Update GetNextTopic Lambda code to support both old and new structure

## Required Lambda Fix

**File**: `aws/lambda/content-topics-get-next/lambda_function.py:305-326`

**Current code**:
```python
topic_response = {
    'topic_text': next_topic.get('topic_text'),  # ❌ Field is 'topic'
    ...
}

if next_topic.get('series_id'):  # ❌ Field is in series_metadata
    topic_response['series_id'] = next_topic.get('series_id')
    topic_response['episode_number'] = next_topic.get('episode_number')
```

**Required fix**:
```python
# Support both field names
series_metadata = next_topic.get('series_metadata', {})
series_id = series_metadata.get('series_id') or next_topic.get('series_id')

topic_response = {
    'topic_text': next_topic.get('topic') or next_topic.get('topic_text'),
    ...
}

if series_id:
    topic_response['series_id'] = series_id
    episode_number = series_metadata.get('episode_number') or next_topic.get('episode_number')
    if episode_number:
        topic_response['episode_number'] = int(episode_number)
```

## Lessons Learned

### For future Python scripts creating series topics:
1. **NEVER hardcode channel_id** - always fetch from DynamoDB ChannelConfigs
2. **Use correct status** - `'queued'` or `'approved'`, NOT `'pending'`
3. **Always include user_id** - required for GetNextTopic security filtering
4. **Match DynamoDB structure** - use `series_metadata` nested map as per schema

### Best practice template:
```python
# Get channel config from DynamoDB
response = dynamodb.get_item(
    TableName='ChannelConfigs',
    Key={'config_id': {'S': 'beastcodex'}}
)
channel_id = response['Item']['channel_id']['S']
user_id = response['Item']['user_id']['S']

# Create topic with correct structure
item = {
    'channel_id': {'S': channel_id},      # From DynamoDB
    'user_id': {'S': user_id},            # From DynamoDB
    'status': {'S': 'queued'},            # queued/approved only
    'topic': {'S': topic_text},           # Note: 'topic' not 'topic_text'
    'series_metadata': {
        'M': {
            'series_id': {'S': series_id},
            'episode_number': {'N': str(ep_num)},
            'series_title': {'S': series_title},
            'total_episodes': {'N': '10'}
        }
    }
}
```

## Next Steps

1. Update GetNextTopic Lambda to support series_metadata structure
2. Deploy updated Lambda
3. Re-run Episode 1 generation
4. Verify:
   - SeriesState created with episodes_generated=1
   - Characters extracted from episode summary
   - Multi-voice TTS with character-specific voices

## Execution ARNs
- Failed (wrong channel): `mask-of-gods-ep1-real-1771971371`
- Failed (ExtractTopicData): `mask-of-gods-ep1-correct-1771972939`
