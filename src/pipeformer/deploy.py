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
"""Tooling to deploy a generated set of templates."""
import json
import logging
import uuid
from functools import partial
from typing import Dict, Optional

import attr
import boto3
import boto3.session
import botocore.session
import requests
from attr.validators import instance_of, optional
from botocore.exceptions import ClientError
from troposphere import Template, cloudformation, s3

from pipeformer.identifiers import LOGGER_NAME, VALUE_SEPARATOR
from pipeformer.input_handling import DefaultInputHandler, InputHandler
from pipeformer.internal.structures import Config, ProjectTemplates
from pipeformer.internal.template_builder import config_to_templates
from pipeformer.internal.util import CloudFormationPhysicalResourceCache, resource_name

_LOGGER = logging.getLogger(LOGGER_NAME)
__all__ = ("Deployer",)


@attr.s
class Deployer:
    """Helper client to manage deploying a set of stacks.

    :param project: Project configuration to use
    :param stack_prefix: Stack prefix (optional: if not provided, the project name from the config will be used)
    :param botocore_session: Pre-configured botocore session (optional)
    :param input_handler: Pre-configured input handler to use (optional)
    """

    _project: Config = attr.ib(validator=instance_of(Config))
    _stack_prefix: Optional[str] = attr.ib(default=None, validator=optional(instance_of(str)))
    _botocore_session: botocore.session.Session = attr.ib(
        default=attr.Factory(botocore.session.Session), validator=instance_of(botocore.session.Session)
    )
    _input_handler: InputHandler = attr.ib(default=None, validator=optional(instance_of(InputHandler)))
    _actual_templates: Optional[ProjectTemplates] = None
    _template_urls: Optional[Dict[str, str]] = None
    _inputs_collected: Optional[bool] = None
    _cache: Optional[CloudFormationPhysicalResourceCache] = None

    def __attrs_post_init__(self):
        """Initialize all needed clients and resources."""
        boto3_session = boto3.session.Session(botocore_session=self._botocore_session)
        self._cloudformation = boto3_session.client("cloudformation")
        self._s3 = boto3_session.client("s3")
        self._inputs_collected = False
        self._template_urls = {}

        self._cache = CloudFormationPhysicalResourceCache(
            client=self._cloudformation, stack_name=self._core_stack_name()
        )

        if self._stack_prefix is None:
            self._stack_prefix = self._project.name

        if self._input_handler is None:
            self._input_handler = DefaultInputHandler(
                stack_namer=partial(self._cache.physical_resource_name, self._inputs_stack_logical_name()),
                botocore_session=self._botocore_session,
            )

    def _collect_inputs(self):
        """Collect inputs from user."""
        # TODO: Should we re-prompt for input values that are already known?
        self._input_handler.collect_inputs(self._project.inputs)
        self._inputs_collected = True

    @property
    def _templates(self):
        """Lazily load templates from config.

        This is necessary because the inputs need to be collected before the templates are built.
        """
        if not self._inputs_collected:
            raise Exception("Inputs have not yet been collected.")

        if self._actual_templates is None:
            self._actual_templates = config_to_templates(self._project)

        return self._actual_templates

    @staticmethod
    def _artifacts_bucket_logical_name() -> str:
        """Determine the logical name for the artifacts S3 bucket."""
        return resource_name(s3.Bucket, "Artifacts")

    def _wait_for_artifacts_bucket(self):
        """Wait until the artifacts bucket is created."""
        self._cache.wait_until_resource_is_complete(self._artifacts_bucket_logical_name())

    def _upload_single_template(self, template_type: str, template: Template):
        """Upload one template to the artifacts bucket.

        :param template_type: Template type name
        :param template: Template to upload
        """
        bucket_name = self._cache.physical_resource_name(self._artifacts_bucket_logical_name())
        _LOGGER.debug('Uploading %s template to bucket "%s"', template_type, bucket_name)
        key = f"templates/{uuid.uuid4()}"
        body = template.to_json()
        self._s3.put_object(Bucket=bucket_name, Key=key, Body=body)
        self._template_urls[VALUE_SEPARATOR.join(("Upload", "Template", template_type))] = key

    def _upload_templates(self):
        """Upload all templates to artifacts bucket."""
        self._upload_single_template("Inputs", self._templates.inputs)
        self._upload_single_template("Iam", self._templates.iam)
        self._upload_single_template("Pipeline", self._templates.pipeline)
        for name, stage in self._templates.codebuild.items():
            self._upload_single_template(VALUE_SEPARATOR.join(("CodeBuild", "Stage", name)), stage)

    def _succeed_wait_condition(self, resource_logical_name: str, reason: str, data: str):
        """Report success to a CloudFormation wait condition.

        :param resource_logical_name: Logical name of wait condition resource
        :param reason: Reason for success
        :param data: Data to include in wait condition report
        """
        _LOGGER.debug('Reporting to wait condition "%s" with data "%s"', resource_logical_name, data)
        wait_condition_url = self._cache.physical_resource_name(resource_logical_name)
        message = {"Status": "SUCCESS", "Reason": reason, "UniqueId": "n/a", "Data": data}
        requests.put(url=wait_condition_url, data=json.dumps(message))

    def _report_templates_uploaded(self):
        """Report success for all template upload wait conditions."""
        for name, value in self._template_urls.items():
            self._succeed_wait_condition(name, "Template uploaded", value)

    @staticmethod
    def _inputs_stack_logical_name() -> str:
        """Determine the logical name for the inputs stack."""
        return resource_name(cloudformation.Stack, "Inputs")

    def _wait_for_inputs_stack(self):
        """Wait until the inputs stack is created."""
        self._cache.wait_until_resource_is_complete(VALUE_SEPARATOR.join(("WaitFor", "Upload", "Template", "Inputs")))
        self._cache.wait_until_resource_is_complete(self._inputs_stack_logical_name())

    def _report_input_values_saved(self):
        """Report that the input values have all been saved."""
        self._succeed_wait_condition(VALUE_SEPARATOR.join(("Upload", "Input", "Values")), "Inputs saved", "complete")

    def _stack_exists(self, stack_name: str) -> bool:
        """Determine if the stack has already been deployed.

        :param stack_name: Name of CloudFormation stack for which to check
        """
        try:
            self._cloudformation.describe_stacks(StackName=stack_name)

        except ClientError as error:
            if error.response["Error"]["Message"] == "Stack with id {name} does not exist".format(name=stack_name):
                return False
            raise

        else:
            return True

    def _core_stack_name(self) -> str:
        """Determine the core stack name."""
        return f"{self._stack_prefix}-core"

    def _update_existing_core_stack(self):
        """Update an existing core stack."""
        _LOGGER.info("Updating existing core stack.")

        self._cloudformation.update_stack(
            StackName=self._core_stack_name(), TemplateBody=self._templates.core.to_json()
        )
        # We specifically do not want to wait for this to complete.

    def _deploy_new_core_stack(self):
        """Deploy a new core stack."""
        _LOGGER.info("Bootstrapping new core stack.")
        self._cloudformation.create_stack(
            StackName=self._core_stack_name(),
            TemplateBody=self._templates.core.to_json(),
            Capabilities=["CAPABILITY_IAM"],
        )
        # We specifically do not want to wait for this to complete.

    def _deploy_core_stack(self) -> str:
        """Deploy or update the core stack."""
        if self._stack_exists(self._core_stack_name()):
            self._update_existing_core_stack()
            return "stack_update_complete"
        else:
            self._deploy_new_core_stack()
            return "stack_create_complete"

    def _wait_for_core_stack(self, waiter_name: str):
        """Wait for the core stack creation to complete."""
        waiter = self._cloudformation.get_waiter(waiter_name)
        waiter.wait(StackName=self._core_stack_name(), WaiterConfig=dict(Delay=10))
        _LOGGER.info("Stack deploy/update complete!")

    def deploy_standalone(self):
        """Deploy a standalone PipeFormer application.

        This will create all necessary resources including all IAM Roles and a KMS CMK.
        """
        _LOGGER.info("Collecting user inputs.")
        self._collect_inputs()

        _LOGGER.info("Starting stack deployment.")
        waiter_name = self._deploy_core_stack()

        _LOGGER.info("Waiting for artifacts bucket creation to complete.")
        self._wait_for_artifacts_bucket()

        _LOGGER.info("Uploading nested stack template files.")
        self._upload_templates()

        # TODO: Do wait conditions re-create on stack updates?
        # TODO: If I update a stack with a dynamic reference
        #  and the only thing that changed is the value in the
        #  referenced location, does the stack update?
        _LOGGER.info("Reporting uploaded template file locations to wait conditions.")
        self._report_templates_uploaded()

        _LOGGER.info("Waiting for inputs stack creation to complete.")
        self._wait_for_inputs_stack()

        _LOGGER.info("Saving inputs values to input stack resources.")
        self._input_handler.save_inputs(inputs=self._project.inputs)

        _LOGGER.info("Reporting inputs status to wait condition.")
        self._report_input_values_saved()

        _LOGGER.info("Waiting for stacks to finish deploying")
        self._wait_for_core_stack(waiter_name)
