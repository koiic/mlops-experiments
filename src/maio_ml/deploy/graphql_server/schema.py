
from ariadne import make_executable_schema
from ariadne.asgi import GraphQL

from resolvers import query, mutations, parameters
from type import type_defs

# Create type instance for Query type defined in our schema...


schema = make_executable_schema(type_defs, query, mutations, parameters, convert_names_case=True)
app = GraphQL(schema, debug=True)
