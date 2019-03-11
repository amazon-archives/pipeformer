==================
Config File Format
==================

Pipeformer is configured using a YAML file with the below contents.

Structure
---------

* **name** : string (required) : Project name. Used in names and descriptions to identify resources as belonging to this project.
* **description** : string (required) : Project description. *Not currently used.*
* **inputs** : map : Inputs that will be required at stack creation or update.

  * **<input name>** : map : Describes an input value.

    * **description** : string (required) : Used for the input prompt and any resource descriptions as appropriate.
    * **secret** : boolean (required) : Determines if this input is treated as secret.

* **roles** : map : Additional permissions to apply to generated IAM Roles. *Not currently used.*

* **pipeline** : map : Definition of desired pipeline.
  Each member defines a stage in the pipeline and is a list of action definitions.

  * <stage name> : list : Description of pipeline stage actions.

    * **provider** : string (required) : `CodePipeline action provider name`_.
    * **run_order** : int : The order in which CodePipeline runs this action (default: 1).
    * **inputs** : list of strings : List of CodePipeline input artifact names.
    * **outputs** : list of strings : List of CodePipeline output artifact names.
    * **configuration** : map : Additional configuration values to provide to in CodePipeline Action definition.
    * **image** : string (required for CodeBuild actions): Docker image to use for CodeBuild action.
    * **environment_type** : string : CodeBuild `environment-type`_ value.
      *If not provided, we assume Linux unless the image name contains "windows" in any casing.*
    * **buildspec** : string : Path to buildspec file in source.
    * **compute_type** : string : CodeBuild `compute-type`_ name. (default: BUILD_GENERAL1_SMALL)
    * **env** : string-string map : Custom environment variable values to set in action.

Input Value Resolution
----------------------

Input values can be referenced using strings of the form: ``"{INPUT:VariableName}"``

These values are referenced from their storage locations using `CloudFormation dynamic references`_.

Example
-------

.. code-block:: yaml

    name: example project
    description: This is an example project.

    inputs:
      GitHubToken:
        description: GitHub user access token that CodePipeline will use to authenticate to GitHub.
        secret: true
      GitHubOwner:
        description: GitHub user that owns target repository.
        secret: false

    pipeline:
      source:
        - provider: GitHub
          outputs:
            - SourceOutput
          configuration:
            Owner: "{INPUT:GitHubOwner}"
            Repo: example
            Branch: master
            OAuthToken: "{INPUT:GitHubToken}"

      build:
        - provider: CodeBuild
          image: aws/codebuild/python:3.6.5
          buildspec: .chalice/buildspec.yaml
          env:
            key1: value2
            key3: value4
          inputs:
            - SourceOutput
          outputs:
            - CompiledCfnTemplate


.. _CodePipeline action provider name: https://docs.aws.amazon.com/codepipeline/latest/userguide/reference-pipeline-structure.html#actions-valid-providers
.. _environment-type: https://docs.aws.amazon.com/codebuild/latest/APIReference/API_ProjectEnvironment.html#CodeBuild-Type-ProjectEnvironment-type
.. _compute-type: https://docs.aws.amazon.com/codebuild/latest/APIReference/API_ProjectEnvironment.html#CodeBuild-Type-ProjectEnvironment-computeType
.. _CloudFormation dynamic references: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html
