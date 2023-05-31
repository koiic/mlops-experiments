import json
from datetime import timezone, datetime, timedelta

import boto3
import pandas as pd
from maio_python import Client


def fetch_data_from_maio(event):
    # Retrieve the payload from the API Gateway request

    BASE_URL = "https://engine.heineken.maio.io"

    gateway_name = event['gateway_name']
    token = event['token']
    start_time = event['start_time']
    end_time = event['end_time']
    base_url = event['base_url']

    # using heineken as the base case
    if base_url is None:
        base_url = BASE_URL
    maio_client = Client(base_url, token=token)

    gateway_id = maio_client.get_gateway_id_from_name(gateway_name)

    assert gateway_id is not None

    # convert start_time and end_time to datetime objects
    start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S.%fZ')
    end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S.%fZ')

    _, df_maio = maio_client.get_tag_entries_for_gateway(gateway_id, start_time, end_time)

    return df_maio


def clean_up_data(event):
    df_maio = fetch_data_from_maio(event)

    mapping_columns = {"CoolerTemp": "cooler_temp", "BathTemp": "bath_temp", "CoolerSwitch": "cooler_switch",
                       "RefridgentTemp": "refridgent_temp", "CompressorCurrent": "compressor_current",
                       "timestamps": "timestamp"}

    df_maio_small = df_maio[mapping_columns.keys()].rename(columns=mapping_columns)

    df_maio_small['timestamp'] = pd.to_datetime(df_maio_small['timestamp'])
    df_maio_small = df_maio_small.set_index('timestamp')

    # print(f"{df_maio_small.shape[0]} over 257")

    # Resample the dataframe to 1 minute
    df_maio_small_resampled = df_maio_small.resample("1Min").mean()

    # Fill missing values with the previous value
    df_maio_small_resampled = df_maio_small_resampled.fillna(method="ffill")

    df_maio_small_resampled.reset_index(inplace=True)

    # # Reset the index
    # df_maio_small_resampled.set_index(inplace=True)

    # Drop the timestamp column
    df_maio_small_resampled.drop(columns=['timestamp'], axis=1, inplace=True)
    return df_maio_small_resampled


def lambda_handler(event, context):
    # Retrieve the payload from the API Gateway request
    # Retrieve the payload from the API Gateway request
    df_maio_small_resampled = clean_up_data(event)
    base_endpoint = 'pytorch-anomaly-classification-2023-05-21-06-50-14-925'

    if event.get('endpoint') is None:
        event['endpoint'] = base_endpoint

    # Invoke the SM endpoint
    runtime_client = boto3.client('sagemaker-runtime')
    response = runtime_client.invoke_endpoint(
        EndpointName=event['endpoint'],
        ContentType="application/json",
        Accept="application/json",
        Body=df_maio_small_resampled.to_json(orient='split', index=False)
    )

    # Transform the response to a string
    data = response['Body'].read().decode("utf-8")

    anom_score = pd.read_json(json.loads(data), orient='split')

    result = dict(
        time=event['end_time'],
        anomaly_detected=str(anom_score.ge(4.5).any()['anom_score']),
        count=int(anom_score.ge(4.5).sum()['anom_score'])

    )

    return result
