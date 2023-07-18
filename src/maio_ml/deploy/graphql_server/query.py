from ariadne import QueryType, ScalarType, UnionType
from sqlalchemy import select

from model import Datasource, MlModel, MlModelVersion, MlModelScheduler, MlAlgorithm, \
    MlModelSchedulerHistory

query = QueryType()

datetime_scalar = ScalarType("DateTime")
tag_interface = UnionType("TagInterface")


@datetime_scalar.serializer
def serialize_datetime(value):
    return value.isoformat()


@tag_interface.type_resolver
def resolve_tag_interface_type(obj, *_):
    return "MLModelTag"


@query.field("datasources")
def resolve_datasources(root, info):
    db = info.context["db"]
    return db.scalars(select(Datasource))


@query.field("mlmodels")
def resolve_mlmodels(_, info):
    # use a map and attach the model signatures for each models
    db = info.context["db"]
    return db.scalars(select(MlModel))


@query.field("mlmodel")
def resolve_mlmodel(_, info, id):
    db = info.context["db"]
    qs = db.get(MlModel, id)
    return qs


@query.field("mlmodelversions")
def resolve_mlmodelversions(_, info, model_id):
    db = info.context["db"]
    qs = db.scalars(select(MlModelVersion).filter(MlModelVersion.ml_model_id == model_id)).all()
    return qs


@query.field("mlmodelversion")
def resolve_mlmodelversion(_, info, id):
    db = info.context["db"]
    return db.get(MlModelVersion, id)


@query.field("mlmodelscheduler")
def resolve_mlmodelscheduler(_, info, id):
    db = info.context["db"]
    return db.get(MlModelScheduler, id)


@query.field("mlmodelschedulers")
def resolve_mlmodelschedulers(_, info, model_version_id):
    db = info.context["db"]
    return db.query(MlModelScheduler).filter(MlModelScheduler.ml_model_version_id == model_version_id).all()


@query.field("mlalgorithms")
def resolve_mlalgorithms(_, info):
    db = info.context["db"]
    query = db.scalars(select(MlAlgorithm))
    return query


@query.field("mlalgorithm")
def resolve_mlalgorithm(_, info, id):
    db = info.context["db"]
    return db.get(MlAlgorithm, id)


@query.field("mlmodelschedulertaskhistory")
def resolve_mlmodelschedulertaskhistory(_, info, model_scheduler_id):
    db = info.context["db"]
    return db.scalars(select(MlModelSchedulerHistory).filter_by(ml_model_scheduler_id = model_scheduler_id)).all()
