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
"""Logic for interacting with CloudFormation service."""
import json
import uuid
from functools import partial

import requests

from .structures import Config, ProjectTemplates

__all__ = (
    "report_template_upload_success",
    "report_template_upload_failed",
    "report_inputs_upload_success",
    "report_inputs_upload_failed",
    "deploy_or_update_stacks",
)


def report_wait_condition(status: str, reason: str, data: str, url: str) -> None:
    """"""
    body = json.dumps({"Status": status, "Reason": reason, "UniqueId": uuid.uuid4(), "Data": data})
    requests.put(url=url, data=body)


report_template_upload_success = partial(report_wait_condition, "SUCCESS", "Template uploaded successfully")
report_template_upload_failed = partial(report_wait_condition, "FAILURE", "Template upload failed")
report_inputs_upload_success = partial(report_wait_condition, "SUCCESS", "All inputs loaded successfully", "")
report_inputs_upload_failed = partial(report_wait_condition, "FAILURE", "Input loading failed", "")


def deploy_or_update_stacks(project: Config, templates: ProjectTemplates) -> None:
    """"""
    # 1. create/update core template
    # 2. wait until all wait conditions are pending
    # 3. upload additional templates
    # 4. trigger wait conditions
    # 5. wait for core stack to complete
