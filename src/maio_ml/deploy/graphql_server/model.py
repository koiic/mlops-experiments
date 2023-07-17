import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, UniqueConstraint, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import relationship, Mapped, mapped_column, Session

from database import Base


class Model(object):

    def save(self, session: Session, **kwargs):
        try:
            session.add(self)
            session.commit()
            session.refresh(self)
        except SQLAlchemyError as e:
            session.rollback()
            raise e


class User(Base, Model):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    fullname: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"


class Tag(Model):
    label = mapped_column(String, index=True)
    display_name = mapped_column(String)
    unit = mapped_column(String)
    type = mapped_column(String)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.label}"


class MlModelTag(Base, Tag):
    __tablename__ = "ml_model_tag"
    # set a unique constraint on the label and ml_model_id
    __table_args__ = (UniqueConstraint("ml_model_id", "label", name="unique_model_tag_label"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ml_model_id: Mapped[int] = mapped_column(Integer, ForeignKey("ml_model.id"))

    def __str__(self):
        return f"{self.label}"


class GatewayTag(Base, Tag):
    __tablename__ = "gateway_tag"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    datasource_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasource.id"))

    # tag_entries = relationship("GatewayTagEntry", back_populates="tag")

    def __str__(self):
        return f"{self.label}"


class Datasource(Base, Model):
    __tablename__ = "datasource"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))

    def __repr__(self) -> str:
        return f"Datasource(id={self.id!r}, name={self.name!r})"


class MlModel(Base, Model):
    __tablename__ = "ml_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[str] = mapped_column(DateTime, default=datetime.utcnow)
    datasource_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasource.id"))
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_account.id"))
    versions: Mapped[List["MlModelVersion"]] = relationship(backref="ml_model", lazy="dynamic")
    output_tag: Mapped[Optional["MlModelTag"]] = relationship("MlModelTag")
    datasource: Mapped[Optional["Datasource"]] = relationship("Datasource")

    def __str__(self):
        return f"{self.name}"

    def max_version(self, session: Session):
        """
        Return the maximum of the currently stored version.
        """
        try:
            # check if there are any versions
            if self.versions:
                max_version = session.query(func.max(MlModelVersion.version).filter(
                    MlModelVersion.ml_model_id == self.id)).scalar()
                if max_version is None:
                    return 0
                return max_version
            return 0
        except SQLAlchemyError as excep:
            print(str(excep))
            self.logger.exception(excep)
        return 0


# create a status enum
class StatusEnum(enum.Enum):
    pending = "PENDING"
    training = "TRAINING"
    deployed = "DEPLOYED"
    undeployed = "UNDEPLOYED"
    trained = "TRAINED"


class MlModelVersion(Base, Model):
    __tablename__ = "ml_model_version"

    id: Mapped[Optional[int]] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[int] = mapped_column(Integer)
    ml_model_id = mapped_column(Integer, ForeignKey("ml_model.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    datasource_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("datasource.id"), nullable=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    training_percentage: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    status: Mapped[StatusEnum] = mapped_column(String, default=StatusEnum.pending.value)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    algorithm: Mapped[Optional["MlAlgorithm"]] = relationship("MlAlgorithm")

    class Meta:
        pass

    def __str__(self):
        return f"{self.name}:{self.version}"

        # overide the save method

    def save(self, db: Session, **kwargs):
        # get the related ml_model
        ml_model = db.get(MlModel, self.ml_model_id)
        if not self.version:
            self.version = ml_model.max_version(db) + 1
        super().save(db, **kwargs)


class MlAlgorithm(Base, Model):
    __tablename__ = "ml_algorithm"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # settings are stored as a postgres jsonblob dict
    parameters: Mapped[List] = mapped_column(postgresql.JSONB(astext_type=String))
    ml_model_version: Mapped[int] = mapped_column(ForeignKey("ml_model_version.id"), nullable=True)

    def __str__(self):
        return f"{self.name}"


class MlModelScheduler(Base, Model):
    __tablename__ = "ml_model_scheduler"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ml_model_version_id: Mapped[int] = mapped_column(ForeignKey("ml_model_version.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime)
    seconds_to_repeat: Mapped[int] = mapped_column(Integer, default=0)
    datasource_id: Mapped[int] = mapped_column(ForeignKey("datasource.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_account.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_account.id"))

    def __str__(self):
        return f"{self.id}:{self.ml_model_version_id}:{self.start_time}"


class TaskStatusEnum(enum.Enum):
    pending = "PENDING"
    preparing = "PREPARING"
    running = "RUNNING"
    failed = "FAILED"
    successful = "SUCCESSFUL"


class MlModelSchedulerHistory(Base, Model):
    __tablename__ = "ml_model_scheduler_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ml_model_scheduler_id: Mapped[int] = mapped_column(ForeignKey("ml_model_scheduler.id"))
    start_execution: Mapped[datetime] = mapped_column(DateTime)
    end_execution: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[StatusEnum] = mapped_column(String, default=TaskStatusEnum.pending)
    execution_duration: Mapped[int] = mapped_column(Integer, default=0)
    successful_run: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_account.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_account.id"))

    def __str__(self):
        return f"{self.id}:{self.ml_model_scheduler_id}:{self.start_execution}"
