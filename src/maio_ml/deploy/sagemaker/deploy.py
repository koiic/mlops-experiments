import sys
import zipfile

sys.path.append(".")
import argparse
import logging.config
import os
import re

import boto3
from deploy_env import DeployEnv
from sagemaker.pytorch import PyTorchModel
from sagemaker.pytorch.estimator import PyTorch
from utils import load_json

logging.config.dictConfig(load_json("logging.json"))
logger = logging.getLogger("logger")


def s3_bucket_from_url(s3_url):
    return re.search("//(.+)/", s3_url).groups()[0]


def upload_model_data(env: DeployEnv):
    if env.isLocal():
        return
    bucket_name = s3_bucket_from_url(env.setting("model_data_path"))
    logger.info("Uploading model.tar.gz to S3 bucket=%s..." % (bucket_name))

    s3 = boto3.client("s3")

    location = {"LocationConstraint": "eu-west-1"}
    try:
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
    except Exception as e:
        logger.info(f"Bucket already exists: {e}")

    return s3.upload_file("build/model.tar.gz", bucket_name, "model.tar.gz")
    logger.info("\t...DONE.")


def build_model_data_file():
    return os.system(
        "tar -czf build/model.tar.gz experiments anomaly_classification logging.json"
    )


def update_endpoint_if_exists(env: DeployEnv):
    return env.isProduction() & env.isDeployed()


def update_endpoint(env: DeployEnv):
    # update sage maker endpoint
    logger.info("Updating endpoint...")
    env.client().update_endpoint(
        EndpointName=env.setting("model_name"),
        EndpointConfigName=env.setting("model_name"),
    )


def delete_endpoint(env: DeployEnv, endpoint: str):
    """
    Need to manually delete the endpoint and config because of
    https://github.com/aws/sagemaker-python-sdk/issues/101#issuecomment-607376320.
    """
    env.client().delete_endpoint(EndpointName=endpoint)
    env.client().delete_endpoint_config(EndpointConfigName=endpoint)


def delete_endpoint_and_config(env: DeployEnv):
    """
    Need to manually delete the endpoint and config because of
    https://github.com/aws/sagemaker-python-sdk/issues/101#issuecomment-607376320.
    """
    env.client().delete_endpoint(EndpointName=env.setting("model_name"))
    env.client().delete_endpoint_config(EndpointConfigName=env.setting("model_name"))


def deploy(env: DeployEnv, source_dir: str):
    logger.info(
        "Deploying model_name=%s to env=%s"
        % (env.setting("model_name"), env.current_env())
    )

    # build_model_data_file()
    # Upload the model to S3 if not local
    upload_model_data(env)

    pytorch_model = PyTorchModel(
        entry_point="script.py",
        source_dir=source_dir,  # "chequers-rookley/code/src/",
        model_data=f"{env.setting('model_data_path')}/model.tar.gz",
        name=env.setting("model_name"),
        framework_version="2.0.0",
        py_version="py310",
        role=env.setting("aws_role"),
        env={"DEPLOY_ENV": env.current_env()},
    )
    logger.info(f"PyTorchModel: {pytorch_model}")

    if env.isDeployed():
        """
        Need to manually delete the endpoint and config because of
        https://github.com/aws/sagemaker-python-sdk/issues/101#issuecomment-607376320.
        """
        logger.info("Deleting existing endpoint and config...")
        env.client().delete_endpoint(EndpointName=env.setting("model_name"))
        env.client().delete_endpoint_config(
            EndpointConfigName=env.setting("model_name")
        )

    logger.info("Deploying model...")
    predictor = pytorch_model.deploy(
        instance_type=env.setting("instance_type"),
        # Below isn't working: https://github.com/aws/sagemaker-python-sdk/issues/101#issuecomment-607376320
        # update_endpoint = update_endpoint_if_exists(),
        initial_instance_count=1,
    )
    logger.info("\t...DONE.")


def train(
        env,
        training_input_path: str,
        test_input_path: str,
        hyperparameters: dict,
        source_dir: str,
        output_path: str,
):
    #
    estimator = PyTorch(
        entry_point="script.py",
        source_dir=source_dir,  # "chequers-rookley/code/src/",
        role=env.setting("aws_role"),
        instance_count=1,
        instance_type=env.setting(
            "instance_type"
        ),  # Train on the local CPU ('local_gpu' if it has a GPU)
        framework_version="2.0.0",
        py_version="py310",
        hyperparameters=hyperparameters,
        output_path=env.setting("model_data_path"),  # output_path,
    )

    estimator.fit({"training": training_input_path, "test": test_input_path})


