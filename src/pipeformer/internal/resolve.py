# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Helpers for resolving custom formatting."""
from typing import Iterable

import attr
from attr.validators import deep_mapping, instance_of
from troposphere import Join

from .structures import Input

_INPUT_TAG = ["{INPUT:", "}"]
_PRIMITIVE_TYPES = (int, float, complex, bool, type(None))
__all__ = ("InputResolver",)


def _tag_in_string(source: str, start: str, end: str) -> bool:
    """"""
    if start not in source:
        return False

    if end not in source[source.index(start) + len(start) :]:
        return False

    return True


def _value_to_triplet(source: str, start: str, end: str) -> Iterable[str]:
    """"""
    prefix, _value = source.split(start, 1)

    value, suffix = _value.split(end, 1)

    return prefix, value, suffix


@attr.s(cmp=False)
class InputResolver:
    _wrapped = attr.ib()
    _inputs = attr.ib(validator=deep_mapping(key_validator=instance_of(str), value_validator=instance_of(Input)))
    required_inputs = attr.ib(default=attr.Factory(set))

    def __attrs_post_init__(self):
        if isinstance(self._wrapped, InputResolver):
            raise TypeError(f"{InputResolver!r} cannot wrap itself.")

        for reserved in ("required_inputs",):
            if hasattr(self._wrapped, reserved):
                raise TypeError(f'Wrapped object must not have "{reserved}" attribute.')

        for method in ("get", "keys", "values", "items"):
            if hasattr(self._wrapped, method):
                setattr(self, method, getattr(self, f"_{method}"))

    def __expand_values(self, value):
        """"""
        prefix, name, suffix = _value_to_triplet(value, *_INPUT_TAG)

        input_definition = self._inputs[name]
        reference = input_definition.dynamic_reference()

        self.required_inputs.add(name)
        return prefix, reference, suffix

    def __convert_value(self, value):
        """"""
        if isinstance(value, _PRIMITIVE_TYPES):
            return value

        if not isinstance(value, str):
            return InputResolver(wrapped=value, inputs=self._inputs, required_inputs=self.required_inputs)

        if not _tag_in_string(value, *_INPUT_TAG):
            return value

        return Join("", self.__expand_values(value))

    def __len__(self):
        return len(self._wrapped)

    def __eq__(self, other) -> bool:
        if isinstance(other, InputResolver):
            return self._wrapped.__eq__(other._wrapped)
        return self._wrapped.__eq__(other)

    def __lt__(self, other) -> bool:
        if isinstance(other, InputResolver):
            return self._wrapped.__lt__(other._wrapped)
        return self._wrapped.__lt__(other)

    def __gt__(self, other) -> bool:
        if isinstance(other, InputResolver):
            return self._wrapped.__gt__(other._wrapped)
        return self._wrapped.__gt__(other)

    def __le__(self, other) -> bool:
        if isinstance(other, InputResolver):
            return self._wrapped.__le__(other._wrapped)
        return self._wrapped.__le__(other)

    def __ge__(self, other) -> bool:
        if isinstance(other, InputResolver):
            return self._wrapped.__ge__(other._wrapped)
        return self._wrapped.__ge__(other)

    def __str__(self) -> str:
        """"""
        return self._wrapped.__str__()

    def __getattr__(self, name):
        return self.__convert_value(getattr(self._wrapped, name))

    def __call__(self, *args, **kwargs):
        return self.__convert_value(self._wrapped(*args, **kwargs))

    def __getitem__(self, key):
        """"""
        return self.__convert_value(self._wrapped[key])

    def __iter__(self) -> Iterable["InputResolver"]:
        """"""
        for each in self._wrapped:
            yield self.__convert_value(each)

    def __reversed__(self) -> Iterable["InputResolver"]:
        """"""
        return self.__convert_value(reversed(self._wrapped))

    def __next__(self) -> "InputResolver":
        """"""
        return self.__convert_value(self._wrapped.__next__())

    def _get(self, key, default=None) -> "InputResolver":
        """"""
        return self.__convert_value(self._wrapped.get(key, default))

    def _items(self) -> Iterable[Iterable["InputResolver"]]:
        """"""
        for key, value in self._wrapped.items():
            yield (self.__convert_value(key), self.__convert_value(value))

    def _keys(self) -> Iterable["InputResolver"]:
        """"""
        for key in self._wrapped.keys():
            yield self.__convert_value(key)

    def _values(self) -> Iterable["InputResolver"]:
        """"""
        for value in self._wrapped.values():
            yield self.__convert_value(value)
