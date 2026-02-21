import json
import boto3

s3_client = boto3.client('s3', region_name='eu-central-1')

def lambda_handler(event, context):
    """
    Load Phase1 results from S3
    Input: Array of S3 references from Phase1
    Output: Full Phase1 data for downstream processing
    """
    print(f"Event: {json.dumps(event, default=str)}")

    try:
        phase1_references = event.get('phase1_references', [])

        if not phase1_references:
            print("No Phase1 references provided")
            return []

        results = []

        for ref in phase1_references:
            s3_bucket = ref.get('s3_bucket')
            s3_key = ref.get('s3_key')

            if not s3_bucket or not s3_key:
                print(f"WARNING: Missing S3 reference: {ref}")
                continue

            try:
                # Load from S3
                response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
                data = json.loads(response['Body'].read().decode('utf-8'))
                results.append(data)
                print(f"Loaded: s3://{s3_bucket}/{s3_key}")

            except Exception as e:
                print(f"ERROR loading s3://{s3_bucket}/{s3_key}: {e}")
                # Continue with other results
                continue

        print(f"Loaded {len(results)} Phase1 results from S3")
        return results

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
