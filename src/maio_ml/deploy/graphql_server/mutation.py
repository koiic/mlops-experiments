from ariadne import MutationType
from ariadne.exceptions import HttpBadRequestError
from sqlalchemy import select, func

from model import MlModel, MlModelTag, Datasource, MlAlgorithm, MlModelVersion

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
    algorithm = MlAlgorithm(
        name=input["name"],
        description=input["description"],
        parameters=input["parameters"],
    )
    db.add(algorithm)
    db.commit()
    db.refresh(algorithm)
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
    db.add(model)
    db.commit()
    db.refresh(model)
    # create a model tag
    tag = MlModelTag(**input["output_tag"])
    # get the model id
    model = db.query(MlModel).filter(MlModel.name == input["name"]).first()
    tag.ml_model_id = model.id
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return model


@mutations.field("createMLModelVersion")
def resolve_create_ml_model_version(_, info, input):
    db = info.context["db"]

    algorithm = input.pop("algorithm", None)
    # create the model version
    model_version = MlModelVersion(**input)
    model_version.save(db)
    # create the model algorithm from the selected algorithm
    if algorithm is not None:
        model_algorithm = db.scalars(select(MlAlgorithm).filter_by(id=algorithm['id'])).first()
        print(model_algorithm, "_+_+NMNK", type(model_algorithm))

        model_algorithm.ml_model_version_id = model_version.id
        model_algorithm.parameters = algorithm['parameters']
        model_algorithm.save(db)

    return model_version
