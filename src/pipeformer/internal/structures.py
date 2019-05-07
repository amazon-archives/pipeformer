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
from typing import Dict, Iterable, Optional, Set

import attr
import oyaml as yaml
from attr.validators import deep_iterable, deep_mapping, instance_of, optional
from troposphere import Ref, Sub, Template, cloudformation, secretsmanager, ssm

from .util import reference_name, resource_name

__all__ = ("Config", "PipelineStage", "PipelineAction", "Input", "ProjectTemplates", "WaitConditionStack", "Pipeline")
_STRING_STRING_MAP = deep_mapping(key_validator=instance_of(str), value_validator=instance_of(str))


def _resolve_parameter(name: Ref, version: str) -> Sub:
    """Build a CloudFormation dynamic reference string structure that resolves a SSM Parameter.

    :param name: Parameter name
    :param version: Parameter version
    :return: Dynamic reference
    """
    return Sub(f"{{{{resolve:ssm:${{name}}:{version}}}}}", {"name": name})


def _resolve_secret(arn: Ref) -> Sub:
    """Build a CloudFormation dynamic reference string structure that resolves a Secrets Manager secret.

    :param arn: Secret Arn
    :return: Dynamic reference
    """
    return Sub(f"{{{{resolve:secretsmanager:${{arn}}:SecretString}}}}", {"arn": arn})


@attr.s
class WaitConditionStack:
    """Container to hold all resources for a wait-condition-initiated stack.

    :param condition: Wait condition
    :param handle: Wait condition handle
    :param stack: Stack
    """

    condition: cloudformation.WaitCondition = attr.ib(validator=instance_of(cloudformation.WaitCondition))
    handle: cloudformation.WaitConditionHandle = attr.ib(validator=instance_of(cloudformation.WaitConditionHandle))
    stack: cloudformation.Stack = attr.ib(validator=instance_of(cloudformation.Stack))


class _ConfigStructure:
    """Base for configuration structures."""
    @staticmethod
    def _clean_kwargs(kwargs: Dict):
        """Convert keys separators from YAML-valid "-" characters to Python-variable-name-valid "_" characters."""
        return {key.replace("-", "_"): value for key, value in kwargs.items()}
    @classmethod
    def from_dict(cls, kwargs: Dict):
        """Load from a dictionary."""
        return cls(**cls._clean_kwargs(kwargs))


@attr.s
class Input(_ConfigStructure):
    """Container and formatter for input values.

    :param name: Input name
    :param description: Input description
    :param secret: Is this input a secret?
    :param value: Input value (optional)
    """
    name: str = attr.ib(validator=instance_of(str))
    description: str = attr.ib(validator=instance_of(str))
    secret: bool = attr.ib(validator=instance_of(bool))
    value: Optional[str] = attr.ib(default=None, validator=optional(instance_of(str)))
    version: Optional[int] = None
    _value_type: str

    def __attrs_post_init__(self):
        """Set additional configuration values based on input type."""
        if self.secret:
            self._resource_type = secretsmanager.Secret
            self._value_type = "Arn"
        else:
            self._resource_type = ssm.Parameter
            self._value_type = "Name"
            self.version = 1

    def resource_name(self) -> str:
        """Build the resource name for this input."""
        return resource_name(self._resource_type, self.name)

    def reference_name(self) -> str:
        """Build the reference name for this input."""
        return reference_name(self.resource_name(), self._value_type)

    def dynamic_reference(self) -> Sub:
        """Build a CloudFormation dynamic reference string structure that resolves this input."""
        if self.secret:
            return _resolve_secret(Ref(self.reference_name()))

        return _resolve_parameter(Ref(self.reference_name()), self.version)


