#!/usr/bin/env python3
"""
Create Phase2ParallelGeneration for Step Function
Adds parallel processing of Images and Audio
"""
import json

# Read current Step Function
with open('/tmp/current-sf.json', 'r') as f:
    sf = json.load(f)

# Extract current image generation states (to move into Branch A)
image_states = {}
for state_name in ['CheckIfAnyImages', 'PreparePhase3WithoutImages', 'StartEC2ForAllImages',
                   'CheckEC2Result', 'GenerateAllImagesBatched', 'DistributeImagesToChannels',
                   'StopEC2AfterImages', 'QueueForRetry', 'WaitForRetrySystem']:
    if state_name in sf['States']:
        image_states[state_name] = sf['States'][state_name]
        # Remove from top level (will be in branch)
        del sf['States'][state_name]

# FIX: Branch states cannot reference states outside the branch
# Change all "Next: Phase3AudioAndSave" to "End: true"
for state_name, state_def in image_states.items():
    if state_def.get('Next') == 'Phase3AudioAndSave':
        del state_def['Next']
        state_def['End'] = True
    # Also fix Catch clauses
    if 'Catch' in state_def:
        for catch in state_def['Catch']:
            if catch.get('Next') == 'Phase3AudioAndSave':
                catch['Next'] = 'PreparePhase3WithoutImages'  # Stay within branch

# Create Branch A: Images
branch_a_images = {
    "StartAt": "CheckIfAnyImages",
    "States": image_states
}

# Create Branch B: Audio (NEW)
branch_b_audio = {
    "StartAt": "StartEC2Qwen3",
    "States": {
        "StartEC2Qwen3": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Comment": "Start EC2 Qwen3-TTS instance",
            "Parameters": {
                "FunctionName": "arn:aws:lambda:eu-central-1:599297130956:function:ec2-qwen3-control",
                "Payload": {
                    "action": "start"
                }
            },
            "ResultPath": "$.qwen3Endpoint",
            "Next": "WaitForQwen3ModelsLoading",
            "Retry": [{
                "ErrorEquals": ["States.ALL"],
                "IntervalSeconds": 10,
                "MaxAttempts": 3,
                "BackoffRate": 2
            }]
        },
        "WaitForQwen3ModelsLoading": {
            "Type": "Wait",
            "Comment": "Wait 3 minutes for models to load",
            "Seconds": 180,
            "Next": "CheckQwen3Health"
        },
        "CheckQwen3Health": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Comment": "Check if Qwen3-TTS service is healthy",
            "Parameters": {
                "FunctionName": "arn:aws:lambda:eu-central-1:599297130956:function:check-qwen3-health",
                "Payload": {
                    "endpoint.$": "$.qwen3Endpoint.Payload.endpoint"
                }
            },
            "ResultPath": "$.qwen3Health",
            "Next": "IsQwen3Healthy",
            "Retry": [{
                "ErrorEquals": ["States.ALL"],
                "IntervalSeconds": 5,
                "MaxAttempts": 2,
                "BackoffRate": 1.5
            }]
        },
        "IsQwen3Healthy": {
            "Type": "Choice",
            "Comment": "Check if service is healthy",
            "Choices": [{
                "Variable": "$.qwen3Health.Payload.healthy",
                "BooleanEquals": True,
                "Next": "Qwen3Ready"
            }],
            "Default": "WaitBeforeRetryHealth"
        },
        "WaitBeforeRetryHealth": {
            "Type": "Wait",
            "Comment": "Wait 30s before retry",
            "Seconds": 30,
            "Next": "CheckQwen3Health"
        },
        "Qwen3Ready": {
            "Type": "Pass",
            "Comment": "Qwen3-TTS is ready",
            "Result": {"qwen3_ready": True},
            "ResultPath": "$.qwen3ReadyFlag",
            "Next": "CollectAudioScenes"
        },
        "CollectAudioScenes": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
                "FunctionName": "arn:aws:lambda:eu-central-1:599297130956:function:collect-audio-scenes",
                "Payload": {
                    "channels_data.$": "$.phase1Results",
                    "ec2_endpoint.$": "$.qwen3Endpoint.Payload.endpoint"
                }
            },
            "ResultSelector": {
                "all_audio_scenes.$": "$.Payload.all_audio_scenes",
                "all_cta_segments.$": "$.Payload.all_cta_segments",
                "total_scenes.$": "$.Payload.total_scenes",
                "total_cta.$": "$.Payload.total_cta",
                "total_audio_files.$": "$.Payload.total_audio_files",
                "channels_count.$": "$.Payload.channels_count",
                "ec2_endpoint.$": "$.Payload.ec2_endpoint"
            },
            "ResultPath": "$.audioCollectionResult",
            "Next": "GenerateAudioBatch"
        },
        "GenerateAudioBatch": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
                "FunctionName": "arn:aws:lambda:eu-central-1:599297130956:function:content-audio-qwen3tts",
                "Payload": {
                    "all_audio_scenes.$": "$.audioCollectionResult.all_audio_scenes",
                    "all_cta_segments.$": "$.audioCollectionResult.all_cta_segments",
                    "ec2_endpoint.$": "$.qwen3Endpoint.Payload.endpoint"
                }
            },
            "ResultSelector": {
                "generated_audio.$": "$.Payload.audio_files",
                "cta_generated_audio.$": "$.Payload.cta_audio_files",
                "total_files.$": "$.Payload.total_files",
                "total_duration_ms.$": "$.Payload.total_duration_ms"
            },
            "ResultPath": "$.audioGenerationResult",
            "Next": "DistributeAudioToChannels",
            "TimeoutSeconds": 900,
            "Retry": [{
                "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
                "IntervalSeconds": 2,
                "MaxAttempts": 3,
                "BackoffRate": 2.0
            }]
        },
        "DistributeAudioToChannels": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
                "FunctionName": "arn:aws:lambda:eu-central-1:599297130956:function:distribute-audio",
                "Payload": {
                    "generated_audio.$": "$.audioGenerationResult.generated_audio",
                    "cta_generated_audio.$": "$.audioGenerationResult.cta_generated_audio",
                    "channels_data.$": "$.phase1Results"
                }
            },
            "ResultSelector": {
                "channels_with_audio.$": "$.Payload.channels_with_audio"
            },
            "ResultPath": "$.audioDistributionResult",
            "End": True
        }
    }
}

