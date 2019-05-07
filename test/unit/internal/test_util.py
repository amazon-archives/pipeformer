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
"""Unit tests for ``pipeformer.internal.util``."""
import pytest
from troposphere import Sub, kms

from pipeformer.internal.util import account_arn, reference_name, resource_name

pytestmark = [pytest.mark.local, pytest.mark.functional]


def test_resource_name():
    assert resource_name(kms.Key, "ExampleKey") == "Key0ExampleKey"


def test_reference_name():
    assert reference_name("ExampleName", "ExampleType") == "ExampleName0ExampleType"


@pytest.mark.parametrize(
    "service_prefix, resource, expected",
    (
        (
            "kms",
            "alias/ExampleAlias",
            Sub("arn:${AWS::Partition}:kms:${AWS::Region}:${AWS::AccountId}:alias/ExampleAlias"),
        ),
        ("s3", "ExampleBucket", Sub("arn:${AWS::Partition}:s3:::ExampleBucket")),
        ("iam", "role/ExampleRole", Sub("arn:${AWS::Partition}:iam::${AWS::AccountId}:role/ExampleRole")),
    ),
)
def test_account_arn(service_prefix, resource, expected):
    expected_dict = expected.to_dict()

    actual = account_arn(service_prefix, resource).to_dict()

    assert actual == expected_dict
