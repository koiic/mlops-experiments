import sys

import boto3
from uvicorn import config

from maio_ml.deploy.sagemaker import utils, predict, serve

sys.path.append(".")
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from http import HTTPStatus
import json
from pydantic import BaseModel

app = FastAPI(
    title="text-classification",
    description="",
    version="1.0.0",
)


@utils.construct_response
@app.get("/")
async def _index():
    response = {
        'message': HTTPStatus.OK.phrase,
        'status-code': HTTPStatus.OK,
        'data': {}
    }
    config.logger.info(json.dumps(response, indent=2))
    return response


@app.get("/tensorboard")
async def _tensorboard():
    """Ensure TensorBoard is running on port 6006
    via `tensorboard --logdir tensorboard`."""
    return RedirectResponse("http://localhost:6006/")


class PredictPayload(BaseModel):
    experiment_id: str = 'latest'
    inputs: list = [{"text": ""}]


@utils.construct_response
@app.post("/predict")
async def _predict(payload: PredictPayload):
    prediction = predict.predict(
        experiment_id=payload.experiment_id, inputs=payload.inputs)
    response = {
        'message': HTTPStatus.OK.phrase,
        'status-code': HTTPStatus.OK,
        'data': {"prediction": prediction}
    }
    config.logger.info(json.dumps(response, indent=2))
    return response


class TrainingPayload(BaseModel):
    training_input_path: str
    test_input_path: str
    hyperparameters: dict
    output_path: str = "file://build/",


@utils.construct_response
@app.post("/train")
async def train(payload: TrainingPayload):
    status = serve.train(payload.training_input_path,
                         payload.test_input_path,
                         payload.hyperparameters,
                         payload.output_path)

    response = {
        'message': HTTPStatus.OK.phrase,
        'status-code': HTTPStatus.OK,
        'data': {"status": status}
    }
    config.logger.info(json.dumps(response, indent=2))
    return response


class LambdaPayload(BaseModel):
    gateway_name: str
    token: str
    start_time: str
    end_time: str
    endpoint: str
    base_url: str = None


@app.post("/invoke-lambda")
def invoke_lambda_function(payload: LambdaPayload):

    # Create the payload for the Lambda function
    lambda_payload = {
        'gateway_name': payload.gateway_name,
        'token': payload.token,
        'start_time': payload.start_time,
        'end_time': payload.end_time,
        'endpoint': payload.endpoint,
        'base_url': payload.base_url
    }

    lambda_client = boto3.client('lambda')

    # Invoke the Lambda function
    response = lambda_client.invoke(
        FunctionName='test_func_v2',
        InvocationType='RequestResponse',
        Payload=str.encode(json.dumps(lambda_payload))
    )

    # Parse the Lambda response
    response_payload = response['Payload'].read().decode('utf-8')
    return response_payload
