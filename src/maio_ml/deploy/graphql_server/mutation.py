import json

from ariadne import MutationType
from ariadne.exceptions import HttpBadRequestError

from model import MlModel, MlModelTag, Datasource, MlAlgorithm, MlModelVersion, StatusEnum, MlModelDeployment, \
    MlModelScheduler

mutations = MutationType()


@mutations.field("createDatasource")
def resolve_create_datasource(_, info, name):
    db = info.context["db"]
    datasource = Datasource(
        name=name,
    )
    db.add(datasource)
    db.commit()
    db.refresh(datasource)
    return datasource


@mutations.field("createMlAlgorithm")
def resolve_create_ml_algorithm(_, info, input):
    # get the db
    db = info.context["db"]

    # check if the algorithm exists
    algorithm = db.query(MlAlgorithm).filter(MlAlgorithm.name == input["name"]).first()
    if algorithm is not None:
        raise HttpBadRequestError("Algorithm already exists")

    # create the algorithm
    algorithm = MlAlgorithm(**input)
    algorithm.save(db)
    return algorithm


@mutations.field("createMLModel")
def resolve_create_ml_model(_, info, input):
    # get the db
    db = info.context["db"]

    # check if the model exists
    model = db.query(MlModel).filter(MlModel.name == input["name"]).first()
    if model is not None:
        raise HttpBadRequestError("Model already exists")

    # create the model
    model = MlModel(
        name=input["name"],
        description=input["description"],
        datasource_id=input["datasource_id"],
        created_by_id=1,
    )
    model.save(db)
    # create a model tag
    tag = MlModelTag(**input["output_tag"])
    # get the model id
    model = db.query(MlModel).filter(MlModel.name == input["name"]).first()
    tag.ml_model_id = model.id
    tag.save(db)
    return model


@mutations.field("updateMLModel")
def resolve_update_ml_model(_, info, input, id):
    # you can only update the datasource if the model doesn't have any versions
    db = info.context["db"]

    # get the model
    model = db.get(MlModel, id)
    if model is None:
        raise HttpBadRequestError("Model doesn't exist")

    # check if the model has any versions
    if model.versions is not None:
        raise HttpBadRequestError("Model has versions, cannot update the datasource")

    # update the model
    # loop through the input and update the model
    for key, value in input.items():
        setattr(model, key, value)
    model.save(db)

    return model


@mutations.field("deleteMLModel")
def resolve_delete_ml_model(_, info, id):
    db = info.context["db"]
    model = db.get(MlModel, id)
    if model is None:
        raise HttpBadRequestError("Model doesn't exist")
    db.delete(model)
    db.commit()
    return True


@mutations.field("createMLModelVersion")
def resolve_create_ml_model_version(_, info, input):
    db = info.context["db"]

    algorithm = input.pop("algorithm", None)

    if algorithm is not None:
        model_algorithm = db.query(MlAlgorithm).get(algorithm['id'])
        # TODO: the parameter value differs because of case sensitivity, write a function to convert the case
        a, b = json.dumps(model_algorithm.parameters, sort_keys=True), json.dumps(algorithm['parameters'],
                                                                                  sort_keys=True)
        if model_algorithm is not None and a != b:
            model_algorithm_ = MlAlgorithm(
                name=model_algorithm.name,
                description=model_algorithm.description,
                parameters=algorithm['parameters'],
            )
            model_algorithm_.save(db)
            input['algorithm_id'] = model_algorithm_.id
        elif model_algorithm is not None:
            input['algorithm_id'] = model_algorithm.id

    # create the model version
    model_version = MlModelVersion(**input)
    model_version.save(db)

    # TODO : call the background task for training the model
    return model_version


