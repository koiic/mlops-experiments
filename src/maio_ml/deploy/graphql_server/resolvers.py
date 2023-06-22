from datetime import datetime

from ariadne import QueryType, MutationType, ObjectType, UnionType
from ariadne.exceptions import HttpBadRequestError

query = QueryType()
mutations = MutationType()

models_ = []
model_versions = []
model_signatures = []
model_parameters = []
schedulers = []
schedules_task_history = []


def get_model(model_id):
    for model in models_:
        if model["id"] == int(model_id):
            model.update(
                {"signature": next(
                    signature for signature in model_signatures if signature["model_id"] == int(model_id))})
            model.update(
                {'versions': [model_version for model_version in model_versions if
                              model_version["model_id"] == model_id]}
            )
            return model
    return None


def get_model_version(model_version_id):
    return next((model_version for model_version in model_versions if model_version["id"] == int(model_version_id)), None)


def get_model_version_count(model_id):
    return len([model_version for model_version in model_versions if model_version["model_id"] == model_id])


# ...and assign our resolver function to its "hello" field.
@query.field("datasources")
def resolve_datasources(_, info):
    data_sources = []
    for i in range(1, 10):
        data_sources.append({
            "id": str(i),
            "name": f"Data Source {i}"
        })
    return data_sources


@query.field("mlmodels")
def resolve_mlmodels(_, info):
    # use a map and attach the model signatures for each models
    models = []
    for model in models_:
        model.update(
            {"signature": next(signature for signature in model_signatures if signature["model_id"] == model["id"])})
        models.append(model)
    return models


@query.field("mlmodel")
def resolve_mlmodel(_, info, id):
    return get_model(id)


@query.field("mlmodelversions")
def resolve_mlmodelversions(_, info, model_id):
    return [model_version for model_version in model_versions if model_version["model_id"] == model_id]


@query.field("mlmodelversion")
def resolve_mlmodelversion(_, info, id):
    print(f"model_version_id: {id}", type(id))
    return get_model_version(id)


@query.field("mlmodelscheduler")
def resolve_mlmodelscheduler(_, info, id):
    return next((scheduler for scheduler in schedulers if scheduler["id"] == int(id)), None)


@query.field("mlmodelschedulers")
def resolve_mlmodelschedulers(_, info, model_version_id):
    return [scheduler for scheduler in schedulers if scheduler["model_version_id"] == model_version_id]


@query.field("mlmodelschedulertaskhistory")
def resolve_mlmodelschedulertaskhistory(_, info, model_version_id):
    return [scheduler for scheduler in schedules_task_history if scheduler["model_version_id"] == model_version_id]


@mutations.field("createDataSource")
def resolve_create_data_source(_, info, input):
    return {
        "id": "1",
        "name": input["name"]
    }


def validate_model(data):
    if data["name"].strip() == "":
        raise HttpBadRequestError("Name is required")


@mutations.field("createMLModel")
def resolve_create_ml_model(_, info, input):
    validate_model(input)
    model_id = models_[-1]["id"] + 1 if models_ else 1
    now = datetime.now()
    dt_str = now.strftime("%Y-%m-%d %H:%M:%S")
    signature = input.pop("signature")
    data = dict(**input)
    data["id"] = model_id
    data["created_by"] = 1
    data["created_at"] = dt_str
    data["versions"] = []

    signature["id"] = model_id
    signature["model_id"] = model_id
    model_signatures.append(signature)
    models_.append(data)
    data['signature'] = signature
    return data


@mutations.field("createMLModelVersion")
def resolve_create_ml_model_version(_, info, input):
    # check if the model exists
    model = next((model for model in models_ if model["id"] == int(input["model_id"])), None)
    if model is None:
        raise HttpBadRequestError("Model not found")
    now = datetime.now()
    dt_str = now.strftime("%Y-%m-%d %H:%M:%S")
    parameters = input.pop("parameters")
    data = dict(**input)
    data["id"] = model_versions[-1]["id"] + 1 if model_versions else 1
    data["version"] = get_model_version_count(input["model_id"]) + 1
    data["status"] = "PENDING"
    data["archived"] = False
    data["created_at"] = dt_str
    data["updated_at"] = dt_str

    parameters["id"] = data["id"]
    data['parameters'] = parameters
    model_versions.append(data)
    model = get_model(input["model_id"])
    data['ml_model'] = model

    return data


parameters = UnionType("ModelParameters")


@parameters.type_resolver
def resolve_model_parameters_type(obj, *_):
    if obj['name'] == 'LSTMODEL':
        return "LSTMModelParameters"
    elif obj['name'] == 'VAEMODEL':
        return "VAEModelParameters"
    return None


@mutations.field("updateMLModelVersion")
def resolve_update_ml_model_version(_, info, id, input):
    # check if the model exists
    model_version = get_model_version(id)
    if model_version is None:
        raise HttpBadRequestError("Model version not found")
    now = datetime.now()
    dt_str = now.strftime("%Y-%m-%d %H:%M:%S")
    model_version.update({
        "name": input["name"],
        "description": input["description"],
        "updated_at": dt_str,
        "parameters": input["parameters"],
    })
    model_version['parameters']['id'] = model_version['id']
    return model_version


