import json
import boto3


def lambda_handler(event, context):
    # Retrieve the payload from the API Gateway request
    payload = json.loads(event['body'])
    endpoint_name = event['endpoint']

    # Perform inference on the SageMaker endpoint
    runtime_client = boto3.client('sagemaker-runtime')
    response = runtime_client.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType='application/json',
        Accept='application/json',
        Body=json.dumps(payload)
    )

    # Parse and return the inference result
    result = json.loads(response['Body'].read().decode())

    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
