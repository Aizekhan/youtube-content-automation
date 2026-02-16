import json
import requests

def lambda_handler(event, context):
    """
    Check if Qwen3-TTS service is healthy

    Input:
    {
        "endpoint": "http://3.125.119.147:5000"
    }

    Output:
    {
        "healthy": true/false,
        "models_loaded": 3,
        "message": "..."
    }
    """

    endpoint = event.get('endpoint')

    if not endpoint:
        return {
            'healthy': False,
            'message': 'No endpoint provided'
        }

    try:
        health_url = f"{endpoint}/health"
        response = requests.get(health_url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            models_loaded = data.get('models_loaded', 0)

            # Service is healthy if at least 3 models loaded
            healthy = models_loaded >= 3

            return {
                'healthy': healthy,
                'models_loaded': models_loaded,
                'status': data.get('status'),
                'message': f"{'Service ready' if healthy else 'Models still loading'} ({models_loaded}/3 models)",
                'endpoint': endpoint  # IMPORTANT: Pass endpoint through for downstream states
            }
        else:
            return {
                'healthy': False,
                'message': f"HTTP {response.status_code}"
            }

    except requests.exceptions.Timeout:
        return {
            'healthy': False,
            'message': 'Health check timeout'
        }
    except Exception as e:
        return {
            'healthy': False,
            'message': f"Error: {str(e)}"
        }