@mutations.field("updateMLModelVersion")
def resolve_update_ml_model_version(_, info, input, id):
    db = info.context["db"]

    # get the model version
    model_version = db.query(MlModelVersion).get(id)
    if model_version is None:
        raise HttpBadRequestError("Model version does not exist")

    algorithm = input.pop("algorithm", None)

    if algorithm is not None:
        model_algorithm = db.query(MlAlgorithm).get(algorithm['id'])
        # TODO: the parameter value differs because of case sensitivity, write a function to convert the case
        a, b = json.dumps(model_algorithm.parameters, sort_keys=True), json.dumps(algorithm['parameters'],
                                                                                  sort_keys=True)
        if model_algorithm is not None and a != b:
            model_algorithm_ = MlAlgorithm(
                name=model_algorithm.name,
                description=model_algorithm.description,
                parameters=algorithm['parameters'],
            )
            model_algorithm_.save(db)
            input['algorithm_id'] = model_algorithm_.id
        elif model_algorithm is not None:
            input['algorithm_id'] = model_algorithm.id

    # update the model version
    for key, value in input.items():
        setattr(model_version, key, value)

    model_version.save(db)

    # TODO : call the background task for training the model
    return model_version


@mutations.field("deleteMLModelVersion")
def resolve_delete_ml_model_version(_, info, id):
    db = info.context["db"]

    # get the model version
    model_version = db.query(MlModelVersion).get(id)
    if model_version is None:
        raise HttpBadRequestError("Model version does not exist")

    # delete the model version
    db.delete(model_version)
    db.commit()

    return True


@mutations.field("deployMLModelVersion")
def resolve_deploy_ml_model_version(_, info, id):
    db = info.context["db"]

    # get the model version
    model_version = db.query(MlModelVersion).get(id)
    if model_version is None:
        raise HttpBadRequestError("Model version does not exist")

    # check if the model version is already deployed
    if model_version.deployed:
        raise HttpBadRequestError("Model version is already deployed")

    # check if the model version is trained
    if not model_version.trained:
        raise HttpBadRequestError("Model version is not trained")

    # TODO : call the function to deploy the model (AWS Sagemaker)

    # create the deployment configuration
    deployment = MlModelDeployment(
        ml_model_version_id=model_version.id,
        deployment_config="",
        endpoint="",

    )
    deployment.save(db)

    # update the model version status to deploying
    model_version.status = StatusEnum.deploying.value
    model_version.save(db)
    return model_version


@mutations.field("undeployMLModelVersion")
def resolve_undeploy_ml_model_version(_, info, id):
    db = info.context["db"]

    # get the model version
    model_version = db.query(MlModelVersion).get(id)
    if model_version is None:
        raise HttpBadRequestError("Model version does not exist")

    # check if the model version is already deployed
    if not model_version.deployed:
        raise HttpBadRequestError("Model version is not deployed")

    # TODO : call the background task for undeploying the model
    # delete the deployment configuration
    db.delete(model_version.deployment)

    # update the model version status to deploying
    model_version.status = StatusEnum.undeployed.value
    model_version.save(db)
    return model_version


@mutations.field("createMLModelScheduler")
def resolve_create_ml_model_scheduler(_, info, input):
    db = info.context["db"]

    # get the model version
    model_version = db.query(MlModelVersion).get(input['ml_model_version_id'])

    if model_version is None:
        raise HttpBadRequestError("Model version does not exist")

    # check if the model version is already deployed
    if not model_version.deployed:
        raise HttpBadRequestError("Model version is not deployed")

    # TODO: call the background task to create an aws event rule

    # listen to the event rule and update the status of the model version

    # create the scheduler
    scheduler = MlModelScheduler(**input)
    scheduler.save(db)

    return scheduler


@mutations.field("deleteMLModelScheduler")
def resolve_delete_ml_model_scheduler(_, info, id):
    db = info.context["db"]

    # get the scheduler
    scheduler = db.query(MlModelScheduler).get(id)

    if scheduler is None:
        raise HttpBadRequestError("Scheduler does not exist")

    db.delete(scheduler)
    db.commit()

    return True
