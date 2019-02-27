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
"""Logic for building the IAM stack template."""
from awacs import (
    aws as AWS,
    awslambda as LAMBDA,
    cloudformation as CLOUDFORMATION,
    cloudwatch as CLOUDWATCH,
    codebuild as CODEBUILD,
    codepipeline as CODEPIPELINE,
    iam as IAM,
    kms as KMS,
    logs as LOGS,
    s3 as S3,
    sts as STS,
)
from awacs.helpers.trust import make_service_domain_name
from troposphere import AWS_STACK_NAME, Output, Parameter, Sub, Template, iam, kms, s3

from pipeformer.internal.structures import Config
from pipeformer.internal.util import account_arn, reference_name, resource_name


def _policy_name(name: str):
    return Sub(f"${{{AWS_STACK_NAME}}}-{name}")


def _cloudformation_role() -> iam.Role:
    """"""
    assume_policy = AWS.PolicyDocument(
        Statement=[
            AWS.Statement(
                Principal=AWS.Principal("Service", make_service_domain_name(CLOUDFORMATION.prefix)),
                Effect=AWS.Allow,
                Action=[STS.AssumeRole],
            )
        ]
    )
    # TODO: Figure out how to scope this down without breaking IAM
    _good_policy = AWS.PolicyDocument(
        Statement=[
            AWS.Statement(
                Effect=AWS.Allow,
                Action=[AWS.Action("*")],
                Resource=[
                    account_arn(service_prefix="*", resource="*"),
                    account_arn(service_prefix=S3.prefix, resource="*"),
                    account_arn(service_prefix=IAM.prefix, resource="*"),
                ],
            )
        ]
    )
    policy = AWS.PolicyDocument(
        Statement=[
            AWS.Statement(
                Effect=AWS.Allow,
                Action=[AWS.Action("*")],
                Resource=["*"]
            )
        ]
    )
    return iam.Role(
        resource_name(iam.Role, "CloudFormation"),
        AssumeRolePolicyDocument=assume_policy,
        Policies=[iam.Policy(PolicyName=_policy_name("CloudFormation"), PolicyDocument=policy)],
    )


def _codepipeline_role(artifacts_bucket: Parameter, resources_bucket: Parameter, cmk: Parameter) -> iam.Role:
    """"""
    assume_policy = AWS.PolicyDocument(
        Statement=[
            AWS.Statement(
                Principal=AWS.Principal("Service", make_service_domain_name(CODEPIPELINE.prefix)),
                Effect=AWS.Allow,
                Action=[STS.AssumeRole],
            )
        ]
    )
    policy = AWS.PolicyDocument(
        Statement=[
            AWS.Statement(
                Effect=AWS.Allow,
                Action=[S3.GetBucketVersioning, S3.PutBucketVersioning],
                Resource=[artifacts_bucket.ref(), resources_bucket.ref()],
            ),
            AWS.Statement(
                Effect=AWS.Allow,
                Action=[S3.GetObject, S3.PutObject],
                Resource=[Sub(f"${{{artifacts_bucket.title}}}/*"), Sub(f"${{{resources_bucket.title}}}/*")],
            ),
            AWS.Statement(
                Effect=AWS.Allow, Action=[KMS.Encrypt, KMS.Decrypt, KMS.GenerateDataKey], Resource=[cmk.ref()]
            ),
            AWS.Statement(
                Effect=AWS.Allow,
                Action=[CLOUDWATCH.Action("*")],
                Resource=[account_arn(service_prefix=CLOUDWATCH.prefix, resource="*")],
            ),
            AWS.Statement(
                Effect=AWS.Allow,
                Action=[IAM.PassRole],
                Resource=[account_arn(service_prefix=IAM.prefix, resource="role/*")],
            ),
            AWS.Statement(
                Effect=AWS.Allow,
                Action=[LAMBDA.InvokeFunction, LAMBDA.ListFunctions],
                Resource=[account_arn(service_prefix=LAMBDA.prefix, resource="*")],
            ),
            AWS.Statement(
                Effect=AWS.Allow,
                Action=[
                    CLOUDFORMATION.CreateStack,
                    CLOUDFORMATION.DeleteStack,
                    CLOUDFORMATION.DescribeStacks,
                    CLOUDFORMATION.UpdateStack,
                    CLOUDFORMATION.CreateChangeSet,
                    CLOUDFORMATION.DeleteChangeSet,
                    CLOUDFORMATION.DescribeChangeSet,
                    CLOUDFORMATION.ExecuteChangeSet,
                    CLOUDFORMATION.SetStackPolicy,
                    CLOUDFORMATION.ValidateTemplate,
                ],
                Resource=[account_arn(service_prefix=CLOUDFORMATION.prefix, resource="*")],
            ),
            AWS.Statement(
                Effect=AWS.Allow,
                Action=[CODEBUILD.BatchGetBuilds, CODEBUILD.StartBuild],
                Resource=[account_arn(service_prefix=CODEBUILD.prefix, resource="*")],
            ),
        ]
    )
    return iam.Role(
        resource_name(iam.Role, "CodePipeline"),
        AssumeRolePolicyDocument=assume_policy,
        Policies=[iam.Policy(PolicyName=_policy_name("CodePipeline"), PolicyDocument=policy)],
    )


