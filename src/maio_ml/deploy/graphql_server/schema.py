from ariadne import QueryType, gql, make_executable_schema, MutationType
from ariadne.asgi import GraphQL

from type import type_defs

# Create type instance for Query type defined in our schema...
query = QueryType()
mutations = MutationType()


# ...and assign our resolver function to its "hello" field.
@query.field("data_sources")
def resolve_data_sources(_, info):
    data_sources = []
    for i in range(1, 10):
        data_sources.append({
            "id": str(i),
            "name": f"Data Source {i}"
        })
    return data_sources


@mutations.field("createDataSource")
def resolve_create_data_source(_, info, input):
    return {
        "id": "1",
        "name": input["name"]
    }


schema = make_executable_schema(type_defs, [query, mutations])
app = GraphQL(schema, debug=True)
