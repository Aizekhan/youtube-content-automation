"""
Distribute Audio Lambda
Розподіляє згенеровані аудіо файли назад по каналах
"""
import json

def lambda_handler(event, context):
    """
    INPUT:
    {
      "generated_audio": [
        {
          "channel_id": "UCxxx",
          "content_id": "temp_xxx",
          "narrative_id": "...",
          "scene_id": "scene_1",
          "s3_url": "s3://...",
          "duration_ms": 5000
        }
      ],
      "channels_data": [...]  // Original channel data
    }

    OUTPUT:
    {
      "channels_with_audio": [
        {
          "channel_id": "UCxxx",
          "content_id": "temp_xxx",
          "audio_files": [...],
          "total_duration_ms": 45000
        }
      ]
    }
    """

    print(f"Distributing audio files back to channels")

    generated_audio = event.get('generated_audio', [])
    channels_data = event.get('channels_data', [])

    # Group audio by channel
    audio_by_channel = {}
    for audio in generated_audio:
        channel_id = audio.get('channel_id')
        if not channel_id:
            print(f"WARNING: Skipping audio without channel_id: {audio.get('s3_url', 'unknown')}")
            continue
        if channel_id not in audio_by_channel:
            audio_by_channel[channel_id] = []
        audio_by_channel[channel_id].append(audio)

    # Attach audio to channel data (SKIP channels marked as {"skipped": true})
    channels_with_audio = []
    skipped_count = 0

    for channel in channels_data:
        # CRITICAL: Skip duplicate/skipped channels to prevent saving incomplete records
        if channel.get('skipped') == True:
            skipped_count += 1
            cid = channel.get('channel_id') or channel.get('channel_item', {}).get('channel_id', 'unknown')
            print(f"Skipping channel (duplicate detected): {cid}")
            continue

        # Extract channel_id from nested structure
        channel_id = channel.get('channel_id') or channel.get('channel_item', {}).get('channel_id')
        if not channel_id:
            skipped_count += 1
            print(f"Skipping channel without channel_id: {channel}")
            continue

        channel_audio = audio_by_channel.get(channel_id, [])

        # Calculate total duration
        total_duration_ms = sum(a.get('duration_ms', 0) for a in channel_audio)

        # Flatten structure: extract channel_item to top level to avoid double nesting
        if 'channel_item' in channel and isinstance(channel['channel_item'], dict):
            nested_item = channel['channel_item']
            # Check if channel_item has another channel_item inside (double nesting from Phase1)
            if 'channel_item' in nested_item and isinstance(nested_item['channel_item'], dict):
                # Phase1 nested structure - extract from nested_item level
                flattened = {
                    'user_id': channel.get('user_id'),
                    'channel_item': nested_item['channel_item'],
                    'queryResult': nested_item.get('queryResult'),
                    'themeResult': nested_item.get('themeResult'),
                    'narrativeResult': nested_item.get('narrativeResult'),
                    'scene_images': channel.get('scene_images', []),  # Preserve images from previous step
                    'images_count': channel.get('images_count', 0),
                    'audio_files': channel_audio,
                    'total_duration_ms': total_duration_ms
                }
            else:
                # Single level nesting - already correct structure
                flattened = {
                    **channel,
                    'audio_files': channel_audio,
                    'total_duration_ms': total_duration_ms
                }
        else:
            # No nesting at all
            flattened = {
                **channel,
                'audio_files': channel_audio,
                'total_duration_ms': total_duration_ms
            }

        channels_with_audio.append(flattened)

        print(f"Channel {channel_id}: {len(channel_audio)} audio files attached, {total_duration_ms}ms total")

    print(f"Total: {len(channels_with_audio)} valid channels, {skipped_count} skipped")

    return {
        'statusCode': 200,
        'channels_with_audio': channels_with_audio
    }
