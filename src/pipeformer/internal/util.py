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
"""Additional utilities."""
import logging
import time
from typing import Dict

import attr
import awacs.iam
import awacs.s3
from attr.validators import instance_of
from botocore.exceptions import ClientError
from troposphere import AWS_ACCOUNT_ID, AWS_PARTITION, AWS_REGION, AWSObject, Sub

from pipeformer.identifiers import LOGGER_NAME
from pipeformer.internal.validators import deep_mapping

VALUE_SEPARATOR: str = "0"
MAX_RESOURCE_ATTEMPTS: int = 20
WAIT_PER_ATTEMPT: int = 5
_LOGGER = logging.getLogger(LOGGER_NAME)


def resource_name(resource_type: AWSObject, name: str) -> str:
    """Build the resource logical name for use in stacks.

    :param AWSObject resource_type: Resource type
    :param str name: Naive logical name
    :return: Specific logical name
    """
    type_name = resource_type.resource_type.split("::")[-1]
    return VALUE_SEPARATOR.join((type_name, name))


def reference_name(name: str, value_type: str) -> str:
    """Build the reference name for a resource. Used in stack outputs and parameters.

    :param str name: Resource name
    :param str value_type: Value type
    :return: Specific reference name
    """
    return VALUE_SEPARATOR.join((name, value_type))


def account_arn(service_prefix: str, resource: str) -> Sub:
    """Build an IAM policy Arn pattern scoping down as for as possible for the specified service.

    :param str service_prefix: Service prefix string
    :param str resource: Any resource data to finish Arn
    :return: Constructed Sub structure that will resolve to the scoped down Arn
    """
    if service_prefix in (awacs.iam.prefix, awacs.s3.prefix):
        _region = ""
    else:
        _region = f"${{{AWS_REGION}}}"

    if service_prefix == awacs.s3.prefix:
        _account_id = ""
    else:
        _account_id = f"${{{AWS_ACCOUNT_ID}}}"

    return Sub(f"arn:${{{AWS_PARTITION}}}:{service_prefix}:{_region}:{_account_id}:{resource}")


@attr.s
class CloudFormationPhysicalResourceCache:
    """Cache for persistent information about CloudFormation stack resources."""

    _client = attr.ib()
    _stack_name: str = attr.ib(validator=instance_of(str))
    _cache: Dict[str, Dict] = attr.ib(
        default=attr.Factory(dict),
        validator=deep_mapping(key_validator=instance_of(str), value_validator=instance_of(str)),
    )

    def _describe_resource(self, logical_resource_name: str) -> Dict:
        """"""
        return self._client.describe_stack_resource(StackName=self._stack_name, LogicalResourceId=logical_resource_name)

    def wait_until_resource_is_complete(self, logical_resource_name: str):
        """"""
        response = self.wait_until_resource_exists_in_stack(logical_resource_name)
        if not response["StackResourceDetail"].get("ResourceStatus", ""):
            response = self._wait_until_field_exists(logical_resource_name, "ResourceStatus")
        while True:
            status = response["StackResourceDetail"]["ResourceStatus"]
            _LOGGER.debug("Status of resource %s in stack %s is %s", logical_resource_name, self._stack_name, status)

            if status in ("CREATE_COMPLETE", "UPDATE_COMPLETE"):
                break
            elif status in ("CREATE_IN_PROGRESS", "UPDATE_IN_PROGRESS"):
                time.sleep(5)
                response = self._describe_resource(logical_resource_name)
            else:
                raise Exception(f'Resource creation failed. Resource "{logical_resource_name}" status: "{status}"')

    def wait_until_resource_exists_in_stack(self, logical_resource_name: str) -> Dict:
        """"""
        resource_attempts = 1
        while True:
            _LOGGER.debug(
                "Waiting for creation of resource %s in stack %s to start. Attempt %d of %d",
                logical_resource_name,
                self._stack_name,
                resource_attempts,
                MAX_RESOURCE_ATTEMPTS,
            )
            try:
                return self._describe_resource(logical_resource_name)
            except ClientError as error:
                _LOGGER.debug('Encountered botocore ClientError: "%s"', error.response["Error"]["Message"])
                if (
                    error.response["Error"]["Message"]
                    == f"Resource {logical_resource_name} does not exist for stack {self._stack_name}"
                ):
                    resource_attempts += 1

                    if resource_attempts > MAX_RESOURCE_ATTEMPTS:
                        raise
                else:
                    raise

            time.sleep(WAIT_PER_ATTEMPT)

    def _wait_until_field_exists(self, logical_resource_name: str, field_name: str) -> Dict:
        """Keep trying to describe a resource until it has the requested field.

        Wait 5 seconds between attempts.
        """
        resource_attempts = 1
        response = self.wait_until_resource_exists_in_stack(logical_resource_name)
        while not response.get("StackResourceDetail", {}).get(field_name, ""):
            time.sleep(WAIT_PER_ATTEMPT)

            _LOGGER.debug(
                "Waiting for resource %s in stack %s to have a value for field %s. Attempt %d of %d",
                logical_resource_name,
                self._stack_name,
                field_name,
                resource_attempts,
                MAX_RESOURCE_ATTEMPTS,
            )
            response = self._describe_resource(logical_resource_name)

        return response

    def physical_resource_name(self, logical_resource_name: str) -> str:
        """Find the physical resource name given its logical resource name."""
        try:
            response = self._cache[logical_resource_name]
        except KeyError:
            response = self._wait_until_field_exists(
                logical_resource_name=logical_resource_name, field_name="PhysicalResourceId"
            )
            self._cache[logical_resource_name] = response

        return response["StackResourceDetail"]["PhysicalResourceId"]
