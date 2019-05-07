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
"""Functional tests for ``pipeformer.internal.structures``."""
import pytest

from pipeformer.internal.structures import Config

from .. import functional_test_utils

pytestmark = [pytest.mark.local, pytest.mark.functional]


@pytest.mark.parametrize("name", functional_test_utils.vector_names())
def test_load_config(name: str):
    config_filename, _inputs = functional_test_utils.load_config(name)

    _test = Config.from_file(config_filename)
