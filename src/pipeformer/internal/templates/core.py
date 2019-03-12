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
"""Logic for building the core stack template."""
from typing import Any, Dict, Iterable, Optional

from awacs import aws as AWS, kms as KMS
from troposphere import GetAtt, Select, Split, Sub, Tags, Template, cloudformation, kms, s3

from pipeformer.internal.structures import Config, Pipeline, WaitConditionStack
from pipeformer.internal.util import VALUE_SEPARATOR, account_arn, reference_name, resource_name

from . import project_tags

__all__ = ("build",)


def _project_key(project: Config) -> kms.Key:
    """Construct the AWS CMK that will be used to protect project resources.

    :param project: Source project
    :return: Constructed key
    """
    policy = AWS.PolicyDocument(
        Version="2012-10-17",
        Statement=[
            AWS.Statement(
                Effect=AWS.Allow,
                Principal=AWS.Principal("AWS", account_arn("iam", "root")),
                Action=[
                    KMS.Encrypt,
                    KMS.Decrypt,
                    KMS.ReEncrypt,
                    KMS.GenerateDataKey,
                    KMS.GenerateDataKeyWithoutPlaintext,
                    KMS.DescribeKey,
                    KMS.GetKeyPolicy,
                ],
                Resource=["*"],
            ),
            # TODO: Change admin statement to some other principal?
            AWS.Statement(
                Effect=AWS.Allow,
                Principal=AWS.Principal("AWS", account_arn("iam", "root")),
                Action=[
                    KMS.GetKeyPolicy,
                    KMS.PutKeyPolicy,
                    KMS.ScheduleKeyDeletion,
                    KMS.CancelKeyDeletion,
                    KMS.CreateAlias,
                    KMS.DeleteAlias,
                    KMS.UpdateAlias,
                    KMS.DescribeKey,
                    KMS.EnableKey,
                    KMS.DisableKey,
                    KMS.GetKeyRotationStatus,
                    KMS.EnableKeyRotation,
                    KMS.DisableKeyRotation,
                    KMS.ListKeyPolicies,
                    KMS.ListResourceTags,
                    KMS.TagResource,
                    KMS.UntagResource,
                ],
                Resource=["*"],
            ),
        ],
    )
    return kms.Key(
        resource_name(kms.Key, "Stack"),
        Enabled=True,
        EnableKeyRotation=False,
        KeyPolicy=policy,
        Tags=project_tags(project),
    )


def _bucket(name: str, cmk_arn: GetAtt, tags: Tags) -> s3.Bucket:
    """Construct a S3 bucket resource with default SSE-KMS using the specified CMK.

    :param name: Logical resource name
    :param cmk_arn: Reference to Arn of CMK resource
    :param tags: Tags to apply to bucket
    :return: Constructed S3 bucket resource
    """
    return s3.Bucket(
        resource_name(s3.Bucket, name),
        BucketEncryption=s3.BucketEncryption(
            ServerSideEncryptionConfiguration=[
                s3.ServerSideEncryptionRule(
                    ServerSideEncryptionByDefault=s3.ServerSideEncryptionByDefault(
                        SSEAlgorithm="aws:kms", KMSMasterKeyID=cmk_arn
                    )
                )
            ]
        ),
        Tags=tags,
    )


def _wait_condition_data_to_s3_url(condition: cloudformation.WaitCondition, artifacts_bucket: s3.Bucket) -> Sub:
    """Build a CloudFormation ``Sub`` structure that resolves to the S3 key reported to a wait condition.

    :param condition: Wait condition to reference
    :param artifacts_bucket: Bucket to reference
    """
    return Sub(
        f"https://${{{artifacts_bucket.title}.DomainName}}/${{key}}",
        {"key": Select(3, Split('"', condition.get_att("Data")))},
    )


def _wait_condition(
    type_name: str, base_name: str
) -> (cloudformation.WaitCondition, cloudformation.WaitConditionHandle):
    """Construct a wait condition and handle.

    :param type_name:
    :param base_name:
    :return:
    """
    handle = cloudformation.WaitConditionHandle(VALUE_SEPARATOR.join(("Upload", type_name, base_name)))
    condition = cloudformation.WaitCondition(
        VALUE_SEPARATOR.join(("WaitFor", handle.title)), Handle=handle.ref(), Count=1, Timeout=3600
    )
    return condition, handle


