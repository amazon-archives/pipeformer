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
"""Logic for building the inputs stack template."""
from troposphere import Output, Parameter, Ref, Tags, Template, kms, secretsmanager, ssm

from pipeformer.internal.structures import Config, Input
from pipeformer.internal.util import reference_name, resource_name

from . import project_tags


def _secret_value(resource: Input, tags: Tags, cmk_arn: Ref) -> secretsmanager.Secret:
    """Construct a Secrets Manager secret to store the input value.

    :param Input resource:
    :param Tags tags:
    :param Ref cmk_arn:
    :return: Constructed resource
    :rtype: secretsmanager.Secret
    """
    return secretsmanager.Secret(
        resource_name(secretsmanager.Secret, resource.name), KmsKeyId=cmk_arn, SecretString="REPLACEME", Tags=tags
    )


def _standard_value(resource: Input) -> ssm.Parameter:
    """Construct a Parameter Store parameter containing the input value.

    :param Input resource: Input to store
    :return: Constructed resource
    :rtype: ssm.Parameter
    """
    return ssm.Parameter(resource_name(ssm.Parameter, resource.name), Type="String", Value=resource.value)


def build(project: Config) -> Template:
    """Build an Inputs stack template from the provided project.

    :param Config project: Source project
    :return: Generated Inputs stack template
    :rtype: Template
    """
    inputs = Template(Description=f"Input values for pipeformer-managed project: {project.name}")
    cmk = inputs.add_parameter(Parameter(reference_name(resource_name(kms.Key, "Stack"), "Arn"), Type="String"))

    default_tags = project_tags(project)

    for value in project.inputs.values():
        if value.secret:
            resource = _secret_value(resource=value, tags=default_tags, cmk_arn=cmk.ref())
            resource_output = "Arn"
        else:
            resource = _standard_value(value)
            resource_output = "Name"
        inputs.add_resource(resource)
        inputs.add_output(Output(reference_name(resource.title, resource_output), Value=Ref(resource)))

    return inputs
