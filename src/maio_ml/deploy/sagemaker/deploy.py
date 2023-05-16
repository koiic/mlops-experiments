import sys

sys.path.append(".")
import argparse
import logging
import logging.config
import os
import re
import tarfile

import boto3
import sagemaker
from deploy_env import DeployEnv
from sagemaker.pytorch import PyTorchModel
from sagemaker.pytorch.estimator import PyTorch
from utils import load_json

logging.config.dictConfig(load_json("logging.json"))
logger = logging.getLogger('logger')

def s3_bucket_from_url(s3_url):
    return re.search('//(.+)/',s3_url).groups()[0]

def upload_model_data(env:DeployEnv):
    if env.isLocal():
        return
    bucket_name = s3_bucket_from_url(env.setting('model_data_path'))
    logger.info("Uploading model.tar.gz to S3 bucket=%s..." % (bucket_name))
    s3 = boto3.resource('s3')
    s3.create_bucket(Bucket=bucket_name)
    return s3.Bucket(bucket_name).upload_file("build/model.tar.gz", "model.tar.gz")
    logger.info("\t...DONE.")

def build_model_data_file():
    return os.system("tar -czf build/model.tar.gz experiments anomaly_classification logging.json")

def update_endpoint_if_exists(env:DeployEnv):
    return (env.isProduction() & env.isDeployed())

def delete_endpoint_and_config(env:DeployEnv):
    """
    Need to manually delete the endpoint and config because of
    https://github.com/aws/sagemaker-python-sdk/issues/101#issuecomment-607376320.
    """
    env.client().delete_endpoint(EndpointName=env.setting('model_name'))
    env.client().delete_endpoint_config(EndpointConfigName=env.setting('model_name'))

def deploy(env:DeployEnv, source_dir:str):
    logger.info("Deploying model_name=%s to env=%s" % (env.setting('model_name'), env.current_env()))

    # build_model_data_file()
    # Upload the model to S3 if not local
    upload_model_data(env)

    pytorch_model = PyTorchModel(
        entry_point='script.py',
        source_dir = source_dir, # "chequers-rookley/code/src/",
        model_data = f"{env.setting('model_data_path')}/model.tar.gz",
        name = env.setting('model_name'),
        framework_version = '2.0.0',
        py_version='py310',
        role = env.setting("aws_role"),
        env = {"DEPLOY_ENV": env.current_env()},
    )

    if env.isDeployed():
        """
        Need to manually delete the endpoint and config because of
        https://github.com/aws/sagemaker-python-sdk/issues/101#issuecomment-607376320.
        """
        env.client().delete_endpoint(EndpointName=env.setting('model_name'))
        env.client().delete_endpoint_config(EndpointConfigName=env.setting('model_name'))

    predictor = pytorch_model.deploy(
        instance_type = env.setting('instance_type'),
        # Below isn't working: https://github.com/aws/sagemaker-python-sdk/issues/101#issuecomment-607376320
        # update_endpoint = update_endpoint_if_exists(),
        initial_instance_count = 1)

def train(env, training_input_path:str, test_input_path:str, hyperparameters:dict, source_dir:str, role:str, output_path:str):
    #
    estimator = PyTorch(
        entry_point='script.py',
        source_dir = source_dir, # "chequers-rookley/code/src/",
        role=env.setting("aws_role"),
        instance_count=1,
        instance_type=env.setting('instance_type'),   # Train on the local CPU ('local_gpu' if it has a GPU)
        framework_version='2.0.0',
        py_version='py310',
        hyperparameters=hyperparameters,
        output_path=env.setting('model_data_path'), #output_path,
    )

    estimator.fit({"training": training_input_path, "test": test_input_path})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # hyperparameters sent by the client are passed as command-line arguments to the script.
    parser.add_argument('--train', action='store_true', help="Use to train the model.")

    env = DeployEnv()

    args = parser.parse_args()

    source_dir="maio_ml/deploy/sagemaker"

    if args.train:
        # deploy()
        hyperparameters={'learning-rate': 0.001, 'epochs': 10}
        role="arn:aws:iam::146915812621:role/service-role/SageMaker-DataScientist"
        #source_dir="chequers-rookley/code/src"
        #output_path="file://chequers-rookley/models/"
        output_path="file://build/"
        training_input_path="file://../data/chequers-rookley/data.csv"
        test_input_path="file://../data/chequers-rookley/data.csv"
        #
        train(env, training_input_path, test_input_path, hyperparameters, source_dir, role, output_path)
    else:
        deploy(env, source_dir)
