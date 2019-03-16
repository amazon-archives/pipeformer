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
"""Modules for building CloudFormation templates."""
from troposphere import Tags

from pipeformer.internal.structures import Config


def project_tags(project: Config) -> Tags:
    """Construct default tags for a project.

    :param project: PipeFormer project
    :return: Tags
    """
    return Tags(pipeformer=project.name)
