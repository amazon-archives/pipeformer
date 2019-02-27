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
"""Attrs validators pre-cached here pending attrs 19.0.0 release."""
from attr import attrib, attrs
from attr.validators import optional


@attrs(repr=False, slots=False, hash=True)
class _IsCallableValidator(object):
    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if not callable(value):
            raise TypeError("'{name}' must be callable".format(name=attr.name))

    def __repr__(self):
        return "<is_callable validator>"


def is_callable():
    """
    A validator that raises a :class:`TypeError` if the initializer is called
    with a value for this particular attribute that is not callable.

    :raises TypeError: With a human readable error message containing the
        attribute (of type :class:`attr.Attribute`) name.
    """
    return _IsCallableValidator()


@attrs(repr=False, slots=True, hash=True)
class _DeepIterable(object):
    member_validator = attrib(validator=is_callable())
    iterable_validator = attrib(default=None, validator=optional(is_callable()))

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if self.iterable_validator is not None:
            self.iterable_validator(inst, attr, value)

        for member in value:
            self.member_validator(inst, attr, member)

    def __repr__(self):
        iterable_identifier = (
            "" if self.iterable_validator is None else " {iterable!r}".format(iterable=self.iterable_validator)
        )
        return ("<deep_iterable validator for{iterable_identifier}" " iterables of {member!r}>").format(
            iterable_identifier=iterable_identifier, member=self.member_validator
        )


def deep_iterable(member_validator, iterable_validator=None):
    """
    A validator that performs deep validation of an iterable.
    :param member_validator: Validator to apply to iterable members
    :param iterable_validator: Validator to apply to iterable itself
        (optional)

    :raises TypeError: if any sub-validators fail
    """
    return _DeepIterable(member_validator, iterable_validator)


@attrs(repr=False, slots=True, hash=True)
class _DeepMapping(object):
    key_validator = attrib(validator=is_callable())
    value_validator = attrib(validator=is_callable())
    mapping_validator = attrib(default=None, validator=optional(is_callable()))

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if self.mapping_validator is not None:
            self.mapping_validator(inst, attr, value)

        for key in value:
            self.key_validator(inst, attr, key)
            self.value_validator(inst, attr, value[key])

    def __repr__(self):
        return ("<deep_mapping validator for objects mapping {key!r} to {value!r}>").format(
            key=self.key_validator, value=self.value_validator
        )


def deep_mapping(key_validator, value_validator, mapping_validator=None):
    """
    A validator that performs deep validation of a dictionary.
    :param key_validator: Validator to apply to dictionary keys
    :param value_validator: Validator to apply to dictionary values
    :param mapping_validator: Validator to apply to top-level mapping
        attribute (optional)

    :raises TypeError: if any sub-validators fail
    """
    return _DeepMapping(key_validator, value_validator, mapping_validator)
