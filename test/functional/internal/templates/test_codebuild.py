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
"""Functional tests for ``pipeformer.internal.templates.codebuild``."""
import pytest

from pipeformer.internal.resolve import InputResolver
from pipeformer.internal.templates import codebuild

from ... import functional_test_utils

pytestmark = [pytest.mark.local, pytest.mark.functional]


@pytest.mark.parametrize("name", functional_test_utils.vector_names())
@pytest.mark.parametrize("stage_name", ("build",))
def test_parse_config(name: str, stage_name: str):
    project = functional_test_utils.populated_config(name)
    stage = InputResolver(wrapped=project.pipeline[stage_name], inputs=project.inputs)

    _test = codebuild.build(project, stage)


@pytest.mark.parametrize("name", functional_test_utils.vector_names())
@pytest.mark.parametrize("stage_name", ("build",))
def test_generate_template(name: str, stage_name: str):
    project = functional_test_utils.populated_config(name)
    stage = InputResolver(wrapped=project.pipeline[stage_name], inputs=project.inputs)
    expected = functional_test_utils.load_vector_as_template(name, f"codebuild-{stage_name}")

    test = codebuild.build(project, stage)

    assert test.to_json() == expected.to_json()