def _codebuild_role(artifacts_bucket: Parameter, resources_bucket: Parameter, cmk: Parameter) -> iam.Role:
    """"""
    assume_policy = AWS.PolicyDocument(
        Statement=[
            AWS.Statement(
                Principal=AWS.Principal("Service", make_service_domain_name(CODEBUILD.prefix)),
                Effect=AWS.Allow,
                Action=[STS.AssumeRole],
            )
        ]
    )
    policy = AWS.PolicyDocument(
        Statement=[
            AWS.Statement(
                Effect=AWS.Allow,
                Action=[LOGS.CreateLogGroup, LOGS.CreateLogStream, LOGS.PutLogEvents],
                Resource=[account_arn(service_prefix=LOGS.prefix, resource="*")],
            ),
            AWS.Statement(
                Effect=AWS.Allow,
                Action=[S3.GetObject, S3.GetObjectVersion, S3.PutObject],
                Resource=[Sub(f"${{{artifacts_bucket.title}}}/*"), Sub(f"${{{resources_bucket.title}}}/*")],
            ),
            AWS.Statement(
                Effect=AWS.Allow, Action=[KMS.Encrypt, KMS.Decrypt, KMS.GenerateDataKey], Resource=[cmk.ref()]
            ),
        ]
    )
    return iam.Role(
        resource_name(iam.Role, "CodeBuild"),
        AssumeRolePolicyDocument=assume_policy,
        Policies=[iam.Policy(PolicyName=_policy_name("CodeBuild"), PolicyDocument=policy)],
    )


def build(project: Config) -> Template:
    """"""
    resources = Template(Description=f"IAM resources for pipeformer-managed project: {project.name}")

    artifacts_bucket_arn = resources.add_parameter(
        Parameter(reference_name(resource_name(s3.Bucket, "Artifacts"), "Arn"), Type="String")
    )
    resources_bucket_arn = resources.add_parameter(
        Parameter(reference_name(resource_name(s3.Bucket, "ProjectResources"), "Arn"), Type="String")
    )
    cmk_arn = resources.add_parameter(Parameter(reference_name(resource_name(kms.Key, "Stack"), "Arn"), Type="String"))

    cloudformation_role = resources.add_resource(_cloudformation_role())
    resources.add_output(
        Output(reference_name(cloudformation_role.title, "Arn"), Value=cloudformation_role.get_att("Arn"))
    )

    codepipeline_role = resources.add_resource(
        _codepipeline_role(artifacts_bucket=artifacts_bucket_arn, resources_bucket=resources_bucket_arn, cmk=cmk_arn)
    )
    resources.add_output(Output(reference_name(codepipeline_role.title, "Arn"), Value=codepipeline_role.get_att("Arn")))

    codebuild_role = resources.add_resource(
        _codebuild_role(artifacts_bucket=artifacts_bucket_arn, resources_bucket=resources_bucket_arn, cmk=cmk_arn)
    )
    resources.add_output(Output(reference_name(codebuild_role.title, "Arn"), Value=codebuild_role.get_att("Arn")))

    return resources
