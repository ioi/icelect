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
    options: list[str]
    num_options: int
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
            options = root['options']
            self.options = [val.as_str() for val in options.array_values()]
            self.num_options = len(self.options)
            if self.num_options < 2:
                options.raise_error("There must be at least 2 options")
            root.assert_no_other_keys()
        except WalkerError as err:
            raise ConfigError(str(err))
