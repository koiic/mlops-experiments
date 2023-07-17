from __future__ import annotations

from ariadne import make_executable_schema
from ariadne.asgi import GraphQL
from ariadne.asgi.handlers import GraphQLTransportWSHandler
from fastapi import FastAPI, Depends, Request
from fastapi.websockets import WebSocket

from mutation import mutations
import model
from database import engine, SessionLocal
from type import type_defs
from query import query, tag_interface, datetime_scalar

# Create type instance for Query type defined in our schema...

model.Base.metadata.create_all(bind=engine)

schema = make_executable_schema(type_defs, query, mutations, tag_interface, datetime_scalar, convert_names_case=True)
# app = GraphQL(schema, debug=True)

# Mount Ariadne GraphQL as sub-application for FastAPI
app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Custom context setup method
def get_context_value(request_or_ws: Request | WebSocket, _data) -> dict:
    return {
        "request": request_or_ws,
        "db": request_or_ws.scope.get("db"),
    }


# Create GraphQL App instance
graphql_app = GraphQL(
    schema,
    debug=True,
    context_value=get_context_value,
    websocket_handler=GraphQLTransportWSHandler(),
)


# Handle GET requests to serve GraphQL explorer
# Handle OPTIONS requests for CORS
@app.get("/graphql/")
@app.options("/graphql/")
async def handle_graphql_explorer(request: Request):
    return await graphql_app.handle_request(request)


# Handle POST requests to execute GraphQL queries
@app.post("/graphql/")
async def handle_graphql_query(
        request: Request,
        db=Depends(get_db),
):
    # Expose database connection to the GraphQL through request's scope
    request.scope["db"] = db
    return await graphql_app.handle_request(request)


# Handle GraphQL subscriptions over websocket
@app.websocket("/graphql")
async def graphql_subscriptions(
        websocket: WebSocket,
        db=Depends(get_db),
):
    # Expose database connection to the GraphQL through request's scope
    websocket.scope["db"] = db
    await graphql_app.handle_websocket(websocket)


# app.mount("/graphql/", GraphQL(schema, debug=True))
