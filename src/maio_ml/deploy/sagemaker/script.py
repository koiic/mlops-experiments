import argparse
import inspect
import json
import logging
import os
import sys
from collections import OrderedDict
from enum import Enum

import pandas as pd
import torch
from merlion.evaluate.anomaly import TSADMetric
from merlion.models.factory import ModelFactory
from merlion.post_process.threshold import AggregateAlarms
from merlion.utils.time_series import TimeSeries
from sagemaker_inference import (
    content_types,
    decoder,
    default_inference_handler,
    encoder,
    errors,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


def is_enum(t):
    return isinstance(t, type) and issubclass(t, Enum)


def is_valid_type(t):
    return t in (int, float, str, bool, list, tuple, dict) or is_enum(t)


def train(args):
    # is_distributed = len(args.hosts) > 1 and args.backend is not None
    # logger.debug("Distributed training - {}".format(is_distributed))
    is_distributed = False

    use_cuda = args.num_gpus > 0
    logger.debug("Number of gpus available - {}".format(args.num_gpus))
    kwargs = {"num_workers": 1, "pin_memory": True} if use_cuda else {}
    device = torch.device("cuda" if use_cuda else "cpu")

    if is_distributed:
        # Initialize the distributed environment.
        world_size = len(args.hosts)
        os.environ["WORLD_SIZE"] = str(world_size)
        host_rank = args.hosts.index(args.current_host)
        os.environ["RANK"] = str(host_rank)
        dist.init_process_group(
            backend=args.backend, rank=host_rank, world_size=world_size
        )
        logger.info(
            "Initialized the distributed environment: '{}' backend on {} nodes. ".format(
                args.backend, dist.get_world_size()
            )
            + "Current host rank is {}. Number of gpus: {}".format(
                dist.get_rank(), args.num_gpus
            )
        )

    # set the seed for generating random numbers
    torch.manual_seed(args.seed)
    if use_cuda:
        torch.cuda.manual_seed(args.seed)

    logger.debug(f"Loading data from {args.data_dir}/data.csv")

    df = pd.read_csv(f"{args.data_dir}/data.csv", index_col=0, parse_dates=True)

    label_column = ["label"]
    columns = [
        "cooler_temp",
        "bath_temp",
        "cooler_switch",
        "refridgent_temp",
        "compressor_current",
    ]
    train_percentage = 70

    n = int(int(train_percentage) * len(df) / 100)

    train_df = df.iloc[:n]
    test_df = df.iloc[n:]

    logger.debug(f"Loading algorithm: {args.algorithm}")

    model_class = ModelFactory.get_model_class(args.algorithm)

    init_method = model_class.config_class.__init__

    param_info = OrderedDict()
    signature = inspect.signature(init_method).parameters
    for name, param in signature.items():
        if name in ["self", "target_seq_index"]:
            continue
        value = param.default
        if value == param.empty:
            value = ""
        if is_valid_type(type(param.default)):
            value = value.name if isinstance(value, Enum) else value
            param_info[name] = {"type": type(param.default), "default": value}
        elif is_valid_type(param.annotation):
            value = value.name if isinstance(value, Enum) else value
            param_info[name] = {"type": param.annotation, "default": value}

    logger.debug(param_info)

    logger.debug(init_method)

    model = model_class(model_class.config_class())
    model = ModelFactory.create(
        args.algorithm,
        threshold=AggregateAlarms(
            alm_threshold=4.5,
            min_alm_in_window=3,
            alm_window_minutes=5,
            alm_suppress_minutes=15,
        ),
    )

    train_ts, train_labels = TimeSeries.from_pd(train_df[columns]), None
    test_ts, test_labels = TimeSeries.from_pd(test_df[columns]), None

    logger.debug(train_ts)

    if label_column is not None and label_column != "":
        train_labels = TimeSeries.from_pd(train_df[label_column])
        test_labels = TimeSeries.from_pd(test_df[label_column])

    logger.debug(f"Training dataset size: {len(train_df)}")
    logger.debug(f"Test dataset size: {len(test_df)}")

    scores = model.train(train_data=train_ts)

    logger.debug(f"Scores: {scores}")
    logger.debug(f"Post Rules: {model.post_rule}")

    train_pred = model.post_rule(scores) if model.post_rule else scores

    train_metrics = {}
    if train_labels is not None:
        for metric in [
            TSADMetric.Precision,
            TSADMetric.Recall,
            TSADMetric.F1,
            TSADMetric.MeanTimeToDetect,
        ]:
            m = metric.value(ground_truth=test_labels, predict=train_pred)
            train_metrics[metric.name] = (
                round(m, 5) if metric.name != "MeanTimeToDetect" else str(m)
            )

    logger.debug(f"Train Metrics: {train_metrics}")

    test_pred = model.get_anomaly_label(test_ts)

    test_metrics = {}
    if test_labels is not None:
        for metric in [
            TSADMetric.Precision,
            TSADMetric.Recall,
            TSADMetric.F1,
            TSADMetric.MeanTimeToDetect,
        ]:
            m = metric.value(ground_truth=test_labels, predict=test_pred)
            test_metrics[metric.name] = (
                round(m, 5) if metric.name != "MeanTimeToDetect" else str(m)
            )

    logger.debug(f"Test Metrics: {test_metrics}")

    save_model(model, args.model_dir)


def test(model, test_loader, device):
    # model.eval()
    # test_loss = 0
    # correct = 0
    # with torch.no_grad():
    #     for data, target in test_loader:
    #         data, target = data.to(device), target.to(device)
    #         output = model(data)
    #         test_loss += F.nll_loss(
    #             output, target, size_average=False
    #         ).item()  # sum up batch loss
    #         pred = output.max(1, keepdim=True)[
    #             1
    #         ]  # get the index of the max log-probability
    #         correct += pred.eq(target.view_as(pred)).sum().item()

    # test_loss /= len(test_loader.dataset)
    # logger.info(
    #     "Test set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n".format(
    #         test_loss,
    #         correct,
    #         len(test_loader.dataset),
    #         100.0 * correct / len(test_loader.dataset),
    #     )
    # )
    logger.info("Nothing to test")


def model_fn(model_dir):
    """
    Load the PyTorch model from the `model_dir` directory.
    Args:
        model_dir (str): path to the directory containing the saved PyTorch model.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # model = torch.nn.DataParallel(Net())
    # with open(os.path.join(model_dir, "model.pth"), "rb") as f:
    #     model.load_state_dict(torch.load(f))

    algorithm = "LSTMED"
    logger.info(f"Loading algorithm: {algorithm} from {model_dir}")
    model = ModelFactory.load(algorithm, model_dir+"/model.pth")

    return model

# From docs:
# Default json deserialization requires request_body contain a single json list.
# https://github.com/aws/sagemaker-pytorch-serving-container/blob/master/src/sagemaker_pytorch_serving_container/default_inference_handler.py#L49
def input_fn(request_body, request_content_type):
    """_summary_

    Args:
        request_body (_type_): _description_
        request_content_type (_type_): _description_

    Returns:
        _type_: _description_
    """
    logger.info(f"input_f (request body): {type(request_body)}")
    # data = json.loads(request_body)
    # model_input = [{"text": features[0]} for features in data]
    df = pd.read_json(request_body, orient='split')
    logger.info(f"Dataframe shape: {df.shape}\n{df.head()}")
    model_input = TimeSeries.from_pd(df)
    # logger.info(f"Model input: {model_input}")
    return model_input

def predict_fn(input_data, model):
    logger.info(f"Calling predict on model with input data\n {type(input_data)}")
    logger.info(f"Model type: {type(model)}")
    prediction = model.get_anomaly_label(input_data)
    # experiment_id='latest', inputs=input_data)
    logger.info(f"Prediction: {type(prediction)}")
    return prediction

def output_fn(prediction, content_type):
    logger.info(f"Prediction: {type(prediction.to_pd())}")
    serie = prediction.to_pd()
    res = serie.to_json(orient='split', index=False) # [{"probabilities": result["probabilities"], "top_n_grams": result["top_n_grams"]} for result in prediction]
    return encoder.encode(res, content_type)

def save_model(model, model_dir):
    """Save the PyTorch model to the `model_dir` directory.

    Args:
        model (_type_): trained PyTorch model to save.
        model_dir (str): path to the directory containing the saved model.
    """
    logger.info("Saving the model.")
    path = os.path.join(model_dir, "model.pth")
    # recommended way from http://pytorch.org/docs/master/notes/serialization.html
    logger.debug(f"Saving model to {path}")
    logger.debug(f"Saving model to {path} - {model} - {type(model)}")
    # torch.save(model.cpu().state_dict(), path)
    model.save(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # hyperparameters sent by the client are passed as command-line arguments to the script.
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--learning-rate", type=float, default=0.1)
    parser.add_argument("--num_gpus", type=int, default=0)
    parser.add_argument(
        "--algorithm",
        type=str,
        choices=["LSTMED", "paper", "scissors"],
        default="LSTMED",
    )
    parser.add_argument("--seed", type=int, default=42, help="random seed (default: 1)")

    # an alternative way to load hyperparameters via SM_HPS environment variable.
    parser.add_argument("--sm-hps", type=json.loads, default=os.environ["SM_HPS"])

    # input data and model directories

    parser.add_argument(
        "--hosts", type=list, default=json.loads(os.environ["SM_HOSTS"])
    )
    parser.add_argument(
        "--current-host", type=str, default=os.environ["SM_CURRENT_HOST"]
    )
    parser.add_argument("--model-dir", type=str, default=os.environ["SM_MODEL_DIR"])
    parser.add_argument(
        "--data-dir", type=str, default=os.environ["SM_CHANNEL_TRAINING"]
    )
    parser.add_argument("--num-gpus", type=int, default=os.environ["SM_NUM_GPUS"])

    train(parser.parse_args())
