=================
Resources Created
=================

Pipeformer creates all resources necessary to build the pipeline that you describe in your configuration.

Stand-Alone Mode
----------------

In stand-alone mode, pipeformer assumes that all necessary resources need to be created.

In this operating mode,
all core resources are defined in a central CloudFormation stack that also contains all other CloudFormation stacks.

Resources
---------

Core Resources
^^^^^^^^^^^^^^

The core resources are resources that are needed by all other components.
These include:

* Application resources S3 bucket made available to the application for use.
* Artifact S3 bucket for use by Pipeformer and resources.
* IAM Roles for use within Pipeformer for:

  * CloudFormation
  * CodePipeline pipelines
  * CodeBuild projects

* A KMS CMK that is used to protect all resources and data managed by pipeformer.

Inputs
^^^^^^

Any input values defined in your configuration need to be stored somewhere.
Pipeformer stores them either in Secrets Manager if the input is marked as secret,
or SSM Parameter Store if it is not.

All input resources are managed in a separate CloudFormation stack,
with a separate Secrets Manager Secret or Parameter Store Parameter resource for each input.
The values stored in these resources are managed outside of CloudFormation.

CodeBuild
^^^^^^^^^

Pipeline actions that use CodeBuild require a unique CodeBuild project for each action.
Because of this, and to avoid CloudFormation per-stack resource limits,
Pipeformer creates a separate CloudFormation stack for each pipeline stage that contains at least one CodeBuild action.
These stacks contain only CodeBuild resources.

CodePipeline
^^^^^^^^^^^^

Finally, a CloudFormation stack is created that contains the CodePipeline resource itself.
All CodeBuild stacks are created as nested stacks of this stack.
