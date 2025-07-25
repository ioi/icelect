from enum import StrEnum, auto
import logging
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, relationship
from sqlalchemy.orm import mapped_column as col
import sqlalchemy.types as t
from typing import Optional, NewType, Any

import icelect.config as config


ElectionId = NewType('ElectionId', int)


class Base(DeclarativeBase):
    type_annotation_map = {
        ElectionId: t.Integer,
    }


class MyEnum(StrEnum):
    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        out = []
        for item in cls:
            out.append((item.name, item.friendly_name()))
        return out

    def friendly_name(self) -> str:
        return str(self)

    @classmethod
    def coerce(cls, name):
        if isinstance(name, cls):
            return name
        try:
            return cls[name]
        except KeyError:
            raise ValueError(name)


class ElectionState(MyEnum):
    init = auto()
    voting = auto()
    counting = auto()
    results = auto()


class Election(Base):
    __tablename__ = 'elections'

    election_id: Mapped[ElectionId] = col(primary_key=True)
    ident: Mapped[str]
    state: Mapped[ElectionState]
    config: Mapped[Any] = col(JSONB)
    election_key: Mapped[str]
    verify_key: Mapped[str]
    order: Mapped[int] = col(default=0)

    cred_hashes: Mapped['CredHash'] = relationship(back_populates='election')
    ballots: Mapped['Ballot'] = relationship(back_populates='election')
    verifiers: Mapped['Verifier'] = relationship(back_populates='election')
    results: Mapped['Result'] = relationship(back_populates='election')


class CredHash(Base):
    __tablename__ = 'cred_hashes'

    election_id: Mapped[ElectionId] = col(ForeignKey('elections.election_id'), primary_key=True)
    hash: Mapped[str] = col(primary_key=True)

    election: Mapped[Election] = relationship()


class Ballot(Base):
    __tablename__ = 'ballots'

    election_id: Mapped[ElectionId] = col(ForeignKey('elections.election_id'), primary_key=True)
    receipt: Mapped[str] = col(primary_key=True)
    nonce: Mapped[str]
    ranks: Mapped[list[int]] = col(ARRAY(t.Integer))

    election: Mapped[Election] = relationship()


class Verifier(Base):
    __tablename__ = 'verifiers'

    election_id: Mapped[ElectionId] = col(ForeignKey('elections.election_id'), primary_key=True)
    verifier: Mapped[str] = col(primary_key=True)

    election: Mapped[Election] = relationship()


class Result(Base):
    __tablename__ = 'results'

    election_id: Mapped[ElectionId] = col(ForeignKey('elections.election_id'), primary_key=True)
    result: Mapped[Any] = col(JSONB)

    election: Mapped[Election] = relationship()


current_session: Optional[Session] = None
flask_db: Any = None


def get_session() -> Session:
    global current_session
    if current_session is None:
        if flask_db is not None:
            current_session = flask_db.session
        else:
            current_session = new_session()
    return current_session


def new_session() -> Session:
    engine = create_engine(
        config.SQLALCHEMY_DATABASE_URI,
        echo=config.SQLALCHEMY_ECHO,
        isolation_level='SERIALIZABLE',
    )

    sqla_logger = logging.getLogger('sqlalchemy.engine.base.Engine')
    sqla_logger.addHandler(logging.NullHandler())

    if config.SQLALCHEMY_DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.DEBUG)

    return Session(engine)
