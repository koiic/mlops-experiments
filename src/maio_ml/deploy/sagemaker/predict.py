import sys

sys.path.append(".")
import argparse
import json
import os
import re
import tarfile
from datetime import datetime, timedelta, timezone

import boto3
import pandas as pd
import sagemaker
from deploy_env import DeployEnv
from maio_python import Client
from sagemaker.pytorch import PyTorchModel

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # hyperparameters sent by the client are passed as command-line arguments to the script.
    # parser.add_argument('--train', action='store_true', help="Use to train the model.")

    env = DeployEnv()

    maio_client = Client("https://engine.heineken.maio.io", token="7EBlJRDyNuJRftXOENSAttekNN4Azu") # os.getenv("MAIO_TOKEN"))

    t0 = datetime(2023, 5, 8, 10, 0, 0, tzinfo=timezone.utc)

    gateway_id = maio_client.get_gateway_id_from_name("Aruba")
    assert gateway_id is not None

    # every 15 minutes for 6 hours
    for dt_ in range(0, 60*24*3, 60):
        t2 = t0 + timedelta(minutes=dt_)
        t1 = t2 - timedelta(minutes=256)

        _, df_maio = maio_client.get_tag_entries_for_gateway(gateway_id, t1, t2)

        mapping_columns = {"CoolerTemp": "cooler_temp", "BathTemp": "bath_temp", "CoolerSwitch": "cooler_switch", "RefridgentTemp": "refridgent_temp", "CompressorCurrent": "compressor_current", "timestamps": "timestamp"}

        df_maio_small = df_maio[mapping_columns.keys()].rename(columns=mapping_columns)

        df_maio_small['timestamp'] = pd.to_datetime(df_maio_small['timestamp'])
        df_maio_small = df_maio_small.set_index('timestamp')

        print(f"{df_maio_small.shape[0]} over 257")

        # Resample the dataframe to 1 minute
        df_maio_small_resampled = df_maio_small.resample("1Min").mean()

        # Fill missing values with the previous value
        df_maio_small_resampled = df_maio_small_resampled.fillna(method="ffill")

        df_maio_small_resampled.reset_index(inplace=True)

        # # Reset the index
        # df_maio_small_resampled.set_index(inplace=True)

        # Drop the timestamp column
        df_maio_small_resampled.drop(columns=['timestamp'], axis=1, inplace=True)

        # Invoke the SM endpoint
        response = env.runtime_client().invoke_endpoint(
            EndpointName=env.setting('model_name'),
            ContentType="application/json",
            Accept="application/json",
            Body=df_maio_small_resampled.to_json(orient='split', index=False)
        )

        # Transform the response to a string
        data = response['Body'].read().decode("utf-8")

        anom_score = pd.read_json(json.loads(data), orient='split')

        print(f"time: {t2} - anomaly detected: {anom_score.ge(4.5).any()['anom_score']} - {anom_score.ge(4.5).sum()['anom_score']}")
