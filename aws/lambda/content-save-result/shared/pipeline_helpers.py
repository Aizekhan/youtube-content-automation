"""
Helper functions for managing content production pipeline status
"""

from datetime import datetime
from typing import Dict, Any, Optional


def initialize_pipeline_status() -> Dict[str, Any]:
    """
    Initialize empty pipeline status structure for a new content item

    Returns:
        Dict with pipeline_status structure
    """
    current_time = datetime.utcnow().isoformat() + 'Z'

    return {
        "overall_status": "pending",
        "progress_percentage": 0,
        "stages": {
            "1_overview": {"status": "completed", "updated_at": current_time},
            "2_thumbnail": {"status": "pending", "updated_at": None},
            "3_story": {"status": "pending", "updated_at": None},
            "4_voice": {"status": "pending", "updated_at": None},
            "5_cta": {"status": "pending", "updated_at": None},
            "6_audio": {"status": "pending", "updated_at": None},
            "7_visuals": {"status": "pending", "updated_at": None},
            "8_video": {"status": "pending", "updated_at": None}
        },
        "last_updated": current_time
    }


def update_pipeline_stage(
    pipeline_status: Dict[str, Any],
    stage_name: str,
    status: str
) -> Dict[str, Any]:
    """
    Update a specific pipeline stage status

    Args:
        pipeline_status: Current pipeline status dict
        stage_name: Stage to update (e.g., "3_story", "4_voice")
        status: New status ("pending", "in_progress", "completed", "failed")

    Returns:
        Updated pipeline_status dict
    """
    current_time = datetime.utcnow().isoformat() + 'Z'

    if stage_name in pipeline_status["stages"]:
        pipeline_status["stages"][stage_name]["status"] = status
        pipeline_status["stages"][stage_name]["updated_at"] = current_time

    # Recalculate progress percentage
    total_stages = len(pipeline_status["stages"])
    completed_stages = sum(
        1 for stage in pipeline_status["stages"].values()
        if stage["status"] == "completed"
    )
    pipeline_status["progress_percentage"] = int((completed_stages / total_stages) * 100)

    # Update overall status
    all_completed = all(
        stage["status"] == "completed"
        for stage in pipeline_status["stages"].values()
    )
    any_failed = any(
        stage["status"] == "failed"
        for stage in pipeline_status["stages"].values()
    )
    any_in_progress = any(
        stage["status"] == "in_progress"
        for stage in pipeline_status["stages"].values()
    )

    if all_completed:
        pipeline_status["overall_status"] = "completed"
    elif any_failed:
        pipeline_status["overall_status"] = "failed"
    elif any_in_progress:
        pipeline_status["overall_status"] = "in_progress"
    else:
        pipeline_status["overall_status"] = "pending"

    pipeline_status["last_updated"] = current_time

    return pipeline_status


def get_stage_status(pipeline_status: Dict[str, Any], stage_name: str) -> Optional[str]:
    """
    Get status of a specific pipeline stage

    Args:
        pipeline_status: Pipeline status dict
        stage_name: Stage name (e.g., "3_story")

    Returns:
        Status string or None if stage not found
    """
    if stage_name in pipeline_status.get("stages", {}):
        return pipeline_status["stages"][stage_name]["status"]
    return None


def initialize_thumbnail_structure() -> Dict[str, Any]:
    """Initialize empty thumbnail structure"""
    return {
        "image_url": None,
        "prompt": None,
        "generated_at": None,
        "service": None,
        "status": "pending",
        "width": 1280,
        "height": 720
    }


def initialize_cta_structure() -> Dict[str, Any]:
    """Initialize empty call-to-action structure"""
    return {
        "text": None,
        "audio_url": None,
        "duration_ms": None,
        "voice_id": None,
        "placement": "end",
        "generated_at": None,
        "status": "pending"
    }


def initialize_background_music_structure() -> Dict[str, Any]:
    """Initialize empty background music structure"""
    return {
        "track_url": None,
        "track_name": None,
        "duration_ms": None,
        "volume_level": 0.3,
        "source": None,
        "license": "royalty-free",
        "fade_in_ms": 2000,
        "fade_out_ms": 3000,
        "status": "pending"
    }


def initialize_final_video_structure() -> Dict[str, Any]:
    """Initialize empty final video structure"""
    return {
        "video_url": None,
        "video_title": None,
        "video_description": None,
        "video_tags": [],
        "duration_ms": None,
        "resolution": "1920x1080",
        "fps": 30,
        "file_size_mb": None,
        "rendered_at": None,
        "rendering_service": "ffmpeg",
        "status": "pending"
    }


def initialize_youtube_publishing_structure() -> Dict[str, Any]:
    """Initialize empty YouTube publishing structure"""
    return {
        "video_id": None,
        "published_url": None,
        "published_at": None,
        "visibility": "private",
        "scheduled_publish_time": None,
        "upload_status": "draft",
        "views": 0,
        "likes": 0,
        "comments": 0,
        "last_synced": None
    }


def get_pipeline_progress_summary(pipeline_status: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get human-readable summary of pipeline progress

    Returns:
        Dict with summary info
    """
    stages = pipeline_status.get("stages", {})

    completed = [k for k, v in stages.items() if v["status"] == "completed"]
    pending = [k for k, v in stages.items() if v["status"] == "pending"]
    in_progress = [k for k, v in stages.items() if v["status"] == "in_progress"]
    failed = [k for k, v in stages.items() if v["status"] == "failed"]

    return {
        "overall_status": pipeline_status.get("overall_status", "unknown"),
        "progress_percentage": pipeline_status.get("progress_percentage", 0),
        "completed_count": len(completed),
        "pending_count": len(pending),
        "in_progress_count": len(in_progress),
        "failed_count": len(failed),
        "completed_stages": completed,
        "pending_stages": pending,
        "in_progress_stages": in_progress,
        "failed_stages": failed,
        "last_updated": pipeline_status.get("last_updated")
    }


# Stage name mappings for easy reference
STAGE_OVERVIEW = "1_overview"
STAGE_THUMBNAIL = "2_thumbnail"
STAGE_STORY = "3_story"
STAGE_VOICE = "4_voice"
STAGE_CTA = "5_cta"
STAGE_AUDIO = "6_audio"
STAGE_VISUALS = "7_visuals"
STAGE_VIDEO = "8_video"

# Status constants
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