def _wait_condition_stack(
    base_name: str,
    parameters: Dict[str, Any],
    artifacts_bucket: s3.Bucket,
    tags: Tags,
    depends_on: Optional[Iterable] = None,
) -> WaitConditionStack:
    """

    :param base_name:
    :param parameters:
    :param artifacts_bucket:
    :param tags:
    :param depends_on:
    :return:
    """
    if depends_on is None:
        depends_on = []

    condition, handle = _wait_condition("Template", base_name)
    stack = cloudformation.Stack(
        resource_name(cloudformation.Stack, base_name),
        DependsOn=[condition.title] + depends_on,
        TemplateURL=_wait_condition_data_to_s3_url(condition, artifacts_bucket),
        Parameters=parameters,
        Tags=tags,
    )
    return WaitConditionStack(condition=condition, handle=handle, stack=stack)


def build(project: Config, inputs_template: Template, iam_template: Template, pipeline_templates: Pipeline) -> Template:
    """Construct a core stack template for a stand-alone deployment.

    :param project:
    :param inputs_template:
    :param iam_template:
    :param pipeline_templates:
    :return:
    """
    default_tags = project_tags(project)

    core = Template(Description=f"Core resources for pipeformer-managed project: {project.name}")

    # Project CMK
    cmk = core.add_resource(_project_key(project))

    # Artifacts Bucket
    artifacts_bucket = core.add_resource(_bucket(name="Artifacts", cmk_arn=cmk.get_att("Arn"), tags=default_tags))
    # Project Bucket
    project_bucket = core.add_resource(_bucket(name="ProjectResources", cmk_arn=cmk.get_att("Arn"), tags=default_tags))

    # Inputs Stack
    inputs_stack = _wait_condition_stack(
        base_name="Inputs",
        parameters={reference_name(cmk.title, "Arn"): cmk.get_att("Arn")},
        artifacts_bucket=artifacts_bucket,
        tags=default_tags,
    )
    core.add_resource(inputs_stack.condition)
    core.add_resource(inputs_stack.handle)
    core.add_resource(inputs_stack.stack)

    # IAM Stack
    iam_stack = _wait_condition_stack(
        base_name="Iam",
        parameters={
            reference_name(artifacts_bucket.title, "Arn"): artifacts_bucket.get_att("Arn"),
            reference_name(project_bucket.title, "Arn"): project_bucket.get_att("Arn"),
            reference_name(cmk.title, "Arn"): cmk.get_att("Arn"),
        },
        artifacts_bucket=artifacts_bucket,
        tags=default_tags,
    )
    core.add_resource(iam_stack.condition)
    core.add_resource(iam_stack.handle)
    core.add_resource(iam_stack.stack)

    # Pipeline Stack and Prerequisites
    pipeline_parameters = {
        # Buckets
        reference_name(artifacts_bucket.title, "Name"): artifacts_bucket.ref(),
        reference_name(project_bucket.title, "Name"): project_bucket.ref(),
    }

    pipeline_depends_on = []

    # Pass on Inputs and Roles
    for nested_template, nested_stack in ((inputs_template, inputs_stack), (iam_template, iam_stack)):
        pipeline_depends_on.append(nested_stack.stack.title)
        for name in nested_template.outputs.keys():
            pipeline_parameters[name] = GetAtt(nested_stack.stack.title, f"Outputs.{name}")

    # Add waiters for each pipeline stage resource stack template
    for name, stage_template in pipeline_templates.stage_templates.items():
        stage_name = VALUE_SEPARATOR.join(("CodeBuild", "Stage", name))
        condition, handle = _wait_condition("Template", stage_name)

        core.add_resource(condition)
        core.add_resource(handle)

        pipeline_depends_on.append(condition.title)
        pipeline_parameters[
            reference_name(VALUE_SEPARATOR.join(("Template", stage_name)), "Url")
        ] = _wait_condition_data_to_s3_url(condition, artifacts_bucket)

    input_condition, input_handle = _wait_condition("Input", "Values")
    pipeline_depends_on.append(input_condition.title)
    core.add_resource(input_condition)
    core.add_resource(input_handle)

    pipeline_stack = _wait_condition_stack(
        base_name="Pipeline",
        parameters=pipeline_parameters,
        artifacts_bucket=artifacts_bucket,
        tags=default_tags,
        depends_on=pipeline_depends_on,
    )
    core.add_resource(pipeline_stack.condition)
    core.add_resource(pipeline_stack.handle)
    core.add_resource(pipeline_stack.stack)

    return core
