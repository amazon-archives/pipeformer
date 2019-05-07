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
"""Functional tests for ``pipeformer.internal.templates.core``."""
import pytest

from pipeformer.internal.templates import core

from ... import functional_test_utils

pytestmark = [pytest.mark.local, pytest.mark.functional]


@pytest.mark.parametrize("name", functional_test_utils.vector_names())
def test_parse_config(name: str):
    project = functional_test_utils.populated_config(name)
    inputs_template = functional_test_utils.load_vector_as_template(name, "inputs")
    iam_template = functional_test_utils.load_vector_as_template(name, "iam")
    pipeline_templates = functional_test_utils.load_vectors_as_pipeline_templates(name)

    _test = core.build(project, inputs_template, iam_template, pipeline_templates)


@pytest.mark.parametrize("name", functional_test_utils.vector_names())
def test_generate_template(name: str):
    project = functional_test_utils.populated_config(name)
    expected = functional_test_utils.load_vector_as_template(name, "core")
    inputs_template = functional_test_utils.load_vector_as_template(name, "inputs")
    iam_template = functional_test_utils.load_vector_as_template(name, "iam")
    pipeline_templates = functional_test_utils.load_vectors_as_pipeline_templates(name)

    test = core.build(project, inputs_template, iam_template, pipeline_templates)

    assert test.to_json() == expected.to_json()
