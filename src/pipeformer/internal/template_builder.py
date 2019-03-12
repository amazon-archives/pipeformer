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
"""Logic for transforming a parsed config to one or more CloudFormation templates."""
from pipeformer.internal.templates import codepipeline, core, iam, inputs

from .structures import Config, ProjectTemplates

__all__ = ("config_to_templates",)


def config_to_templates(project: Config) -> ProjectTemplates:
    """Construct all standalone templates from project.

    :param Config project: Source project
    :return: Constructed templates
    :rtype: ProjectTemplates
    """
    iam_template = iam.build(project)

    inputs_template = inputs.build(project)

    pipeline_templates = codepipeline.build(project)

    core_template = core.build(
        project=project,
        inputs_template=inputs_template,
        iam_template=iam_template,
        pipeline_templates=pipeline_templates,
    )

    return ProjectTemplates(
        core=core_template,
        inputs=inputs_template,
        iam=iam_template,
        pipeline=pipeline_templates.template,
        codebuild=pipeline_templates.stage_templates,
    )
