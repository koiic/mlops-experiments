import os
import sys

from uvicorn import config

from src.maio_ml.deploy.sagemaker import utils, predict, serve

sys.path.append(".")
from fastapi import FastAPI
from fastapi import Path
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
