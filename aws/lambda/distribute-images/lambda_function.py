"""
Distribute Images Lambda
  images   
"""
import json

def lambda_handler(event, context):
    """
    INPUT:
    {
      "generated_images": [
        {
          "channel_id": "UCxxx",
          "content_id": "temp_xxx",
          "scene_index": 0,
          "image_url": "s3://...",
          "cost_usd": 0.05
        }
      ],
      "channels_data": [...]  // Original channel data
    }

    OUTPUT:
    {
      "channels_with_images": [
        {
          "channel_id": "UCxxx",
          "content_id": "temp_xxx",
          "scene_images": [...]
        }
      ]
    }
    """

    print(f" Distributing images back to channels")

    generated_images = event.get('generated_images', [])
    channels_data = event.get('channels_data', [])

    # Group images by channel
    images_by_channel = {}
    for img in generated_images:
        channel_id = img.get('channel_id')
        if not channel_id:
            print(f"Warning: Skipping image without channel_id: {img.get('image_url', 'unknown')}")
            continue
        if channel_id not in images_by_channel:
            images_by_channel[channel_id] = []
        images_by_channel[channel_id].append(img)

    # Attach images to channel data (SKIP channels marked as {"skipped": true})
    channels_with_images = []
    skipped_count = 0

    for channel in channels_data:
        # CRITICAL: Skip duplicate/skipped channels to prevent saving incomplete records
        if channel.get('skipped') == True:
            skipped_count += 1
            cid = channel.get('channel_id') or channel.get('channel_item', {}).get('channel_id', 'unknown')
            print(f"  Skipping channel (duplicate detected): {cid}")
            continue

        # Extract channel_id from nested structure (phase1 returns channel_item.channel_id)
        channel_id = channel.get('channel_id') or channel.get('channel_item', {}).get('channel_id')
        if not channel_id:
            skipped_count += 1
            print(f"  Skipping channel without channel_id: {channel}")
            continue

        channel_images = images_by_channel.get(channel_id, [])

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
                    'scene_images': channel_images,
                    'images_count': len(channel_images)
                }
            else:
                # Single level nesting - already correct structure
                flattened = {
                    **channel,
                    'scene_images': channel_images,
                    'images_count': len(channel_images)
                }
        else:
            # No nesting at all
            flattened = {
                **channel,
                'scene_images': channel_images,
                'images_count': len(channel_images)
            }

        channels_with_images.append(flattened)

        print(f" Channel {channel_id}: {len(channel_images)} images attached")

    print(f" Total: {len(channels_with_images)} valid channels, {skipped_count} skipped")

    return {
        'statusCode': 200,
        'channels_with_images': channels_with_images
    }
