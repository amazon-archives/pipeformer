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
"""Helper tools for use with functional tests."""
import json
import os
from collections import OrderedDict
from typing import Dict

from troposphere.template_generator import TemplateGenerator

from pipeformer.internal import structures, util

_TEST_VECTORS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "vectors")


def vector_names():
    for child in os.listdir(_TEST_VECTORS_DIR):
        abs_child = os.path.abspath(os.path.join(_TEST_VECTORS_DIR, child))
        if os.path.isdir(abs_child):
            yield abs_child


def check_vector_exists(name: str):
    if not os.path.isdir(os.path.join(_TEST_VECTORS_DIR, name)):
        raise ValueError(f"Vector name {name!r} does not exist.")


def load_vector(vector_name: str, vector_type: str) -> Dict:
    check_vector_exists(vector_name)

    vector_filename = os.path.join(_TEST_VECTORS_DIR, vector_name, vector_type) + ".json"

    with open(vector_filename) as f:
        return json.load(f)


def load_vector_as_template(vector_name: str, vector_type: str) -> TemplateGenerator:
    vector_dict = load_vector(vector_name, vector_type)
    return TemplateGenerator(vector_dict)


def load_vectors_as_pipeline_templates(vector_name: str) -> structures.Pipeline:
    pipeline = load_vector_as_template(vector_name, "codepipeline")
    stages = OrderedDict()

    for param in pipeline.parameters:
        if param.startswith("Template0CodeBuild0Stage0"):
            stage_name = param.split(util.VALUE_SEPARATOR)[3]
            stages[stage_name] = load_vector_as_template(vector_name, f"codebuild-{stage_name}")

    return structures.Pipeline(template=pipeline, stage_templates=stages)


def load_config(name: str) -> (str, Dict[str, str]):
    check_vector_exists(name)

    config_filename = os.path.join(_TEST_VECTORS_DIR, name, "config.yaml")

    with open(os.path.join(_TEST_VECTORS_DIR, name, "config_inputs.json"), "r") as f:
        inputs = json.load(f)

    return config_filename, inputs


def populated_config(name: str) -> structures.Config:
    config_filename, inputs = load_config(name)

    project = structures.Config.from_file(config_filename)
    for name, value in inputs.items():
        project.inputs[name].value = value

    return project
