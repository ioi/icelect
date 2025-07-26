# Icelect - Representation of elections
# (c) 2025 Martin Mareš <mj@ucw.cz>

import csv
from sqlalchemy import select
import tomllib
from typing import Any

from icelect.crypto import gen_key
import icelect.db as db
from icelect.json_walker import Walker, WalkerError
from icelect.results import Results


class ConfigError(ValueError):
    pass


class ElectionData:
    ident: str
    title: str
    options: list[str]
    num_options: int
    config: Any
    election_key: str
    verify_key: str
    ballots: list[db.Ballot]

    def __init__(self, ident: str):
        self.ident = ident

    @classmethod
    def from_config_file(cls, ident: str) -> 'ElectionData':
        try:
            with open(f'elections/{ident}.toml', 'rb') as file:
                config = tomllib.load(file)
        except tomllib.TOMLDecodeError as err:
            raise ConfigError(str(err))
        except FileNotFoundError:
            raise ConfigError('File not found')

        ed = ElectionData(ident)
        ed._parse_config(config)
        ed.election_key = gen_key()
        ed.verify_key = gen_key()
        return ed

    @classmethod
    def from_db(cls, election: db.Election) -> 'ElectionData':
        ed = ElectionData(election.ident)
        ed._parse_config(election.config)
        ed.election_key = election.election_key
        ed.verify_key = election.verify_key
        return ed

    def _parse_config(self, config: Any) -> None:
        try:
            root = Walker(config).enter_object()
            self.title = root['title'].as_str()
            options = root['options']
            self.options = [val.as_str() for val in options.array_values()]
            self.num_options = len(self.options)
            if self.num_options < 2:
                options.raise_error("There must be at least 2 options")
            root.assert_no_other_keys()
        except WalkerError as err:
            raise ConfigError(str(err))

    @classmethod
    def from_csv_ballots(cls, filename: str) -> 'ElectionData':
        with open(filename) as f:
            csr = csv.reader(f)
            header = next(csr)
            assert len(header) > 3
            assert header[0] == 'receipt'
            assert header[1] == 'nonce'
            ed = ElectionData(filename)
            ed.title = filename
            ed.options = header[2:]
            ed.num_options = len(ed.options)

            ed.ballots = []
            for row in csr:
                assert len(row) == len(header)
                ed.ballots.append(db.Ballot(
                    electio_id=0,
                    receipt=row[0],
                    nonce=row[1],
                    ranks=[int(r) for r in row[2:]],
                ))

            return ed

    def ballots_from_db(self, election: db.Election) -> None:
        sess = db.get_session()
        # FIXME: Replace with iterating a relationship
        self.ballots = list(sess.scalars(select(db.Ballot).filter_by(election=election)))

    def results(self) -> 'Results':
        return Results(self.num_options, [b.ranks for b in self.ballots])
