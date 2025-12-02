"""
Lambda: distribute-image-results
Distributes generated images back to their respective channels
"""
import json


def lambda_handler(event, context):
    """
    Input:
    {
        "batch_results": [...],  # Results from all image batches
        "channels_metadata": {...}  # Metadata from collect step
    }

    Output: Array of results ready for Phase 3 (save & assemble)
    [
        {
            "channel_id": "...",
            "content_id": "...",
            "scene_images": [...],
            "narrative_data": {...},
            "audio_files": [...],
            ...
        }
    ]
    """

    print("📤 Distributing image results to channels...")

    batch_results = event.get('batch_results', [])
    channels_metadata = event.get('channels_metadata', {})

    # Collect all generated images
    all_images = []
    total_cost = 0.0
    total_generated = 0
    total_failed = 0

    for batch_result in batch_results:
        images = batch_result.get('scene_images', [])
        all_images.extend(images)
        total_cost += batch_result.get('total_cost_usd', 0.0)
        total_generated += batch_result.get('images_generated', 0)
        total_failed += batch_result.get('images_failed', 0)

    print(f"📊 Total images: {len(all_images)} (success: {total_generated}, failed: {total_failed})")
    print(f"💰 Total cost: ${total_cost:.4f}")

    # Group images by channel
    channels_images = {}
    for img in all_images:
        channel_id = img.get('channel_id')
        if channel_id not in channels_images:
            channels_images[channel_id] = []
        channels_images[channel_id].append(img)

    # Build final results for each channel
    final_results = []

    for channel_id, metadata in channels_metadata.items():
        channel_images = channels_images.get(channel_id, [])

        # Sort images by scene_number
        channel_images.sort(key=lambda x: x.get('scene_number', 0))

        result = {
            'channel_id': channel_id,
            'content_id': metadata['content_id'],
            'scene_images': channel_images,
            'narrative_data': metadata['narrative_data'],
            'audio_files': metadata['audio_files'],
            'selected_topic': metadata['selected_topic'],
            'sfx_data': metadata['sfx_data'],
            'cta_data': metadata['cta_data'],
            'thumbnail_data': metadata['thumbnail_data'],
            'description_data': metadata['description_data'],
            'metadata': metadata['metadata'],
            'images_generated': len([img for img in channel_images if img.get('status') == 'success']),
            'images_failed': len([img for img in channel_images if img.get('status') == 'failed']),
            'image_generation_cost_usd': sum(img.get('cost_usd', 0.0) for img in channel_images)
        }

        final_results.append(result)

        print(f"✅ {channel_id}: {result['images_generated']}/{len(channel_images)} images")

    return {
        'channels_results': final_results,
        'summary': {
            'total_channels': len(final_results),
            'total_images_generated': total_generated,
            'total_images_failed': total_failed,
            'total_cost_usd': total_cost
        }
    }