@attr.s
class PipelineAction(_ConfigStructure):
    """CodePipeline action definition.

    :param provider: Action provider name
        (must be a valid CodePipeline action provider name)
    :param inputs: Names of CodePipeline inputs to collect
    :param outputs: Names of CodePipeline outputs to emit
    :param configuration: Additional string-string map of configuration values to provide in
        CodePipeline action definition
    :param image: Docker image to use with CodeBuild
        (only used for CodeBuild provider actions)
    :param environment_type: CodeBuild environment type name
        (only used for CodeBuild provider actions)
        (if not provided, we will attempt to guess based on the image name)
    :param buildspec: Location of CodeBuild buildspec in source
        (only used for CodeBuild provider actions)
        (in-line buildspec definition not supported)
    :param compute_type: CodeBuild compute type name
        (only used for CodeBuild provider actions)
        (default: ``BUILD_GENERAL1_SMALL``)
    :param env: Mapping of environment variables to set in action environment
    :param run_order: CodePipeline action run order
    """

    provider: str = attr.ib(validator=instance_of(str))
    inputs: Set[str] = attr.ib(
        default=attr.Factory(set), validator=optional(deep_iterable(member_validator=instance_of(str)))
    )
    outputs: Set[str] = attr.ib(
        default=attr.Factory(set), validator=optional(deep_iterable(member_validator=instance_of(str)))
    )
    configuration: Dict[str, str] = attr.ib(default=attr.Factory(dict), validator=optional(_STRING_STRING_MAP))
    image: Optional[str] = attr.ib(default=None, validator=optional(instance_of(str)))
    environment_type: Optional[str] = attr.ib(default=None, validator=optional(instance_of(str)))
    buildspec: Optional[str] = attr.ib(default=None, validator=optional(instance_of(str)))
    compute_type: str = attr.ib(default="BUILD_GENERAL1_SMALL", validator=optional(instance_of(str)))
    env: Dict[str, str] = attr.ib(default=attr.Factory(dict), validator=optional(_STRING_STRING_MAP))
    run_order: int = attr.ib(default=1, validator=optional(instance_of(int)))

    @run_order.validator
    def _check_run_order(self, attribute, value):  # pylint: disable=unused-argument,no-self-use
        """Verify that ``run_order`` value is valid."""
        if value < 1:
            raise ValueError("PipelineAction run_order value must be >= 1")

    @image.validator
    def _check_image(self, attribute, value):  # pylint: disable=unused-argument
        """Verify that ``image`` is set if provider type ``CodeBuild`` is used."""
        if self.provider == "CodeBuild" and value is None:
            raise ValueError('image must be defined for actions of type "CodeBuild"')

    @buildspec.validator
    def _check_buildspec(self, attribute, value):  # pylint: disable=unused-argument
        """Verify that ``buildspec`` is set if provider type ``CodeBuild`` is used."""
        if self.provider == "CodeBuild" and value is None:
            raise ValueError('buildspec must be defined for actions of type "CodeBuild"')

    def __attrs_post_init__(self):
        """Set default values for ``environment_type``."""
        if self.provider == "CodeBuild" and self.environment_type is None:
            if "windows" in self.image.lower():
                self.environment_type = "WINDOWS_CONTAINER"
            else:
                self.environment_type = "LINUX_CONTAINER"


@attr.s
class PipelineStage(_ConfigStructure):
    """CodePipeline stage definition.

    :param name: Stage name
    :param actions: Actions to be taken in stage
    """

    name: str = attr.ib(validator=instance_of(str))
    actions: Iterable[PipelineAction] = attr.ib(validator=deep_iterable(member_validator=instance_of(PipelineAction)))


@attr.s
class Config(_ConfigStructure):
    """PipeFormer project configuration.

    :param name: Project name
    :param description: Project description
    :param custom_cmk: Should a custom CMK be generated? (reserved for later use: must always be ``True``)
    :param pipeline: Mapping of stage names to pipeline stages
    :param inputs: Mapping of input names to loaded inputs
    """

    name: str = attr.ib(validator=instance_of(str))
    description: str = attr.ib(validator=instance_of(str))
    custom_cmk: bool = attr.ib(validator=instance_of(bool))
    pipeline: Dict[str, PipelineStage] = attr.ib(
        validator=deep_mapping(key_validator=instance_of(str), value_validator=instance_of(PipelineStage))
    )
    inputs: Dict[str, Input] = attr.ib(
        validator=optional(deep_mapping(key_validator=instance_of(str), value_validator=instance_of(Input)))
    )

    @custom_cmk.validator
    def _check_custom_cmk(self, attribute, value):  # pylint: disable=unused-argument,,no-self-use
        """Validate that the ``custom_cmk`` value is always ``True``."""
        if not value:
            raise ValueError(
                "Use of AWS-managed CMKs is not supported. Must use customer-managed CMK (custom-cmk: true)."
            )

    @classmethod
    def from_dict(cls, kwargs: Dict):
        """Load a PipeFormer config from a dictionary parsed from a PipeFormer config file.

        :param kwargs: Parsed config file dictionary
        :return: Loaded PipeFormer config
        """
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
        """Load a PipeFormer config from an existing file.

        :param filename: Existing filename
        :return: Loaded PipeFormer config
        """
        with open(filename, "rb") as config_file:
            raw_parsed = yaml.safe_load(config_file)

        return cls.from_dict(raw_parsed)


@attr.s
class Pipeline:
    """Container to hold all templates for a single PipeFormer pipeline.

    :param template: CodePipeline stack template
    :param codebuild: Mapping of stage names to corresponding CodeBuild templates
    """

    template: Template = attr.ib(validator=instance_of(Template))
    stage_templates: Dict[str, Template] = attr.ib(
        validator=deep_mapping(
            key_validator=instance_of(str),
            value_validator=instance_of(Template),
            mapping_validator=instance_of(OrderedDict),
        )
    )


@attr.s
class ProjectTemplates:
    """Container to hold all templates for a PipeFormer project.

    :param core: Core stack template
    :param inputs: Inputs stack template
    :param iam: IAM stack template
    :param pipeline: CodePipeline stack template
    :param codebuild: Mapping of stage names to corresponding CodeBuild templates
    """

    core: Template = attr.ib(validator=instance_of(Template))
    inputs: Template = attr.ib(validator=instance_of(Template))
    iam: Template = attr.ib(validator=instance_of(Template))
    pipeline: Template = attr.ib(validator=instance_of(Template))
    codebuild: Dict[str, Template] = attr.ib(
        validator=deep_mapping(
            key_validator=instance_of(str),
            value_validator=instance_of(Template),
            mapping_validator=instance_of(OrderedDict),
        )
    )
