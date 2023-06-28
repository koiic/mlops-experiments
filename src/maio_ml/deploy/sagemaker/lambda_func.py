import json
from datetime import timezone, datetime, timedelta

import boto3
import pandas as pd
from maio_python import Client


def fetch_data_from_maio(base_url, token, gateway_name, start_time, end_time):
    # Creating MAIO client
    maio_client = Client(base_url, token=token)
    # Get gateway Id
    gateway_id = maio_client.get_gateway_id_from_name(gateway_name)

    assert gateway_id is not None

    # convert start_time and end_time to datetime objects
    start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S.%fZ')
    end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S.%fZ')

    _, df_maio = maio_client.get_tag_entries_for_gateway(gateway_id, start_time, end_time)

    return df_maio


def clean_up_data(base_url, token, gateway_name, start_time, end_time):
    # Get data from MAIO
    df_maio = fetch_data_from_maio(base_url, token, gateway_name, start_time, end_time)

    mapping_columns = {"CoolerTemp": "cooler_temp", "BathTemp": "bath_temp", "CoolerSwitch": "cooler_switch",
                       "RefridgentTemp": "refridgent_temp", "CompressorCurrent": "compressor_current",
                       "timestamps": "timestamp"}

    df_maio_small = df_maio[mapping_columns.keys()].rename(columns=mapping_columns)

    df_maio_small['timestamp'] = pd.to_datetime(df_maio_small['timestamp'])
    df_maio_small = df_maio_small.set_index('timestamp')

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
    base_url = "https://engine.heineken.maio.io"
    gateway_name = 'Aruba'
    start_time = '2023-05-08T10:00:00.000000Z'
    end_time = '2023-05-08T11:00:00.000000Z'
    token = 'lqaYNKBQD7gUfSR3dwOB3Llrk8Ujoa'
    endpoint = 'pytorch-anomaly-classification-2023-05-21-06-50-14-925'

    """ check if token is passed in the header, throw forbidden error if not"""
    if 'headers' in event:
        if 'oauth_token' in event['headers']:
            token = event['headers']['oauth_token']
        else:
            message = 'access token is missing'
            return {
                'statusCode': 403,
                'body': json.dumps('Forbidden Error: {}'.format(message)),
            }


    if 'queryStringParameters' in event:
        event = event['queryStringParameters']

    if 'base_url' in event:
        base_url = event['base_url']

    if 'gateway_name' in event:
        gateway_name = event['gateway_name']

    if 'start_time' in event:
        start_time = event['start_time']

    if 'end_time' in event:
        end_time = event['end_time']

    # if 'token' in event:
    #     token = event['token']

    if 'endpoint' in event:
        endpoint = event['endpoint']

    df_maio_small_resampled = clean_up_data(base_url, token, gateway_name, start_time, end_time)
    # base_endpoint = 'pytorch-anomaly-classification-2023-05-21-06-50-14-925'

    # Invoke the SM endpoint
    runtime_client = boto3.client('sagemaker-runtime')
    response = runtime_client.invoke_endpoint(
        EndpointName=endpoint,
        ContentType="application/json",
        Accept="application/json",
        Body=df_maio_small_resampled.to_json(orient='split', index=False)
    )

    # Transform the response to a string
    data = response['Body'].read().decode("utf-8")

    anom_score = pd.read_json(json.loads(data), orient='split')

    result = dict(
        anomaly_detected=str(anom_score.ge(4.5).any()['anom_score']),
        count=int(anom_score.ge(4.5).sum()['anom_score'])
    )

    return result
