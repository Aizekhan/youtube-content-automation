# YouTube Content Automation - Technical Architecture
**Last Updated:** 2025-11-29
**Version:** 2.0 (Multi-Tenant with S3 State Offloading)

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Multi-Tenant Architecture](#multi-tenant-architecture)
3. [Authentication & Authorization](#authentication--authorization)
4. [Content Generation Pipeline](#content-generation-pipeline)
5. [S3 State Offloading Pattern](#s3-state-offloading-pattern)
6. [Data Flow Architecture](#data-flow-architecture)
7. [Lambda Functions Reference](#lambda-functions-reference)
8. [Database Schema](#database-schema)
9. [Cost Tracking](#cost-tracking)
10. [Deployment Guide](#deployment-guide)

---

## System Overview

### What This System Does
Automated YouTube content generation platform that creates complete video content including:
- AI-generated narrative scripts
- AI-generated images (via Stable Diffusion 3.5)
- Text-to-speech audio narration
- Call-to-action segments
- Video assembly
- YouTube-ready metadata (titles, descriptions, thumbnails)

### Key Capabilities
- **Multi-Tenant:** Supports multiple users with complete data isolation
- **Multi-Channel:** Single user can manage up to 38+ channels
- **Genre-Adaptive:** 20+ supported genres (Horror, Philosophy, History, etc.)
- **Parallel Processing:** Generates content for multiple channels simultaneously
- **Cost-Efficient:** Automated cost tracking and optimization

### Technology Stack
- **Orchestration:** AWS Step Functions (state machine)
- **Compute:** AWS Lambda (serverless functions)
- **Storage:** AWS S3 (media files), DynamoDB (metadata)
- **Authentication:** AWS Cognito (Google OAuth)
- **AI Services:**
  - OpenAI GPT-4o (narrative generation)
  - AWS Bedrock / Replicate (image generation)
  - AWS Polly Neural / ElevenLabs (text-to-speech)
- **Frontend:** Static HTML/JS hosted on EC2

---

## Multi-Tenant Architecture

### Why Multi-Tenant?
The system was designed to support multiple independent content creators, each managing their own channels, with complete data isolation and security.

### User Isolation Model
```
User (Google Account)
  ├─ user_id: c334d862-4031-7097-4207-84856b59d3ed
  ├─ Channels (1-38+)
  │   ├─ HorrorWhisper Studio
  │   ├─ AncientLight
  │   └─ DivineRemnants
  ├─ Generated Content (filtered by user_id)
  └─ Cost Tracking (per user)
```

### Data Isolation Strategy
Every DynamoDB table includes `user_id` field:
- **ChannelConfigs:** User's channel configurations
- **GeneratedContent:** User's generated videos
- **CostTracking:** User's API usage costs

**Global Secondary Index (GSI):** `user_id-channel_id-index` for efficient queries

---

## Authentication & Authorization

### Authentication Flow
```
1. User clicks "Sign in with Google" → login.html
2. Redirect to AWS Cognito hosted UI
3. Google OAuth authentication
4. Cognito returns JWT tokens → callback.html
5. Tokens saved in cookies (5 separate cookies to avoid 4KB limit)
6. All API requests include user_id from decoded JWT
```

### Cookie-Based Session Storage
**Why Cookies Instead of localStorage?**
- Browser Tracking Prevention blocks localStorage/sessionStorage
- Cookies bypass these restrictions

**Session Split Across 5 Cookies:**
```javascript
auth_id_token       // ~1500 bytes - Identity token
auth_access_token   // ~1500 bytes - API access
auth_refresh_token  // ~1000 bytes - Refresh token
auth_user           // ~200 bytes  - User info
auth_expires        // ~30 bytes   - Expiration
```

**Security:**
- `SameSite=Lax` prevents CSRF attacks
- 7-day expiration
- HTTPS only (production)

### Authorization Pattern
Every Lambda function extracts user_id:
```python
# From Step Functions (direct)
user_id = event.get('user_id')

# From Function URL (body)
body = json.loads(event['body'])
user_id = body.get('user_id')

# Query DynamoDB with user_id filter
response = table.query(
    IndexName='user_id-channel_id-index',
    KeyConditionExpression='user_id = :uid',
    ExpressionAttributeValues={':uid': user_id}
)
```

---

## Content Generation Pipeline

### Three-Phase Architecture

```
PHASE 1: Content Generation (Parallel per channel)
┌─────────────────────────────────────────────┐
│ For Each Active Channel (parallel):        │
│  1. QueryTitles     - Get trending topics  │
│  2. ThemeAgent      - Generate titles      │
│  3. Narrative       - Generate full story  │
│  4. SaveToS3        - Save to S3          │
│  5. Return S3 ref   - Only reference      │
└─────────────────────────────────────────────┘
              ↓
PHASE 2: Image Generation (Batched)
┌─────────────────────────────────────────────┐
│  1. LoadFromS3      - Load all narratives  │
│  2. CollectPrompts  - Extract image prompts│
│  3. StartEC2        - Launch SD3.5 instance│
│  4. GenerateImages  - Batch all images     │
│  5. DistributeImages- Return to channels   │
│  6. StopEC2         - Terminate instance   │
└─────────────────────────────────────────────┘
              ↓
PHASE 3: Audio & Save (Parallel per channel)
┌─────────────────────────────────────────────┐
│ For Each Channel (parallel):               │
│  1. GenerateSSML    - Create TTS markup    │
│  2. GenerateAudio   - Polly/ElevenLabs TTS │
│  3. GenerateCTA     - Call-to-action audio │
│  4. SaveContent     - Save to DynamoDB     │
│  5. VideoAssembly   - Create final video   │
└─────────────────────────────────────────────┘
```

### Why This Architecture?

**Phase 1 Parallel:**
- Each channel is independent
- Can process 5-38 channels simultaneously
- MaxConcurrency: 5 (to avoid API rate limits)

**Phase 2 Batched:**
- EC2 startup is expensive (2-3 minutes)
- Better to start EC2 once for all channels
- Batch all image generation together
- Single EC2 instance handles 6-200 images

**Phase 3 Parallel:**
- Audio generation is independent per channel
- TTS APIs are fast (no EC2 startup)
- Final save is per-channel

---

## S3 State Offloading Pattern

### The Problem
**AWS Step Functions Limit:** 256KB maximum state size

**Scenario:**
- Processing 38 channels
- Each channel's narrative: ~15-20KB
- Total: 38 × 20KB = 760KB ❌ **Exceeds limit!**

### The Solution: S3 State Offloading

```
┌─────────────────────────────────────────────────────────┐
│ BEFORE (Failed with 38 channels):                      │
├─────────────────────────────────────────────────────────┤
│ Phase1 Map → Returns full narrative data (760KB)       │
│ Step Functions state → EXCEEDED 256KB LIMIT ❌          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ AFTER (Works with 38 channels):                         │
├─────────────────────────────────────────────────────────┤
│ Phase1 Map → Save to S3 → Return S3 reference (200B)   │
│ Step Functions state → 38 × 200B = 7.6KB ✅             │
│ Later: Load from S3 only when needed                    │
└─────────────────────────────────────────────────────────┘
```

### Implementation

**1. Save to S3 (End of Phase1 Iterator):**
```python
# save-phase1-to-s3 Lambda
def lambda_handler(event, context):
    # Save full narrative data to S3
    s3_key = f"phase1-results/{user_id}/{channel_id}/{timestamp}.json"
    s3_client.put_object(
        Bucket='youtube-automation-data-grucia',
        Key=s3_key,
        Body=json.dumps(event)
    )

    # Return ONLY small reference
    return {
        'channel_id': channel_id,
        's3_bucket': 'youtube-automation-data-grucia',
        's3_key': s3_key,
        'timestamp': timestamp
    }
```

**2. Extract Reference Only (Step Functions Pass State):**
```json
{
  "ExtractS3ReferenceOnly": {
    "Type": "Pass",
    "Comment": "Return ONLY S3 reference to avoid state size limit",
    "Parameters": {
      "s3_reference.$": "$.s3Result.s3_reference"
    },
    "End": true
  }
}
```

**3. Load from S3 When Needed:**
```python
# collect-all-image-prompts Lambda
def lambda_handler(event, context):
    s3_references = event.get('s3_references', [])

    for ref in s3_references:
        # Load full data from S3
        response = s3_client.get_object(
            Bucket=ref['s3_bucket'],
            Key=ref['s3_key']
        )
        channel_data = json.loads(response['Body'].read())
        # Extract image prompts...
```

### Benefits
✅ **Scalability:** Can process unlimited channels
✅ **State Size:** Step Functions state stays under 10KB
✅ **Persistence:** S3 data preserved for debugging
✅ **Cost:** S3 storage is cheap ($0.023/GB/month)

---

## Data Flow Architecture

### Complete Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│ USER INITIATES                                               │
│ https://n8n-creator.space/                                   │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ AUTHENTICATION                                               │
│ - Google OAuth via Cognito                                   │
│ - JWT tokens stored in 5 cookies                            │
│ - user_id: c334d862-4031-7097-4207-84856b59d3ed            │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ STEP FUNCTIONS EXECUTION                                     │
│ Input: {"user_id": "...", "active_only": true}             │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ PHASE 1: CONTENT GENERATION (Parallel)                      │
│                                                              │
│ GetActiveChannels (user_id filter)                          │
│   ↓                                                          │
│ Map (MaxConcurrency: 5) - For each channel:                │
│   ├─ QueryTitles     → OpenAI                              │
│   ├─ ThemeAgent      → OpenAI GPT-4o                       │
│   ├─ Narrative       → OpenAI GPT-4o                       │
│   ├─ SaveToS3        → s3://.../{user_id}/{channel_id}/... │
│   └─ Return          → {s3_reference}                       │
│                                                              │
│ Result: [{s3_reference}, {s3_reference}, ...]              │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ PHASE 2: IMAGE GENERATION (Batched)                         │
│                                                              │
│ CollectAllImagePrompts                                       │
│   ├─ Load from S3 (all channels)                           │
│   └─ Extract all image prompts                             │
│                                                              │
│ StartEC2                                                     │
│   └─ Launch t3.2xlarge with SD3.5                          │
│                                                              │
│ GenerateAllImagesBatched                                     │
│   ├─ Send all prompts to EC2                               │
│   └─ Return all generated images                            │
│                                                              │
│ DistributeImagesToChannels                                   │
│   ├─ Load Phase1 from S3                                   │
│   └─ Match images to channels                              │
│                                                              │
│ StopEC2                                                      │
│   └─ Terminate instance                                     │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ PHASE 3: AUDIO & SAVE (Parallel)                           │
│                                                              │
│ Map (MaxConcurrency: 5) - For each channel:                │
│   ├─ GenerateSSML    → SSML markup                         │
│   ├─ GenerateAudio   → AWS Polly Neural                    │
│   ├─ GenerateCTA     → CTA audio                           │
│   ├─ SaveContent     → DynamoDB (with user_id)             │
│   └─ VideoAssembly   → Lambda or ECS Fargate               │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ RESULT                                                       │
│ - Content saved to DynamoDB with user_id                    │
│ - Visible on https://n8n-creator.space/content.html        │
│ - Filtered by authenticated user                            │
└──────────────────────────────────────────────────────────────┘
```

### Active Channel Filtering

**Why Filter by Active Status?**

```
Total Channels: 38
├─ Active: 1 (HorrorWhisper Studio)
└─ Inactive: 37

Problem: Processing all 38 channels is expensive
Solution: Process only active channels by default
```

**Implementation:**
```json
// Step Functions Input
{
  "user_id": "c334d862-4031-7097-4207-84856b59d3ed",
  "active_only": true  // Default: only active channels
}
```

**Lambda Filter:**
```python
# content-get-channels
active_only = event.get('active_only', True)

for item in items:
    if active_only and not item.get('is_active', False):
        continue  # Skip inactive channels
```

**Result:** Cost savings of 97% (1 channel vs 38)

---

## Lambda Functions Reference

### Authentication & Data Access

**content-get-channels**
- **Purpose:** Get user's channels (with active filter)
- **Input:** `{user_id, active_only}`
- **Output:** `[{channel_id, config_id, channel_name, genre}]`
- **Multi-Tenant:** Queries by user_id GSI

**dashboard-content**
- **Purpose:** Get user's generated content
- **Input:** `{user_id, limit, lastKey}`
- **Output:** Paginated content list
- **Multi-Tenant:** Filters by user_id

**dashboard-costs**
- **Purpose:** Get user's API costs
- **Input:** `{user_id, start_date, end_date}`
- **Output:** Cost breakdown by service
- **Multi-Tenant:** Filters by user_id

### Phase 1: Content Generation

**content-query-titles**
- **Purpose:** Get trending YouTube titles for genre
- **Input:** `{channel_id, genre}`
- **Output:** `{titles: [...]}` (mock data currently)

**content-theme-agent**
- **Purpose:** Generate 4 title variations
- **AI:** OpenAI GPT-4o
- **Input:** `{channel_id, genre, titles}`
- **Output:** `{generated_titles: [...]}`

**content-narrative**
- **Purpose:** Generate complete narrative
- **AI:** OpenAI GPT-4o
- **Input:** `{channel_id, selected_topic}`
- **Output:** Full story with scenes, image prompts, metadata

**save-phase1-to-s3**
- **Purpose:** Save Phase1 results to S3
- **Input:** All Phase1 data (queryResult, themeResult, narrativeResult)
- **Output:** `{s3_bucket, s3_key, timestamp}` (200 bytes)
- **S3 Path:** `phase1-results/{user_id}/{channel_id}/{timestamp}.json`

### Phase 2: Image Generation

**collect-all-image-prompts**
- **Purpose:** Load Phase1 from S3 and collect image prompts
- **Input:** `{s3_references: [{s3_bucket, s3_key}]}`
- **Output:** `{all_image_prompts: [...], total_images, provider}`

**ec2-sd35-control**
- **Purpose:** Start/Stop EC2 with Stable Diffusion 3.5
- **Input:** `{action: "start" | "stop"}`
- **Output:** `{endpoint: "http://...", state}`

**content-generate-images**
- **Purpose:** Generate all images via EC2
- **AI:** Stable Diffusion 3.5 Large
- **Input:** `{all_prompts, ec2_endpoint, batch_mode: true}`
- **Output:** `{scene_images: [{image_url, cost}]}`

**distribute-images**
- **Purpose:** Match images back to channels
- **Input:** `{generated_images, channels_data}`
- **Output:** `{channels_with_images: [...]}`

### Phase 3: Audio & Save

**ssml-generator**
- **Purpose:** Generate SSML markup for Polly
- **Input:** `{scenes, tts_service, genre}`
- **Output:** `{scenes: [{ssml_text}]}`

**content-audio-polly**
- **Purpose:** Generate TTS audio via AWS Polly
- **Input:** `{scenes, voice_profile}`
- **Output:** `{audio_files: [{s3_url}], cost}`

**content-cta-audio**
- **Purpose:** Generate CTA audio
- **Input:** `{cta_segments, voice_config}`
- **Output:** `{cta_audio_files: [...]}`

**content-save-result**
- **Purpose:** Save final content to DynamoDB
- **Input:** All content data + user_id
- **Multi-Tenant:** Saves with user_id field
- **Output:** `{content_id, status}`

**content-video-assembly**
- **Purpose:** Assemble final video
- **Input:** `{content_id, channel_id}`
- **Routing:** Lambda (<15 min) or ECS Fargate (15+ min)
- **Output:** `{video_url}`

---

## Database Schema

### ChannelConfigs
```json
{
  "config_id": "cfg_1761314021521547018_UCaxPNkUMQ",  // PK
  "user_id": "c334d862-4031-7097-4207-84856b59d3ed",
  "channel_id": "UCaxPNkUMQKqepAp0JbpVrrw",
  "channel_name": "HorrorWhisper Studio",
  "genre": "Horror",
  "is_active": true,
  "tts_service": "aws_polly_neural",
  "tts_voice_profile": "deep_male",
  "image_provider": "ec2-sd35",
  "created_at": "2025-11-20T15:30:21Z",
  "updated_at": "2025-11-28T10:15:00Z"
}
```

**GSI:** `user_id-channel_id-index`

### GeneratedContent
```json
{
  "channel_id": "UCaxPNkUMQKqepAp0JbpVrrw",  // PK
  "created_at": "2025-11-28T23:28:40Z",      // SK
  "user_id": "c334d862-4031-7097-4207-84856b59d3ed",
  "content_id": "20251128T232840",
  "story_title": "The Curse of the Abandoned Manor House",
  "genre": "Horror",
  "scenes": [...],
  "audio_files": [{
    "s3_url": "s3://youtube-automation-audio-files/...",
    "duration_seconds": 45.2
  }],
  "generated_images": [{
    "scene_number": 1,
    "s3_url": "s3://youtube-automation-audio-files/images/..."
  }],
  "video_url": "s3://...",
  "metadata": {
    "total_scenes": 5,
    "total_duration": 320.5,
    "character_count": 1829
  },
  "costs": {
    "narrative_cost": 0.025,
    "image_cost": 0.24,
    "tts_cost": 0.18,
    "total_cost": 0.445
  }
}
```

**GSI:** `user_id-created_at-index`

### CostTracking
```json
{
  "date": "2025-11-28",           // PK
  "timestamp": "2025-11-28T23:28:40Z",  // SK
  "user_id": "c334d862-4031-7097-4207-84856b59d3ed",
  "service": "openai_gpt4o",
  "operation": "narrative_generation",
  "cost_usd": 0.025,
  "channel_id": "UCaxPNkUMQKqepAp0JbpVrrw",
  "content_id": "20251128T232840",
  "details": {
    "input_tokens": 1200,
    "output_tokens": 3500,
    "model": "gpt-4o"
  }
}
```

**GSI:** `user_id-date-index`

---

## Cost Tracking

### Services Tracked
1. **OpenAI GPT-4o** - Narrative generation
2. **AWS Polly Neural** - Text-to-speech
3. **ElevenLabs** - Premium TTS
4. **Replicate / Bedrock** - Image generation
5. **AWS Lambda** - Compute costs
6. **AWS S3** - Storage costs

### Cost Per Video (Estimated)
```
Content Generation:
├─ Theme Agent (GPT-4o):        $0.005
├─ Narrative (GPT-4o):          $0.020
├─ Image Gen (6 images):        $0.240
├─ TTS Audio (Polly):           $0.180
├─ CTA Audio:                   $0.020
├─ Video Assembly:              $0.015
└─ Total:                       $0.48 per video
```

### Monthly Costs (1 video/day, 30 days)
```
Single Channel:  $0.48 × 30 = $14.40/month
38 Channels:     $14.40 × 38 = $547/month
Active Only (1): $14.40/month ✅
```

---

## Deployment Guide

### Prerequisites
- AWS Account with appropriate permissions
- AWS CLI configured
- Python 3.11
- Node.js 18+

### Step 1: Deploy Lambda Functions
```bash
cd aws/lambda/content-narrative
python create_zip.py
aws lambda update-function-code \
  --function-name content-narrative \
  --zip-file fileb://function.zip \
  --region eu-central-1
```

### Step 2: Deploy Step Functions
```bash
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator \
  --definition file://step-function-with-active-filter.json \
  --region eu-central-1
```

### Step 3: Update Frontend
```bash
scp -i /path/to/key.pem \
  content.html \
  ubuntu@3.75.97.188:/home/ubuntu/n8n-docker/html/
```

### Step 4: Verify Multi-Tenant
```bash
# Test with user_id
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:...:stateMachine:ContentGenerator \
  --input '{"user_id":"c334d862-4031-7097-4207-84856b59d3ed","active_only":true}'
```

---

## Troubleshooting

### Issue: DataLimitExceeded Error
**Symptom:** Step Functions fails with "state size exceeds 256KB"
**Cause:** Processing too many channels without S3 offloading
**Solution:** Ensure S3 offloading is enabled, or reduce channel count

### Issue: Missing user_id in Content
**Symptom:** Content saved but user_id is null
**Cause:** Lambda not receiving user_id from Step Functions
**Solution:** Check Step Functions passes user_id through entire workflow

### Issue: Authentication Redirects Loop
**Symptom:** Infinite redirect between login.html and index.html
**Cause:** Cookies not being set properly
**Solution:** Check browser allows cookies, check auth.js cookie logic

### Issue: No Active Channels Found
**Symptom:** Step Functions completes but generates no content
**Cause:** All channels have is_active=false
**Solution:** Set at least one channel to is_active=true in DynamoDB

---

## Performance Metrics

### Execution Times (1 Active Channel)
```
Phase 1 (Content Generation):    ~30-40 seconds
Phase 2 (Image Generation):       ~3-4 minutes
Phase 3 (Audio & Save):           ~1-2 minutes
Total:                            ~5-7 minutes
```

### Execution Times (5 Active Channels)
```
Phase 1 (Parallel):               ~30-40 seconds
Phase 2 (Batched):                ~5-8 minutes
Phase 3 (Parallel):               ~1-2 minutes
Total:                            ~7-10 minutes
```

### Execution Times (38 Channels - With S3)
```
Phase 1 (Parallel, MaxConcurrency: 5):  ~3-4 minutes
Phase 2 (Batched):                      ~15-20 minutes
Phase 3 (Parallel, MaxConcurrency: 5):  ~3-4 minutes
Total:                                  ~22-28 minutes
```

---

## Future Enhancements

### Planned Features
1. **SQS-Based Queuing** - For processing 100+ channels
2. **Scheduled Generation** - Daily/weekly automatic runs
3. **Template Management** - Custom templates per channel
4. **Analytics Dashboard** - Video performance tracking
5. **YouTube Auto-Upload** - Direct upload to YouTube
6. **A/B Testing** - Test multiple thumbnails/titles

### Architecture Improvements
1. **Distributed Map** - Native Step Functions support for 10,000+ parallel tasks
2. **EventBridge Integration** - Event-driven triggers
3. **DynamoDB Streams** - Real-time cost tracking
4. **CloudWatch Dashboards** - System monitoring

---

**Documentation Maintained By:** Claude Code
**Last Reviewed:** 2025-11-29
**Contact:** Support via GitHub Issues
