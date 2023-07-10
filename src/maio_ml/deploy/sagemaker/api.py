import json
import logging.config

import boto3

from src.maio_ml.deploy.sagemaker.utils import load_json

# logging.config.dictConfig(load_json("logging.json"))
# logger = logging.getLogger("logger")

# create an api gateway client
apigw_client = boto3.client('apigateway')
lambda_function_arn = 'arn:aws:lambda:eu-west-1:146915812621:function:test_func_v2'
http_method = 'GET'
stage_name = 'test'


def get_resource_id(rest_api_id, resource_path):
    # get the resource id
    resources = apigw_client.get_resources(restApiId=rest_api_id)['items']
    resource_id = None
    for resource in resources:
        if resource['path'] == resource_path:
            resource_id = resource['id']
            break
    return resource_id


def update_api(rest_api_id: str, pathPart: str):
    resource_id = get_resource_id(rest_api_id, resource_path="/")

    resource = apigw_client.create_resource(
        restApiId=rest_api_id,
        parentId=resource_id,
        pathPart=pathPart
    )

    resource_id = resource['id']

    # create a get method with query string parameters
    apigw_client.put_method(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=http_method,
        authorizationType='NONE',
    )

    uri = f'arn:aws:apigateway:eu-west-1:lambda:path/2015-03-31/functions/{lambda_function_arn}/invocations'

    # set the integration for the method
    apigw_client.put_integration(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=http_method,
        type='AWS_PROXY',
        integrationHttpMethod=http_method,
        uri=uri
    )
    logging.info("Creating resources...")

    # create a deployment
    deployment_response = apigw_client.create_deployment(
        restApiId=rest_api_id,
        stageName=stage_name,
    )

    logging.info("deploying rest endpoint...DONE")

    invoke_url = f'https://{rest_api_id}.execute-api.eu-west-1.amazonaws.com/{stage_name}/{pathPart}'

    return invoke_url


def create_api():
    # create an api
    response = apigw_client.create_rest_api(
        name='anomaly-detection-api',
        description='maio anomaly detection api',
        endpointConfiguration={
            'types': [
                'REGIONAL',
            ]
        }
    )
    rest_api_id = response['id']
    logging.info(f"Creating api...DONE. rest_api_id: {rest_api_id}")
    return rest_api_id


def create_function_url(function_name: str):
    lambda_client = boto3.client('lambda')
    response = lambda_client.create_function_url_config(
        FunctionName=function_name,
        InvokeMode='BUFFERED',
        AuthType='NONE'
    )
    return response


def add_permission_to_function():
    lambda_client = boto3.client('lambda')

    # Attach the policy to the Lambda function
    lambda_client.add_permission(
        FunctionName='graphql-server',
        StatementId='FunctionURLAllowPublicAccess',
        Action='lambda:InvokeFunctionUrl',
        Principal='*',
        FunctionUrlAuthType='NONE'
        # Replace the SourceArn with your API Gateway ARN
    )



if __name__ == '__main__':
    add_permission_to_function()
    # print(create_function_url('graphql-server'))
    # print(create_api())
    # print(update_api('o4mw4cqmrd', 'predict'))
    # print(get_resource_id('o4mw4cqmrd', 'predict'))
