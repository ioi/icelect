# A simple module for walking through a parsed JSON file
# (c) 2023 Martin Mareš <mj@ucw.cz>

from collections.abc import Iterator
from enum import Enum
import re
from typing import Any, Optional, NoReturn, Tuple, Set, Type, TypeVar


T = TypeVar('T')
E = TypeVar('E', bound=Enum)


class MissingValue:
    pass


class Walker:
    obj: Any
    parent: Optional['Walker'] = None
    custom_context: str = ""

    def __init__(self, root: Any) -> None:
        self.obj = root

    def context(self) -> str:
        return 'root'

    def raise_error(self, msg) -> NoReturn:
        raise WalkerError(self, msg)

    def is_null(self) -> bool:
        return self.obj is None

    def is_str(self) -> bool:
        return isinstance(self.obj, str)

    def is_int(self) -> bool:
        return isinstance(self.obj, int)

    def is_missing(self) -> bool:
        return isinstance(self.obj, MissingValue)

    def is_present(self) -> bool:
        return not isinstance(self.obj, MissingValue)

    def is_bool(self) -> bool:
        return isinstance(self.obj, bool)

    def is_array(self) -> bool:
        return isinstance(self.obj, list)

    def is_object(self) -> bool:
        return isinstance(self.obj, dict)

    def expect_present(self):
        if self.is_missing():
            self.raise_error('Mandatory key is missing')

    def as_type(self, typ: Type[T], msg: str, default: Optional[T] = None) -> T:
        if isinstance(self.obj, typ):
            return self.obj
        elif self.is_missing():
            if default is None:
                self.raise_error('Mandatory key is missing')
            else:
                return default
        else:
            self.raise_error(msg)

    def as_optional_type(self, typ: Type[T], msg: str) -> Optional[T]:
        if isinstance(self.obj, typ):
            return self.obj
        elif self.is_missing():
            return None
        else:
            self.raise_error(msg)

    def as_str(self, default: Optional[str] = None) -> str:
        return self.as_type(str, 'Expected a string', default)

    def as_int(self, default: Optional[int] = None) -> int:
        return self.as_type(int, 'Expected an integer', default)

    def as_bool(self, default: Optional[bool] = None) -> bool:
        return self.as_type(bool, 'Expected a Boolean value', default)

    def as_enum(self, enum: Type[E], default: Optional[E] = None) -> E:
        if self.is_missing() and default is not None:
            return default
        try:
            return enum(self.as_str())
        except ValueError:
            self.raise_error('Must be one of ' + '/'.join(sorted(enum.__members__.values())))  # FIXME: type

    def as_optional_str(self) -> Optional[str]:
        return self.as_optional_type(str, 'Expected a string')

    def as_optional_int(self) -> Optional[int]:
        return self.as_optional_type(int, 'Expected an integer')

    def as_optional_bool(self) -> Optional[bool]:
        return self.as_optional_type(bool, 'Expected a Boolean value')

    def array_values(self) -> Iterator['WalkerInArray']:
        ary = self.as_type(list, 'Expected an array')
        for i, obj in enumerate(ary):
            yield WalkerInArray(obj, self, i)

    def object_values(self) -> Iterator['WalkerInObject']:
        dct = self.as_type(dict, 'Expected an object')
        for key, obj in dct.items():
            yield WalkerInObject(obj, self, key)

    def object_items(self) -> Iterator[Tuple[str, 'WalkerInObject']]:
        dct = self.as_type(dict, 'Expected an object')
        for key, obj in dct.items():
            yield key, WalkerInObject(obj, self, key)

    def enter_object(self) -> 'ObjectWalker':
        dct = self.as_type(dict, 'Expected an object')
        return ObjectWalker(dct, self)

    def default_to(self, default) -> 'Walker':    # XXX: Use Self when available
        if self.is_missing():
            self.obj = default
        return self

    def set_custom_context(self, ctx: str) -> None:
        self.custom_context = ctx


class WalkerInArray(Walker):
    index: int

    def __init__(self, obj: Any, parent: Walker, index: int) -> None:
        super().__init__(obj)
        self.parent = parent
        self.index = index

    def context(self) -> str:
        return f'[{self.index}]'


class WalkerInObject(Walker):
    key: str

    def __init__(self, obj: Any, parent: Walker, key: str) -> None:
        super().__init__(obj)
        self.parent = parent
        self.key = key

    def context(self) -> str:
        if re.fullmatch(r'\w+', self.key):
            return f'.{self.key}'
        else:
            quoted_key = re.sub(r'(\\|")', r'\\\1', self.key)
            return f'."{quoted_key}"'

    def unexpected(self) -> NoReturn:
        self.raise_error('Unexpected key')


class ObjectWalker(Walker):
    referenced_keys: Set[str]

    def __init__(self, obj: Any, parent: Walker) -> None:
        super().__init__(obj)
        assert isinstance(obj, dict)
        self.parent = parent
        self.referenced_keys = set()

    def __enter__(self) -> 'ObjectWalker':
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is None:
            self.assert_no_other_keys()

    def context(self) -> str:
        return ""

    def __contains__(self, key: str) -> bool:
        return key in self.obj

    def __getitem__(self, key: str) -> WalkerInObject:
        if key in self.obj:
            self.referenced_keys.add(key)
            return WalkerInObject(self.obj[key], self, key)
        else:
            return WalkerInObject(MissingValue(), self, key)

    def assert_no_other_keys(self) -> None:
        for key, val in self.obj.items():
            if key not in self.referenced_keys:
                WalkerInObject(val, self, key).unexpected()


class WalkerError(Exception):
    walker: Walker
    msg: str

    def __init__(self, walker: Walker, msg: str) -> None:
        self.walker = walker
        self.msg = msg

    def __str__(self) -> str:
        contexts = []
        w: Optional[Walker] = self.walker
        while w is not None:
            contexts.append(w.context())
            contexts.append(w.custom_context)
            w = w.parent
        return "".join(reversed(contexts)) + ": " + self.msg
