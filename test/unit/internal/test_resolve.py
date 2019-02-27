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
"""Unit tests for ``pipeformer.internal.resolve``."""
import itertools
import json
import uuid
from collections import namedtuple
from typing import Union

import pytest
from troposphere import Join, Ref, Sub

from pipeformer.internal.resolve import _PRIMITIVE_TYPES, InputResolver
from pipeformer.internal.structures import Input

pytestmark = [pytest.mark.local]

Example = namedtuple("Example", ("value",))
INPUTS = {
    "ExampleOne": Input(name="ExampleOne", description="Example number one", secret=False),
    "ExampleTwo": Input(name="ExampleTwo", description="Example number two", secret=True),
}


def resolved_strings():
    for prefix, suffix in itertools.product(("", "prefix"), ("", "suffix")):
        yield (
            f"{prefix}{{INPUT:ExampleOne}}{suffix}",
            Join("", [prefix, Sub("{{resolve:ssm:${name}:1}}", {"name": Ref("Parameter0ExampleOne0Name")}), suffix]),
        )
        yield (
            f"{prefix}{{INPUT:ExampleTwo}}{suffix}",
            Join(
                "",
                [
                    prefix,
                    Sub("{{resolve:secretsmanager:${arn}:SecretString}}", {"arn": Ref("Secret0ExampleTwo0Arn")}),
                    suffix,
                ],
            ),
        )
    yield ("NoInput", "NoInput")
    yield ("{INPUT:Broken", "{INPUT:Broken")
    yield ("PUT:Broken}", "PUT:Broken}")


def resolved_dicts():
    source_map = {}
    resolved_map = {}

    for source, resolved in resolved_strings():
        key = str(uuid.uuid4())
        source_map[key] = source
        resolved_map[key] = resolved

    return source_map, resolved_map


def _normalize_joins(source):
    try:
        return json.dumps(source.to_dict(), sort_keys=True)
    except AttributeError:
        return source


SOURCE_DICT, RESOLVED_DICT = resolved_dicts()
RESOLVED_VALUES = [_normalize_joins(value) for value in RESOLVED_DICT.values()]
SOURCE_INVERSE = {value: key for key, value in SOURCE_DICT.items()}
RESOLVED_INVERSE = {value: key for key, value in RESOLVED_DICT.items()}


def _invert_dict(source):
    return {_normalize_joins(value): key for key, value in source.items()}


def _assert_resolved(actual, expected):
    assert _normalize_joins(actual) == _normalize_joins(expected)


def _assert_converted(value):
    assert isinstance(value, (str, Join, InputResolver) + _PRIMITIVE_TYPES)


