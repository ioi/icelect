# Icelect - Handling election configuration
# (c) 2025 Martin Mareš <mj@ucw.cz>

import tomllib
from typing import Any

from icelect.json_walker import Walker, WalkerError


class ConfigError(ValueError):
    pass


class ElectionConfig:
    ident: str
    title: str
    candidates: list[str]
    tree: Any

    def __init__(self, ident: str, tree: Any):
        self.ident = ident
        self.tree = tree
        self.parse_tree()

    @classmethod
    def from_config_file(cls, ident: str) -> 'ElectionConfig':
        try:
            with open(f'etc/{ident}.toml', 'rb') as file:
                tree = tomllib.load(file)
        except tomllib.TOMLDecodeError as err:
            raise ConfigError(str(err))
        except FileNotFoundError:
            raise ConfigError('File not found')
        return ElectionConfig(ident, tree)

    def parse_tree(self) -> None:
        try:
            root = Walker(self.tree).enter_object()
            self.title = root['title'].as_str()
            candidates = root['candidates']
            self.candidates = [val.as_str() for val in candidates.array_values()]
            if len(self.candidates) < 2:
                candidates.raise_error("There must be at least 2 candidates")
            root.assert_no_other_keys()
        except WalkerError as err:
            raise ConfigError(str(err))
