"""
Merge channel images and audio data for Phase3
"""

def lambda_handler(event, context):
    """
    Merge channels_with_images and channels_with_audio

    Input:
    {
        "channels_with_images": [...],  # From distribute-images
        "channels_with_audio": [...],    # From distribute-audio
        "qwen3_endpoint": "http://..."   # From Phase2B audio branch
    }

    Output:
    {
        "merged_channels": [...],  # Full channel data with both images and audio
        "qwen3_endpoint": "http://..."
    }
    """
    channels_with_images = event.get('channels_with_images', [])
    channels_with_audio = event.get('channels_with_audio', [])
    qwen3_endpoint = event.get('qwen3_endpoint')

    # Create audio lookup by channel_id (both scene audio and CTA audio)
    audio_lookup = {}
    cta_audio_lookup = {}
    for audio_channel in channels_with_audio:
        channel_id = audio_channel.get('channel_id') or audio_channel.get('channel_item', {}).get('channel_id')
        if channel_id:
            audio_lookup[channel_id] = audio_channel.get('audio_files', [])
            cta_audio_lookup[channel_id] = audio_channel.get('cta_audio_files', [])

    # Merge audio into channels_with_images
    merged_channels = []
    for channel in channels_with_images:
        channel_id = channel.get('channel_id') or channel.get('channel_item', {}).get('channel_id')

        # Add audio_files and cta_audio_files from lookups
        if channel_id and channel_id in audio_lookup:
            channel['audio_files'] = audio_lookup[channel_id]
            channel['cta_audio_files'] = cta_audio_lookup.get(channel_id, [])
        else:
            channel['audio_files'] = []
            channel['cta_audio_files'] = []

        merged_channels.append(channel)

    print(f"Merged {len(merged_channels)} channels (images + audio)")

    return {
        'merged_channels': merged_channels,
        'qwen3_endpoint': qwen3_endpoint
    }
