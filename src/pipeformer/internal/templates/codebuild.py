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
"""Logic for building the CodeBuild stack templates."""
import string

from troposphere import AWS_STACK_NAME, Output, Parameter, Ref, Sub, Tags, Template, codebuild, iam, s3

from pipeformer.internal.resolve import InputResolver
from pipeformer.internal.structures import Config, PipelineAction, PipelineStage
from pipeformer.internal.util import reference_name, resource_name

from . import project_tags


def project_name(action_number: int) -> str:
    return resource_name(codebuild.Project, string.ascii_letters[action_number])


def _build_project(name: str, action: InputResolver, role: Ref, bucket: Ref, tags: Tags) -> codebuild.Project:
    """"""
    return codebuild.Project(
        name,
        Name=Sub(f"${{{AWS_STACK_NAME}}}-{name}"),
        ServiceRole=role,
        Artifacts=codebuild.Artifacts(Type="CODEPIPELINE"),
        Source=codebuild.Source(Type="CODEPIPELINE", BuildSpec=action.buildspec),
        Environment=codebuild.Environment(
            ComputeType=action.compute_type,
            Type=action.environment_type,
            Image=action.image,
            EnvironmentVariables=[codebuild.EnvironmentVariable(Name="PIPEFORMER_S3_BUCKET", Value=bucket)]
            + [codebuild.EnvironmentVariable(Name=key, Value=value) for key, value in action.env.items()],
        ),
        Tags=tags,
    )


def build(project: Config, stage: InputResolver) -> Template:
    """"""
    resources = Template(
        Description=f"CodeBuild projects for {stage.name} stage in pipeformer-managed project: {project.name}"
    )

    # set all non-input parameters
    resources_bucket = resources.add_parameter(
        Parameter(reference_name(resource_name(s3.Bucket, "ProjectResources"), "Name"), Type="String")
    )
    role = resources.add_parameter(
        Parameter(reference_name(resource_name(iam.Role, "CodeBuild"), "Arn"), Type="String")
    )

    default_tags = project_tags(project)

    required_inputs = set()

    # add all resources
    for pos in range(len(stage.actions)):
        action = stage.actions[pos]

        if action.provider != "CodeBuild":
            continue

        action_resource = resources.add_resource(
            _build_project(
                name=project_name(pos), action=action, role=role.ref(), bucket=resources_bucket.ref(), tags=default_tags
            )
        )
        resources.add_output(Output(reference_name(action_resource.title, "Name"), Value=action_resource.ref()))

        required_inputs.update(action.required_inputs)

    # use collected parameters to set all input values needed as parameters
    for name in required_inputs:
        resources.add_parameter(Parameter(project.inputs[name].reference_name(), Type="String"))

    return resources