# Create Phase2ParallelGeneration
phase2_parallel = {
    "Type": "Parallel",
    "Comment": "Generate images and prepare audio EC2 in PARALLEL for speed",
    "Branches": [branch_a_images, branch_b_audio],
    "ResultPath": "$.phase2Results",
    "Next": "MergeChannelData"
}

# Insert Phase2ParallelGeneration after CollectAllImagePrompts
sf['States']['CollectAllImagePrompts']['Next'] = 'Phase2ParallelGeneration'
sf['States']['Phase2ParallelGeneration'] = phase2_parallel

# Add MergeChannelData state
sf['States']['MergeChannelData'] = {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Comment": "Merge images and audio data from parallel branches",
    "Parameters": {
        "FunctionName": "arn:aws:lambda:eu-central-1:599297130956:function:merge-channel-data",
        "Payload": {
            "images_branch.$": "$.phase2Results[0]",
            "audio_branch.$": "$.phase2Results[1]",
            "phase1_results.$": "$.phase1Results"
        }
    },
    "ResultSelector": {
        "merged_channels.$": "$.Payload.merged_channels",
        "qwen3_endpoint.$": "$.Payload.qwen3_endpoint"
    },
    "ResultPath": "$.mergedChannels",
    "Next": "Phase3AudioAndSave"
}

# Update Phase3AudioAndSave to use merged channels
sf['States']['Phase3AudioAndSave']['ItemsPath'] = '$.mergedChannels.Payload.merged_channels'

# Update Phase3 to pass qwen3_endpoint
sf['States']['Phase3AudioAndSave']['Parameters'] = {
    "user_id.$": "$$.Map.Item.Value.user_id",
    "channel_item.$": "$$.Map.Item.Value.channel_item",
    "queryResult.$": "$$.Map.Item.Value.queryResult",
    "themeResult.$": "$$.Map.Item.Value.themeResult",
    "narrativeResult.$": "$$.Map.Item.Value.narrativeResult",
    "scene_images.$": "$$.Map.Item.Value.scene_images",
    "images_count.$": "$$.Map.Item.Value.images_count",
    "qwen3_endpoint.$": "$.mergedChannels.Payload.qwen3_endpoint",
    "audio_files.$": "$$.Map.Item.Value.audio_files",
    "cta_audio_files.$": "$$.Map.Item.Value.cta_audio_files"
}

# Remove old audio generation from Phase3 Iterator
phase3_iterator = sf['States']['Phase3AudioAndSave']['Iterator']['States']

# Remove GenerateSSML, GenerateAudioQwen3, GenerateCTAAudio
if 'GenerateSSML' in phase3_iterator:
    del phase3_iterator['GenerateSSML']
if 'GenerateAudioQwen3' in phase3_iterator:
    del phase3_iterator['GenerateAudioQwen3']
if 'GenerateCTAAudio' in phase3_iterator:
    del phase3_iterator['GenerateCTAAudio']

# Update GetTTSConfig to go directly to SaveFinalContent
phase3_iterator['GetTTSConfig']['Next'] = 'SaveFinalContent'

# Add StopEC2Qwen3AfterPhase3 state
sf['States']['StopEC2Qwen3AfterPhase3'] = {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Comment": "Stop EC2 Qwen3 after Phase3 completes",
    "Parameters": {
        "FunctionName": "arn:aws:lambda:eu-central-1:599297130956:function:ec2-qwen3-control",
        "Payload": {
            "action": "stop",
            "execution_arn.$": "$$.Execution.Id"
        }
    },
    "ResultPath": "$.qwen3StopResult",
    "End": True
}

# Update Phase3AudioAndSave to continue to StopEC2Qwen3AfterPhase3
# Remove 'End' if it exists (can't have both Next and End)
if 'End' in sf['States']['Phase3AudioAndSave']:
    del sf['States']['Phase3AudioAndSave']['End']
sf['States']['Phase3AudioAndSave']['Next'] = 'StopEC2Qwen3AfterPhase3'

# Save modified Step Function
with open('/tmp/new-sf.json', 'w') as f:
    json.dump(sf, f, indent=2)

print("Created new Step Function definition")
print("Added Phase2ParallelGeneration with Images + Audio branches")
print("Moved audio generation to Phase2B")
print("Removed old audio states from Phase3")
print("Added MergeChannelData and StopEC2Qwen3AfterPhase3")
print()
print("File saved: /tmp/new-sf.json")