class TestInputResolver:
    def test_recurse(self):
        test = InputResolver("asdf", INPUTS)

        with pytest.raises(TypeError) as excinfo:
            InputResolver(test, INPUTS)

        excinfo.match(f"{InputResolver!r} cannot wrap itself.")

    @pytest.mark.parametrize("source, expected", resolved_strings())
    def test_attribute_string(self, source: str, expected: Union[str, Join]):
        wrapped = Example(value=source)
        resolver = InputResolver(wrapped, INPUTS)

        test = resolver.value

        _assert_resolved(test, expected)

    @pytest.mark.parametrize("source, _expected", resolved_strings())
    def test_required_inputs_resolution(self, source, _expected):
        wrapped = Example(value=source)
        resolver = InputResolver(wrapped, INPUTS)

        test = resolver.value

        if source != test:
            assert resolver.required_inputs
        else:
            assert not resolver.required_inputs

    def test_expand_and_resolve_dict(self):
        source = {"a": "{INPUT:ExampleTwo}"}
        expected = {
            "a": Join(
                "",
                ["", Sub("{{resolve:secretsmanager:${arn}:SecretString}}", {"arn": Ref("Secret0ExampleTwo0Arn")}), ""],
            )
        }
        resolver = InputResolver(source, INPUTS)

        test = dict(**resolver)
        assert not isinstance(test, InputResolver)
        assert test["a"].to_dict() == expected["a"].to_dict()

    def test_transitive_required_inputs(self):
        Test = namedtuple("Test", ("value_1", "value_2"))
        values = Test(value_1="{INPUT:ExampleOne}", value_2={"a": "{INPUT:ExampleTwo}"})

        resolver = InputResolver(wrapped=values, inputs=INPUTS)

        _resolve_example_one = resolver.value_1

        assert resolver.required_inputs == {"ExampleOne"}

        extract_dictionary = resolver.value_2

        assert isinstance(extract_dictionary, InputResolver)

        _resolve_values = dict(**extract_dictionary)

        assert resolver.required_inputs == {"ExampleOne", "ExampleTwo"}

    def test_str(self):
        resolver = InputResolver("test", INPUTS)

        assert str(resolver) == "test"

    @pytest.mark.parametrize("value", (42, 42.0, complex(42), False, True, None))
    def test_attribute_primitive_types(self, value):
        source = Example(value=value)
        resolver = InputResolver(source, INPUTS)

        test = resolver.value

        assert not isinstance(test, InputResolver)
        assert type(test) is type(value)
        assert test == value

    def test_attribute_other(self):
        source = Example(value=42)
        resolver = InputResolver(source, INPUTS)

        test = resolver.value

        _assert_converted(test)
        assert test == 42

    def test_equality(self):
        a = InputResolver(42, INPUTS)
        b = InputResolver(76, INPUTS)
        c = InputResolver(42, INPUTS)

        assert a < b
        assert b > c
        assert a == c
        assert a != b
        assert b >= c
        assert a >= c
        assert a <= b
        assert a <= c

        assert a == 42
        assert a != 99
        assert a > 8
        assert a >= 42
        assert a >= 8
        assert a < 99
        assert a <= 42

    def test_item(self):
        source = {"a": 42}
        resolver = InputResolver(source, INPUTS)

        test = resolver["a"]

        _assert_converted(test)
        assert test == 42

    def test_len(self):
        source = "asdf"
        resolver = InputResolver(source, INPUTS)

        assert len(resolver) == len(source)

    @pytest.mark.parametrize("source, expected", resolved_strings())
    def test_call(self, source, expected):
        def example():
            return source

        resolver = InputResolver(example, INPUTS)

        _assert_resolved(resolver(), expected)

    @pytest.mark.parametrize("pos", list(range(4)))
    def test_iter(self, pos: int):
        source = [1, 2, 3, 4]
        resolver = InputResolver(source, INPUTS)

        test = [i for i in resolver]

        _assert_converted(test[pos])
        assert test[pos] == source[pos]

    def test_next(self):
        source = iter([1, 2, 3, 4])
        resolver = InputResolver(source, INPUTS)

        a = next(resolver)
        _assert_converted(a)

    @pytest.mark.parametrize("pos", list(range(4)))
    def test_reversed(self, pos: int):
        source = [1, 2, 3, 4]
        rev_source = list(reversed(source))
        resolver = InputResolver(source, INPUTS)

        test = [i for i in reversed(resolver)]

        _assert_converted(test[pos])
        assert test[pos] == rev_source[pos]

    def test_invalid_inputs_value(self):
        with pytest.raises(TypeError) as _excinfo:
            InputResolver("test", {"a": "b"})

    def test_invalid_wrapped_has_required_inputs(self):
        Invalid = namedtuple("Invalid", ("required_inputs",))

        test = Invalid(required_inputs="asdf")

        with pytest.raises(TypeError) as excinfo:
            InputResolver(test, inputs=INPUTS)

        excinfo.match(r'Wrapped object must not have "required_inputs" attribute.')

    @pytest.mark.parametrize("key", SOURCE_DICT.keys())
    def test_get(self, key):
        resolver = InputResolver(SOURCE_DICT, INPUTS)

        test = resolver.get(key)

        _assert_resolved(test, RESOLVED_DICT[key])

    def test_resolve_values(self):
        resolver = InputResolver(SOURCE_DICT, INPUTS)

        for each in resolver.values():
            _assert_converted(each)
            assert _normalize_joins(each) in RESOLVED_VALUES

    def test_resolve_keys(self):
        resolver = InputResolver(SOURCE_INVERSE, INPUTS)

        for each in resolver.keys():
            _assert_converted(each)
            assert _normalize_joins(each) in RESOLVED_VALUES

    @pytest.mark.parametrize("source", (SOURCE_DICT, SOURCE_INVERSE))
    def test_resolve_items(self, source):
        resolver = InputResolver(source, INPUTS)

        for key, value in resolver.items():
            _assert_converted(key)
            assert _normalize_joins(key) in list(RESOLVED_DICT.keys()) + RESOLVED_VALUES

            _assert_converted(value)
            assert _normalize_joins(value) in list(RESOLVED_DICT.keys()) + RESOLVED_VALUES