@mutations.field("updateMLModel")
def resolve_update_ml_model(_, info, id, input):
    # check if the model exists
    model = get_model(id)
    if model is None:
        raise HttpBadRequestError("Model not found")

    # check if the model have version attached, if yes, do not update the signature
    if len(model['versions']) > 0:
        if model['signature']['inputs'] != input['signature']['inputs'] or model['signature']['outputs'] != \
                input['signature']['outputs']:
            raise HttpBadRequestError("Model signature cannot be changed once it has versions")
    now = datetime.now()
    dt_str = now.strftime("%Y-%m-%d %H:%M:%S")
    model.update({
        "name": input["name"],
        "description": input["description"],
        "use_case": input["use_case"],
        "usage_guidelines": input["usage_guidelines"],
        "updated_at": dt_str,
    })
    return model


@mutations.field("deleteMLModelVersion")
def resolve_delete_ml_model_version(_, info, id):
    # check if the model exists
    model_version = get_model_version(id)
    if model_version is None:
        raise HttpBadRequestError("Model version not found")
    # should not be able to delete a model version  that it's status is training or deploying
    if model_version['status'] == 'TRAINING' or model_version['status'] == 'DEPLOYING':
        raise HttpBadRequestError(f"Cannot delete a model version that is {model_version['status']}")
    model_versions.remove(model_version)
    return True


@mutations.field("deleteMLModel")
def resolve_delete_ml_model(_, info, id):
    # check if the model exists
    model = get_model(id)
    if model is None:
        raise HttpBadRequestError("Model not found")
    # delete all versions of the model
    for model_version in model_versions:
        if model_version['model_id'] == int(id):
            model_versions.remove(model_version)
    models_.remove(model)

    return True


@mutations.field("trainMLModelVersion")
def resolve_train_ml_model_version(_, info, id):
    # check if the model exists
    model_version = get_model_version(id)
    if model_version is None:
        raise HttpBadRequestError("Model version not found")

    if model_version['status'] == 'DEPLOYED':
        raise HttpBadRequestError(f"Cannot train a model that is already deployed")
    # should not be able to train a model version that it's status is training or deploying
    if model_version['status'] == 'TRAINING' or model_version['status'] == 'DEPLOYING':
        raise HttpBadRequestError(f"Cannot train a model that is currently {model_version['status']}")

    # TODO: call the api gateway to train the model

    model_version['status'] = 'TRAINED'
    return model_version


@mutations.field("deployMLModelVersion")
def resolve_deploy_ml_model_version(_, info, id):
    # check if the model exists
    model_version = get_model_version(int(id))
    if model_version is None:
        raise HttpBadRequestError("Model version not found")
    # should not be able to deploy a model version that it's status is training or deploying
    if model_version['status'] == 'TRAINING' or model_version['status'] == 'DEPLOYING':
        raise HttpBadRequestError(f"Cannot deploy a model version that is {model_version['status']}")

    # check if the model is trained
    if model_version['status'] != 'TRAINED':
        raise HttpBadRequestError(f"Cannot deploy a model version that is not trained")

    # TODO: call the api gateway to deploy the model
    model_version['status'] = 'DEPLOYED'
    return model_version


@mutations.field("undeployMLModelVersion")
def resolve_undeploy_ml_model_version(_, info, id):
    # check if the model exists
    model_version = get_model_version(id)
    if model_version is None:
        raise HttpBadRequestError("Model version not found")
    # should not be able to undeploy a model version that it's status is training or deploying
    if model_version['status'] == 'TRAINING' or model_version['status'] == 'DEPLOYING':
        raise HttpBadRequestError(f"Cannot undeploy a model version that is {model_version['status']}")

    # check if the model is deployed
    if model_version['status'] != 'DEPLOYED':
        raise HttpBadRequestError(f"Cannot undeploy a model version that is not deployed")

    model_version['status'] = 'UNDEPLOYED'
    return model_version


@mutations.field("createMLModelScheduler")
def resolve_create_ml_model_scheduler(_, info, input):
    # check if the model version exists
    model_version = get_model_version(int(input['model_version_id']))
    if model_version is None:
        raise HttpBadRequestError("Model version not found")
    # check if the model version is deployed
    if model_version['status'] != 'DEPLOYED':
        raise HttpBadRequestError("Cannot create a scheduler for a model version that is not deployed")

    now = datetime.now()
    dt_str = now.strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "id": len(schedulers) + 1,
        "created_at": dt_str,
        "updated_at": dt_str,
        "model_version_id": input['model_version_id'],
        "seconds_to_repeat": input['seconds_to_repeat'],
        "datasource_id": input['datasource_id'],
        "start_time": input['start_time'],
        "enabled": True,
        "created_by": 1
    }
    data['model_version'] = get_model_version(data['model_version_id'])
    schedulers.append(data)

    # if enabled is true, create a job for the scheduler
    if data['enabled']:
        schedule_counts = len(schedules_task_history)
        schedule = {
            "id": schedule_counts + 1,
            "counter": 1,
            "status": "PENDING",
            "failureReason": "",
            "errorMessage": "",
            "model_version_id": data['model_version_id'],
            "start_execution": dt_str,
            "end_execution": dt_str,
            "execution_Duration": None,
            "successfulRuns": 0,
        }
        schedules_task_history.append(schedule)

    return data
