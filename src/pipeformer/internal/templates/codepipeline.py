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
"""Logic for building the CodePipeline stack template."""
from collections import OrderedDict
from typing import Dict

from troposphere import GetAtt, Parameter, Ref, Tags, Template, cloudformation, codepipeline, iam, s3

from pipeformer.internal.resolve import InputResolver
from pipeformer.internal.structures import Config, Pipeline
from pipeformer.internal.util import VALUE_SEPARATOR, reference_name, resource_name

from . import codebuild as codebuild_template, project_tags

__all__ = ("build",)
_ACTION_TYPE_IDS = {
    "GitHub": codepipeline.ActionTypeId(Category="Source", Owner="ThirdParty", Provider="GitHub", Version="1"),
    "CodeBuild": codepipeline.ActionTypeId(Category="Build", Owner="AWS", Provider="CodeBuild", Version="1"),
    "CloudFormation": codepipeline.ActionTypeId(Category="Deploy", Owner="AWS", Provider="CloudFormation", Version="1"),
}
_DEFAULT_PARAMETERS = (
    Parameter(reference_name(resource_name(s3.Bucket, "Artifacts"), "Name"), Type="String"),
    Parameter(reference_name(resource_name(s3.Bucket, "ProjectResources"), "Name"), Type="String"),
    Parameter(reference_name(resource_name(iam.Role, "CodePipeline"), "Arn"), Type="String"),
    Parameter(reference_name(resource_name(iam.Role, "CodeBuild"), "Arn"), Type="String"),
    Parameter(reference_name(resource_name(iam.Role, "CloudFormation"), "Arn"), Type="String"),
)


def _action_configuration(action: InputResolver, stage_name: str, action_number: int) -> Dict[str, str]:
    """Compile a CloudFormation CodePipeline action configuration.

    :param action: PipeFormer action definition
    :param stage_name: Stage name
    :param action_number: Action counter
    :return: CloudFormation action configuration
    """
    codebuild_output = reference_name(codebuild_template.project_name(action_number), "Name")
    _action_type_default_configurations = {  # pylint: disable=invalid-name
        "GitHub": lambda: dict(PollForSourceChanges=True),
        "CodeBuild": lambda: dict(ProjectName=GetAtt(_codebuild_stage_name(stage_name), f"Outputs.{codebuild_output}")),
        "CloudFormation": lambda: dict(RoleArn=Ref(reference_name(resource_name(iam.Role, "CloudFormation"), "Arn"))),
    }

    config = _action_type_default_configurations.get(action.provider, lambda: {})()
    # expand and re-cast configuration to resolve references
    config.update(dict(**action.configuration))
    return config


def _stage_action(stage_name: str, action_number: int, action: InputResolver) -> codepipeline.Actions:
    """Construct a CodePipeline action resource.

    :param stage_name: Stage name
    :param action_number: Action counter
    :param action: PipeFormer action definition
    :return: CloudFormation action definition
    """
    try:
        action_type_id = _ACTION_TYPE_IDS[action.provider]
    except KeyError:
        raise ValueError(
            f'Unknown action provider "{action.provider}". Supported providers are: {list(_ACTION_TYPE_IDS.keys())!r}'
        )

    kwargs = dict(
        Name=f"{stage_name}-{action_number}",
        RunOrder=action.run_order,
        ActionTypeId=action_type_id,
        Configuration=_action_configuration(action, stage_name, action_number),
    )

    if action.inputs:
        kwargs["InputArtifacts"] = [codepipeline.InputArtifacts(Name=name) for name in action.inputs]

    if action.outputs:
        kwargs["OutputArtifacts"] = [codepipeline.OutputArtifacts(Name=name) for name in action.outputs]

    return codepipeline.Actions(**kwargs)


def _stage(stage: InputResolver) -> codepipeline.Stages:
    """Construct a CodePipeline stage resource.

    :param stage: PipeFormer stage definition
    :return: CloudFormation stage definition
    """
    stage_actions = []
    for pos, action in enumerate(stage.actions):
        stage_actions.append(_stage_action(stage.name, pos, action))

    return codepipeline.Stages(Name=stage.name, Actions=stage_actions)


def _url_reference(stage_name) -> str:
    """Build a stage stack template URL reference logical resource name.

    :param stage_name: Stage name
    :return: Logical resource name
    """
    return reference_name(VALUE_SEPARATOR.join(("Template", "CodeBuild", "Stage", stage_name)), "Url")


def _codebuild_stage_name(stage_name) -> str:
    """Build a CodeBuild stage logical resource name.

    :param stage_name: Stage name
    :return: Logical resource name
    """
    return resource_name(cloudformation.Stack, VALUE_SEPARATOR.join(("CodeBuild", "Stage", stage_name)))


def _stack(
    project: Config, stage: InputResolver, stage_name: str, default_tags: Tags
) -> (cloudformation.Stack, Parameter):
    """Construct a nested CloudFormation stack template

    :param project: PipeFormer project
    :param stage: Pipeline stage definition
    :param stage_name: Stage name
    :param default_tags: Default tags to add to resources
    :return: Constructed stack template and a parameter to add to the parent template.
    """
    # Add stack to template
    parameters = {
        name: Ref(name)
        for name in (
            reference_name(resource_name(s3.Bucket, "ProjectResources"), "Name"),
            reference_name(resource_name(iam.Role, "CodeBuild"), "Arn"),
        )
    }

    for name in stage.required_inputs:
        parameters[project.inputs[name].reference_name()] = Ref(project.inputs[name].reference_name())

    url_reference = _url_reference(stage_name)

    return (
        cloudformation.Stack(
            _codebuild_stage_name(stage_name), TemplateURL=Ref(url_reference), Parameters=parameters, Tags=default_tags
        ),
        Parameter(url_reference, Type="String"),
    )


def build(project: Config) -> Pipeline:
    """Construct CodePipeline templates for a project.

    :param project: PipeFormer project
    :return: Constructed templates
    """
    pipeline_template = Template(Description=f"CodePipeline resources for pipeformer-managed project: {project.name}")

    # Add resource parameters
    for param in _DEFAULT_PARAMETERS:
        pipeline_template.add_parameter(param)

    required_inputs = set()

    default_tags = project_tags(project)

    stage_templates = OrderedDict()
    pipeline_stages = []
    for stage_name, stage in project.pipeline.items():
        stage_loader = InputResolver(wrapped=stage, inputs=project.inputs)

        stage_resources_template = codebuild_template.build(project, stage_loader)

        pipeline_stages.append(_stage(stage_loader))

        stack_resource, stack_parameter = _stack(project, stage_loader, stage_name, default_tags)

        required_inputs.update(stage_loader.required_inputs)

        if stage_resources_template.resources:
            pipeline_template.add_resource(stack_resource)
            stage_templates[stage_name] = stage_resources_template
            pipeline_template.add_parameter(stack_parameter)

    # Add inputs parameters
    for name in required_inputs:
        pipeline_template.add_parameter(Parameter(project.inputs[name].reference_name(), Type="String"))

    # Add pipeline resource

    pipeline_resource = codepipeline.Pipeline(
        resource_name(codepipeline.Pipeline, project.name),
        ArtifactStore=codepipeline.ArtifactStore(
            Type="S3", Location=Ref(reference_name(resource_name(s3.Bucket, "Artifacts"), "Name"))
        ),
        RoleArn=Ref(reference_name(resource_name(iam.Role, "CodePipeline"), "Arn")),
        Stages=pipeline_stages,
    )
    pipeline_template.add_resource(pipeline_resource)

    return Pipeline(template=pipeline_template, stage_templates=stage_templates)
