"""
Merge Image Batches Lambda

Об'єднує результати паралельної генерації зображень з різних батчів.

Input (from Map state output):
{
  "batch_results": [
    {
      "scene_images": [
        {"scene_id": 1, "image_url": "s3://...", "status": "completed"},
        ...
      ],
      "batch_info": {"batch_index": 0, "batch_size": 6}
    },
    {
      "scene_images": [
        {"scene_id": 7, "image_url": "s3://...", "status": "completed"},
        ...
      ],
      "batch_info": {"batch_index": 1, "batch_size": 6}
    }
  ]
}

Output:
{
  "scene_images": [
    {"scene_id": 1, "image_url": "s3://...", "status": "completed"},
    {"scene_id": 2, "image_url": "s3://...", "status": "completed"},
    ...
    {"scene_id": 18, "image_url": "s3://...", "status": "completed"}
  ],
  "total_images_generated": 18,
  "total_images_failed": 0,
  "total_cost_usd": 0.054,
  "batches_processed": 3
}
"""

import json
from decimal import Decimal


def lambda_handler(event, context):
    """Об'єднання результатів з різних батчів зображень"""

    print(f" Merge Image Batches")
    print(f"Event keys: {list(event.keys())}")

    # Get batch results (can be in different formats depending on Step Function)
    batch_results = event.get('batch_results', event.get('batches', []))

    if not batch_results:
        print("  No batch results provided")
        return {
            'scene_images': [],
            'total_images_generated': 0,
            'total_images_failed': 0,
            'total_cost_usd': 0.0,
            'batches_processed': 0
        }

    print(f" Processing {len(batch_results)} batches")

    # Collect all scene images
    all_scene_images = []
    total_cost = 0.0
    total_generated = 0
    total_failed = 0

    for batch_idx, batch_result in enumerate(batch_results):
        print(f"\n   Processing batch {batch_idx}:")

        # Extract scene_images from batch result
        scene_images = batch_result.get('scene_images', [])
        batch_cost = float(batch_result.get('total_cost_usd', 0))
        batch_generated = batch_result.get('images_generated', 0)
        batch_failed = batch_result.get('images_failed', 0)

        print(f"      Images: {batch_generated} generated, {batch_failed} failed")
        print(f"      Cost: ${batch_cost:.4f}")

        # Add to totals
        all_scene_images.extend(scene_images)
        total_cost += batch_cost
        total_generated += batch_generated
        total_failed += batch_failed

    # Sort by scene_id to maintain order
    all_scene_images.sort(key=lambda x: x.get('scene_id', 0))

    print(f"\n Merge complete:")
    print(f"   Total images: {len(all_scene_images)}")
    print(f"   Generated: {total_generated}")
    print(f"   Failed: {total_failed}")
    print(f"   Total cost: ${total_cost:.4f}")

    output = {
        'scene_images': all_scene_images,
        'total_images_generated': total_generated,
        'total_images_failed': total_failed,
        'total_cost_usd': round(total_cost, 6),
        'batches_processed': len(batch_results),
        'provider': batch_results[0].get('provider', 'unknown') if batch_results else 'unknown'
    }

    return output


def convert_decimals(obj):
    """Convert Decimal to float for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj
