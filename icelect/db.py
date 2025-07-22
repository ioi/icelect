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

class ElectionState(StrEnum):
    init = auto()
    voting = auto()
    counting = auto()
    results = auto()


class Election(Base):
    __tablename__ = 'elections'

    election_id: Mapped[ElectionId] = col(primary_key=True)
    ident: Mapped[str]
    name: Mapped[str]
    state: Mapped[ElectionState]
    config: Mapped[Any] = col(JSONB)
    election_key: Mapped[str]
    verify_key: Mapped[str]

    cred_hashes: Mapped['CredHash'] = relationship()
    ballots: Mapped['Ballot'] = relationship()
    verifiers: Mapped['Verifier'] = relationship()


class CredHash(Base):
    __tablename__ = 'cred_hashes'

    election_id: Mapped[ElectionId] = col(ForeignKey('elections.election_id'), primary_key=True)
    hash: Mapped[str] = col(primary_key=True)

    election: Mapped[Election] = relationship()


class Ballot(Base):
    __tablename__ = 'ballots'

    election_id: Mapped[ElectionId] = col(ForeignKey('elections.election_id'), primary_key=True)
    receipt: Mapped[str] = col(primary_key=True)
    ranks: Mapped[list[int]] = col(ARRAY(int))

    election: Mapped[Election] = relationship()


class Verifier(Base):
    __tablename__ = 'verifiers'

    election_id: Mapped[ElectionId] = col(ForeignKey('elections.election_id'), primary_key=True)
    verifier: Mapped[str] = col(primary_key=True)

    election: Mapped[Election] = relationship()


current_session: Optional[Session] = None


def get_session() -> Session:
    global current_session
    if current_session is None:
        current_session = new_session()
    return current_session


def new_session() -> Session:
    engine = create_engine(
        config.SQLALCHEMY_DATABASE_URI,
        echo=config.SQLALCHEMY_DEBUG,
    )

    sqla_logger = logging.getLogger('sqlalchemy.engine.base.Engine')
    sqla_logger.addHandler(logging.NullHandler())

    if config.SQLALCHEMY_DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.DEBUG)

    return Session(engine)
