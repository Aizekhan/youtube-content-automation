"""
Lambda: merge-parallel-results
Dynamically merges phase2ParallelResults into main context

This replaces the hardcoded Pass state with flexible Lambda that:
- Automatically unpacks phase2ParallelResults
- Works with ANY number of fields (scalable)
- No need to update when adding new parallel branches
"""

import json


def lambda_handler(event, context):
    """
    Merge phase2ParallelResults into top-level context

    Input:
    {
        "user_id": "...",
        "phase2ParallelResults": {
            "distributedData": {...},
            "qwen3Endpoint": {...},
            "audioDistributionResult": {...}
        }
    }

    Output:
    {
        "user_id": "...",
        "distributedData": {...},
        "qwen3Endpoint": {...},
        "audioDistributionResult": {...}
    }
    """

    # Extract phase2ParallelResults (remove from event)
    phase2_results = event.pop('phase2ParallelResults', {})

    # Log what we're merging
    print(f"Merging {len(phase2_results)} fields from phase2ParallelResults")
    print(f"Fields: {list(phase2_results.keys())}")

    # Merge all fields from phase2 into event (dynamic!)
    event.update(phase2_results)

    # Log final structure
    print(f"Final context has {len(event)} top-level fields")

    return event
