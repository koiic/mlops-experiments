import argparse

import boto3
import json
from deploy_env import DeployEnv

env = DeployEnv()
lambda_client = boto3.client('events')


def attach_policy():
    iam_client = boto3.client('iam')

    # Specify the name of your Lambda function and the ARN of the policy to attach
    function_name = 'your-lambda-function-name'
    policy_arn = 'arn:aws:iam::your-account-id:policy/AWSLambdaInvocation-Destination'

    # Get the current execution role of the Lambda function
    response = lambda_client.get_function(FunctionName=function_name)
    execution_role_arn = response['Configuration']['Role']

    # Attach the policy to the execution role
    iam_client.attach_role_policy(RoleName=execution_role_arn.split('/')[-1], PolicyArn=policy_arn)

    print("Policy attached successfully.")
def create_cloudwatch_event_rule(interval: int, payload: dict):
    events_client = boto3.client('events')

    # convert interval seconds to rate in minutes
    rate = f"rate({interval // 60} minutes)"

    response = events_client.put_rule(
        Name='LambdaSchedulerRule',
        ScheduleExpression=rate,  # Set the desired interval
        State='ENABLED',
        # RoleArn=env.setting("aws_role")
    )

    # Create the target for the rule
    target = {
        'Id': '1',
        'Arn': 'arn:aws:lambda:eu-west-1:146915812621:function:test_func_v2',
        'Input': json.dumps(payload)  # Set the desired payload for each invocation
    }

    # Add the target to the rule
    events_client.put_targets(
        Rule='LambdaSchedulerRule',
        Targets=[target]
    )

    # Add permission for CloudWatch Events to invoke the Lambda function
    lambda_client.add_permission(
        FunctionName='test_func_v2',
        StatementId='LambdaInvokePermission',
        Action='lambda:InvokeFunction',
        Principal='events.amazonaws.com',
        SourceArn=response['RuleArn']
    )

    print('CloudWatch Event rule created successfully.')


def update_rule(state: str, name: str = None):
    # check the state of the rule
    if name is None:
        name = 'LambdaSchedulerRule'
    events_client = boto3.client('events')
    if state == 'ENABLED':
        events_client.enable_rule(Name=name)
    else:
        events_client.disable_rule(Name=name)

    print('CloudWatch Event rule updated successfully.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # hyperparameters sent by the client are passed as command-line arguments to the script.
    # parser.add_argument("--train", action="store_true", help="Use to train the model.")
    parser.add_argument("--schedule", action="store_true", help="Use to schedule the lambda function.")
    parser.add_argument("--enabled", type=str, help="Use to enable cloudwatch event.")
    parser.add_argument("--disabled", type=str, help="Use to disable cloudwatch event.")
    parser.add_argument("--name", type=str, help="rule name.")
    parser.add_argument("--interval", type=int, help="schedule interval in seconds.")

    args = parser.parse_args()

    payload = {
        "gateway_name": "Aruba",
        "token": "token_id",
        "endpoint": "pytorch-anomaly-classification-2023-05-21-06-50-14-925",
        "start_time": "2023-05-08T10:00:00.000000Z",
        "end_time": "2023-05-08T11:00:00.000000Z"
    }

    if args.enabled:
        update_rule('ENABLED', args.name)

    elif args.disabled:
        update_rule('DISABLED', args.name)

    else:
        create_cloudwatch_event_rule(args.interval, payload)
