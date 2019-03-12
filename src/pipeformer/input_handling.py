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
"""Tooling for reading and writing inputs."""
import getpass
import logging
import os
from typing import Callable, Dict, Optional

import attr
import boto3
import boto3.session
import botocore.session
from attr.validators import instance_of

from pipeformer.identifiers import LOGGER_NAME
from pipeformer.internal.structures import Input
from pipeformer.internal.util import CloudFormationPhysicalResourceCache
from pipeformer.internal.validators import is_callable

_LOGGER = logging.getLogger(LOGGER_NAME)


class InputHandler:
    """Parent class for all classes used for collecting user input."""

    def collect_secret(self, secret: Input):
        """Collect a secret input value from the user.

        :param Input secret: Input to collect from user
        """
        raise NotImplementedError()

    def save_secret(self, secret: Input):
        """Save a secret input value.

        :param Input secret: Input to save
        """
        raise NotImplementedError()

    def collect_parameter(self, parameter: Input):
        """Collect a non-secret input value from the user.

        :param Input parameter: Input to collect from user
        """
        raise NotImplementedError()

    def save_parameter(self, parameter: Input):
        """Save a non-secret input value.

        :param Input parameter: Input to save
        """
        raise NotImplementedError()

    def collect_inputs(self, inputs: Dict[str, Input]):
        """Collect all input values.

        :param inputs: Mapping of input names to inputs
        """
        for each in inputs.values():
            if each.secret:
                self.collect_secret(each)
            else:
                self.collect_parameter(each)

    def save_inputs(self, inputs: Dict[str, Input]):
        """Save all input values.

        :param inputs: Mapping of input names to inputs
        """
        for each in inputs.values():
            if each.secret:
                self.save_secret(each)
            else:
                self.save_parameter(each)


@attr.s
class DefaultInputHandler(InputHandler):
    """The default input handler.

    Inputs are collected from the command line.
    Secrets are saved to Secrets Manager.
    Parameters are saved to Parameter Store.

    :param callable stack_namer: Callable that returns the stack name
    :param botocore.session.Session botocore_session: Pre-configured botocore session (optional)
    """

    _stack_namer: Callable[[], str] = attr.ib(validator=is_callable())
    _botocore_session: botocore.session.Session = attr.ib(
        default=attr.Factory(botocore.session.Session), validator=instance_of(botocore.session.Session)
    )
    _cache: Optional[CloudFormationPhysicalResourceCache] = None

    def __attrs_post_init__(self):
        """Initialize all AWS SDK clients."""
        boto3_session = boto3.session.Session(botocore_session=self._botocore_session)
        self._secrets_manager = boto3_session.client("secretsmanager")
        self._parameter_store = boto3_session.client("ssm")
        self._cloudformation = boto3_session.client("cloudformation")

    @property
    def cache(self):
        """Lazily create the physical resource cache and return it for use.
        This is necessary because the resources do not exist yet when we create this handler
        (needed for collecting inputs)
        but will exist by the time we need to save those inputs.

        :returns: Cache resource
        """
        if self._cache is not None:
            return self._cache

        self._cache = CloudFormationPhysicalResourceCache(client=self._cloudformation, stack_name=self._stack_namer())
        return self._cache

    @staticmethod
    def _input_prompt(value: Input) -> str:
        """Generate the input prompt message for an input.

        :param Input value: Input for which to create input prompt
        :returns: Formatted input prompt message
        :rtype: str
        """
        return os.linesep.join((value.description, f"{value.name}: ")).lstrip()

    def collect_secret(self, secret: Input):
        """Collect a secret input value from the user via the CLI.

        :param Input secret: Input to collect from user
        """
        secret.value = getpass.getpass(prompt=self._input_prompt(secret))

    @staticmethod
    def _assert_input_set(value: Input):
        """Verify that an input has a value set.

        :param Input value: Input to verify
        :raises ValueError: if value is not set
        """
        if value.value is None:
            raise ValueError(f'Value for input "{value.name}" is not set.')

    def save_secret(self, secret: Input):
        """Save a secret input value to Secrets Manager.

        :param Input secret: Input to save
        """
        _LOGGER.debug(f'Saving secret value for input "{secret.name}"')
        self._assert_input_set(secret)
        secret_id = self.cache.physical_resource_name(secret.resource_name())
        self._secrets_manager.update_secret(SecretId=secret_id, SecretString=secret.value)

    def collect_parameter(self, parameter: Input):
        """Collect a non-secret input value from the user via the CLI.

        :param Input parameter: Input to collect from user
        """
        parameter.value = input(self._input_prompt(parameter))

    def save_parameter(self, parameter: Input):
        """Save a non-secret input value to Parameter Store.

        :param Input parameter: Input to save
        """
        _LOGGER.debug(f'Saving parameter value for input "{parameter.name}"')
        self._assert_input_set(parameter)
        parameter_name = self.cache.physical_resource_name(parameter.resource_name())
        parameter.version = self._parameter_store.put_parameter(
            Name=parameter_name, Type="String", Value=parameter.value, Overwrite=True
        )
