"""
Lambda: collect-all-image-prompts
Collects image prompts from all channels and creates global batches
"""
import json


def lambda_handler(event, context):
    """
    Input: Array of results from Phase 1 content generation
    [
        {
            "channel_id": "...",
            "content_id": "...",
            "image_data": {"scenes": [...]},
            "narrative_data": {...},
            "audio_files": [...]
        }
    ]

    Output: Global batches with all prompts from all channels
    {
        "global_batches": [
            {
                "batch_id": 0,
                "items": [
                    {
                        "channel_id": "...",
                        "content_id": "...",
                        "scene_number": 1,
                        "image_prompt": "...",
                        "negative_prompt": "..."
                    }
                ]
            }
        ],
        "channels_metadata": {
            "channel_id": {
                "content_id": "...",
                "total_scenes": 5,
                "narrative_data": {...},
                "audio_files": [...]
            }
        }
    }
    """

    print("📦 Collecting image prompts from all channels...")

    # Get phase 1 results
    phase1_results = event.get('phase1_results', [])

    if not phase1_results:
        print("⚠️  No results from phase 1")
        return {
            'global_batches': [],
            'channels_metadata': {},
            'total_prompts': 0
        }

    # Collect all prompts from all channels
    all_prompts = []
    channels_metadata = {}

    for result in phase1_results:
        channel_id = result.get('channel_id')
        content_id = result.get('content_id')
        image_data = result.get('image_data', {})

        if not channel_id or not content_id:
            continue

        # Store metadata for this channel
        channels_metadata[channel_id] = {
            'content_id': content_id,
            'narrative_data': result.get('narrative_data', {}),
            'audio_files': result.get('audio_files', []),
            'selected_topic': result.get('selected_topic', {}),
            'sfx_data': result.get('sfx_data', {}),
            'cta_data': result.get('cta_data', {}),
            'thumbnail_data': result.get('thumbnail_data', {}),
            'description_data': result.get('description_data', {}),
            'metadata': result.get('metadata', {}),
            'total_scenes': 0
        }

        # Extract all image prompts
        scenes = image_data.get('scenes', [])
        for scene in scenes:
            scene_number = scene.get('scene_number')
            image_prompt = scene.get('image_prompt')
            negative_prompt = scene.get('negative_prompt', 'blurry, low quality, distorted, ugly, text, watermark')

            if scene_number and image_prompt:
                all_prompts.append({
                    'channel_id': channel_id,
                    'content_id': content_id,
                    'scene_number': scene_number,
                    'image_prompt': image_prompt,
                    'negative_prompt': negative_prompt
                })

        channels_metadata[channel_id]['total_scenes'] = len(scenes)

    print(f"✅ Collected {len(all_prompts)} prompts from {len(channels_metadata)} channels")

    # Create global batches (6 prompts per batch)
    batch_size = 6
    global_batches = []

    for i in range(0, len(all_prompts), batch_size):
        batch_items = all_prompts[i:i + batch_size]
        global_batches.append({
            'batch_id': len(global_batches),
            'batch_size': len(batch_items),
            'items': batch_items
        })

    print(f"📊 Created {len(global_batches)} global batches (batch_size={batch_size})")

    return {
        'global_batches': global_batches,
        'channels_metadata': channels_metadata,
        'total_prompts': len(all_prompts),
        'total_batches': len(global_batches),
        'total_channels': len(channels_metadata)
    }
