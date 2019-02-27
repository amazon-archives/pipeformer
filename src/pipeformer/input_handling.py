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
from typing import Dict, Callable, Optional

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
    """"""

    def collect_secret(self, secret: Input):
        """"""
        raise NotImplementedError()

    def save_secret(self, secret: Input):
        """"""
        raise NotImplementedError()

    def collect_parameter(self, secret: Input):
        """"""
        raise NotImplementedError()

    def save_parameter(self, secret: Input):
        """"""
        raise NotImplementedError()

    def collect_inputs(self, inputs: Dict[str, Input]):
        """"""
        for each in inputs.values():
            if each.secret:
                self.collect_secret(each)
            else:
                self.collect_parameter(each)

    def save_inputs(self, inputs: Dict[str, Input]):
        """"""
        for each in inputs.values():
            if each.secret:
                self.save_secret(each)
            else:
                self.save_parameter(each)


@attr.s
class DefaultInputHandler(InputHandler):
    """"""

    _stack_namer: Callable[[], str] = attr.ib(validator=is_callable())
    _botocore_session: botocore.session.Session = attr.ib(
        default=attr.Factory(botocore.session.Session), validator=instance_of(botocore.session.Session)
    )
    _cache: Optional[CloudFormationPhysicalResourceCache] = None

    def __attrs_post_init__(self):
        boto3_session = boto3.session.Session(botocore_session=self._botocore_session)
        self._secrets_manager = boto3_session.client("secretsmanager")
        self._parameter_store = boto3_session.client("ssm")
        self._cloudformation = boto3_session.client("cloudformation")

    @property
    def cache(self):
        """"""
        if self._cache is not None:
            return self._cache

        self._cache = CloudFormationPhysicalResourceCache(client=self._cloudformation, stack_name=self._stack_namer())
        return self._cache

    @staticmethod
    def _input_prompt(value: Input) -> str:
        """"""
        return os.linesep.join((value.description, f"{value.name}: ")).lstrip()

    def collect_secret(self, secret: Input):
        """"""
        secret.value = getpass.getpass(prompt=self._input_prompt(secret))

    @staticmethod
    def _assert_input_set(value: Input):
        """"""
        if value.value is None:
            raise ValueError(f'Value for input "{value.name}" is not set.')

    def save_secret(self, secret: Input):
        """"""
        _LOGGER.debug(f'Saving secret value for input "{secret.name}"')
        self._assert_input_set(secret)
        secret_id = self.cache.physical_resource_name(secret.resource_name())
        self._secrets_manager.update_secret(SecretId=secret_id, SecretString=secret.value)

    def collect_parameter(self, parameter: Input):
        """"""
        parameter.value = input(self._input_prompt(parameter))

    def save_parameter(self, parameter: Input):
        """"""
        _LOGGER.debug(f'Saving parameter value for input "{parameter.name}"')
        self._assert_input_set(parameter)
        parameter_name = self.cache.physical_resource_name(parameter.resource_name())
        parameter.version = self._parameter_store.put_parameter(
            Name=parameter_name, Type="String", Value=parameter.value, Overwrite=True
        )
