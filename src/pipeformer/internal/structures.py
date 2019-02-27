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
"""Internal data structures."""
from collections import OrderedDict
from typing import Dict

import attr
import oyaml as yaml
from attr.validators import instance_of, optional
from troposphere import Ref, Sub, Template, cloudformation, secretsmanager, ssm

from .util import reference_name, resource_name
from .validators import deep_iterable, deep_mapping

__all__ = ("Config", "PipelineStage", "PipelineAction", "Input", "ProjectTemplates", "WaitConditionStack", "Pipeline")
_STRING_STRING_MAP = deep_mapping(key_validator=instance_of(str), value_validator=instance_of(str))


def _resolve_parameter(name: Ref, version: str) -> Sub:
    """"""
    return Sub(f"{{{{resolve:ssm:${{name}}:{version}}}}}", {"name": name})


def _resolve_secret(arn: Ref) -> Sub:
    """"""
    return Sub(f"{{{{resolve:secretsmanager:${{arn}}:SecretString}}}}", {"arn": arn})


@attr.s
class WaitConditionStack:
    """"""

    condition = attr.ib(validator=instance_of(cloudformation.WaitCondition))
    handle = attr.ib(validator=instance_of(cloudformation.WaitConditionHandle))
    stack = attr.ib(validator=instance_of(cloudformation.Stack))


class _ConfigStructure:
    """"""

    @staticmethod
    def _clean_kwargs(kwargs):
        """"""
        return {key.replace("-", "_"): value for key, value in kwargs.items()}

    @classmethod
    def from_dict(cls, kwargs):
        """"""
        return cls(**cls._clean_kwargs(kwargs))


@attr.s
class Input(_ConfigStructure):
    """"""

    name = attr.ib(validator=instance_of(str))
    description = attr.ib(validator=instance_of(str))
    secret = attr.ib(validator=instance_of(bool))
    value = attr.ib(default=None, validator=optional(instance_of(str)))
    version = None

    def __attrs_post_init__(self):
        """"""
        if self.secret:
            self._resource_type = secretsmanager.Secret
            self._value_type = "Arn"
        else:
            self._resource_type = ssm.Parameter
            self._value_type = "Name"
            self.version = 1

    def resource_name(self) -> str:
        """"""
        return resource_name(self._resource_type, self.name)

    def reference_name(self) -> str:
        """"""
        return reference_name(self.resource_name(), self._value_type)

    def dynamic_reference(self) -> Sub:
        """"""
        if self.secret:
            return _resolve_secret(Ref(self.reference_name()))

        return _resolve_parameter(Ref(self.reference_name()), self.version)


@attr.s
class PipelineAction(_ConfigStructure):
    """"""

    provider = attr.ib(validator=instance_of(str))
    inputs = attr.ib(default=attr.Factory(set), validator=optional(deep_iterable(member_validator=instance_of(str))))
    outputs = attr.ib(default=attr.Factory(set), validator=optional(deep_iterable(member_validator=instance_of(str))))
    configuration = attr.ib(default=attr.Factory(dict), validator=optional(_STRING_STRING_MAP))
    image = attr.ib(default=None, validator=optional(instance_of(str)))
    environment_type = attr.ib(default=None, validator=optional(instance_of(str)))
    buildspec = attr.ib(default=None, validator=optional(instance_of(str)))
    compute_type = attr.ib(default="BUILD_GENERAL1_SMALL", validator=optional(instance_of(str)))
    env = attr.ib(default=attr.Factory(dict), validator=optional(_STRING_STRING_MAP))
    run_order = attr.ib(default=1, validator=optional(instance_of(int)))

    def __attrs_post_init__(self):
        if self.run_order < 1:
            raise ValueError("PipelineAction run_order value must be >= 1")

        if self.provider == "CodeBuild":
            if None in (self.image, self.buildspec):
                raise ValueError('image and buildspec must both be defined for actions of type "CodeBuild"')
            if self.environment_type is None:
                if "windows" in self.image.lower():
                    self.environment_type = "WINDOWS_CONTAINER"
                else:
                    self.environment_type = "LINUX_CONTAINER"


@attr.s
class PipelineStage(_ConfigStructure):
    """"""

    name = attr.ib(validator=instance_of(str))
    actions = attr.ib(validator=deep_iterable(member_validator=instance_of(PipelineAction)))


@attr.s
class Config(_ConfigStructure):
    """"""

    name = attr.ib(validator=instance_of(str))
    description = attr.ib(validator=instance_of(str))
    custom_cmk = attr.ib(validator=instance_of(bool))
    pipeline = attr.ib(
        validator=deep_mapping(key_validator=instance_of(str), value_validator=instance_of(PipelineStage))
    )
    inputs = attr.ib(
        validator=optional(deep_mapping(key_validator=instance_of(str), value_validator=instance_of(Input)))
    )

    def __attrs_post_init__(self):
        """"""
        if not self.custom_cmk:
            raise ValueError(
                "Use of AWS-managed CMKs is not supported. Must use customer-managed CMK (custom-cmk: true)."
            )

    @classmethod
    def from_dict(cls, kwargs: Dict):
        """"""
        loaded = kwargs.copy()

        if "inputs" in loaded:
            loaded["inputs"] = {
                key: Input.from_dict(dict(name=key, **value)) for key, value in kwargs["inputs"].items()
            }

        loaded["pipeline"] = {
            key: PipelineStage(name=key, actions=[PipelineAction.from_dict(value) for value in actions])
            for key, actions in kwargs["pipeline"].items()
        }

        return cls(**cls._clean_kwargs(loaded))

    @classmethod
    def from_file(cls, filename: str):
        with open(filename, "rb") as f:
            raw_parsed = yaml.safe_load(f)

        return cls.from_dict(raw_parsed)


@attr.s
class Pipeline:
    """"""

    template = attr.ib(validator=instance_of(Template))
    stage_templates = attr.ib(
        validator=deep_mapping(
            key_validator=instance_of(str),
            value_validator=instance_of(Template),
            mapping_validator=instance_of(OrderedDict),
        )
    )


@attr.s
class ProjectTemplates:
    """"""

    core = attr.ib(validator=instance_of(Template))
    inputs = attr.ib(validator=instance_of(Template))
    iam = attr.ib(validator=instance_of(Template))
    pipeline = attr.ib(validator=instance_of(Template))
    codebuild = attr.ib(
        validator=deep_mapping(
            key_validator=instance_of(str),
            value_validator=instance_of(Template),
            mapping_validator=instance_of(OrderedDict),
        )
    )