def create_layer(env: DeployEnv):
    """
    create a aws_utils layer with the required libraries

    """

    # Upload the layer ZIP file to AWS Lambda
    with open('maio_ml/deploy/aws_utils/layer.zip', 'rb') as f:
        response = env.lambda_client().publish_layer_version(
            LayerName='maio-layer',
            Content={
                'ZipFile': f.read()
            },
            CompatibleRuntimes=['python3.8'],  # Replace with your desired runtime(s)
            Description='Maio layer for aws_utils functions'
        )
        print(response['LayerVersionArn'], response)


# def create_lambda_function(env: DeployEnv, source_dir, zip_file_name):
#     # Create a new Lambda function and update it with the latest code
#     # Create a ZIP file of the function code
#
#     with zipfile.ZipFile(zip_file_name, 'w') as zipf:
#         zipf.write(f"{source_dir}/lambda_func.py", arcname=os.path.basename("lambda_func.py"))
#
#     with open(zip_file_name, 'rb') as f:
#         zipped_code = f.read()
#
#     response = env.lambda_client().create_function(
#         FunctionName='test_func_v2',
#         Runtime='python3.8',
#         Role=env.setting("aws_role"),
#         Handler='lambda_func.lambda_handler',
#         Code={
#             'ZipFile': zipped_code
#
#         },
#
#     )
#
#     print(response, " RESPONSE")
#

def update_lambda_function(env: DeployEnv, source_dir, zip_file_name):
    with zipfile.ZipFile(zip_file_name, 'w') as zipf:
        zipf.write(f"{source_dir}/lambda_func.py", arcname=os.path.basename("lambda_func.py"))

    with open(zip_file_name, 'rb') as f:
        zipped_code = f.read()

    response = env.lambda_client().update_function_code(
        FunctionName='test_func_v2',
        ZipFile=zipped_code,
        Publish=True

    )

    print(response, " RESPONSE")


def create_lambda_function(env: DeployEnv, source_dir, zip_file_name):
    # Create a new Lambda function and update it with the latest code
    # Create a ZIP file of the function code

    with zipfile.ZipFile(zip_file_name, 'w') as zipf:
        # get all files from the source_dir
        for root, dirs, files in os.walk(source_dir):
            print(root, dirs, files)
            for file in files:
                zipf.write(os.path.join(root, file), arcname=os.path.basename(file))

        # zipf.write(f"{source_dir}/lambda_func.py", arcname=os.path.basename("lambda_func.py"))

    with open(zip_file_name, 'rb') as f:
        zipped_code = f.read()

    response = env.lambda_client().create_function(
        FunctionName='graphql-server',
        Runtime='python3.8',
        Role=env.setting("aws_role"),
        Handler='lambda_func.handler',
        Code={
            'ZipFile': zipped_code

        },

    )

    print(response, " RESPONSE")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # hyperparameters sent by the client are passed as command-line arguments to the script.
    # parser.add_argument("--train", action="store_true", help="Use to train the model.")
    parser.add_argument("--train", action="store_true", help="Use to train the model.")
    parser.add_argument("--delete", action="store_true", help="Use to delete the endpoint.")
    parser.add_argument("--function", action="store_true", help="Use to create the lambda function.")
    parser.add_argument("--endpoint", type=str, help="endpoint name.")

    env = DeployEnv()

    args = parser.parse_args()

    print(args)

    source_dir = "maio_ml/deploy/sagemaker"
    zip_file_name = 'lambda_func.zip'

    if args.train:
        # deploy()
        hyperparameters = {"learning-rate": 0.001, "epochs": 10}
        # source_dir="chequers-rookley/code/src"
        # output_path="file://chequers-rookley/models/"
        output_path = "file://build/"
        training_input_path = "file://../data/chequers-rookley/data.csv"
        test_input_path = "file://../data/chequers-rookley/data.csv"
        #
        train(
            env,
            training_input_path,
            test_input_path,
            hyperparameters,
            source_dir,
            output_path,
        )
    elif args.delete:
        delete_endpoint(env, args.endpoint)
    elif args.function:
        create_layer(env)
        # update_lambda_function(env, source_dir, zip_file_name)
        # create_lambda_function(env, "maio_ml/deploy/graphql_server", "graphql_server.zip")
    else:
        deploy(env, source_dir)
