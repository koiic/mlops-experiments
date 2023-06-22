import json
import logging

from ariadne.asgi import GraphQL
from mangum import Mangum
from schema import schema

logger = logging.getLogger()

app = GraphQL(schema, debug=True)

# Create the Ariadne app
handler = Mangum(app)


def response(body: dict, status_code: int = 200):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body),
    }
