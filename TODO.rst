****
TODO
****

[#43] * Add versioning to the config format

Features
========

[#28] * Add support for updating an existing pipeformer deployment.
* Implement value expansion behavior

[#35]   * List to replica
[#35]   * Brace expansion

[#30] * Collapse CloudFormation ``CHANGE_SET_REPLACE`` + ``CHANGE_SET_EXECUTE`` pattern into a single virtual action.
[#41] * Add support for partial deployment (ex: buckets/CMK/roles already exist).

  * This will be necessary for later work.

[#31] * Periodically poll CloudFormation for the status of the stack deployment.
   We need to fail gracefully if the stack create/update fails.
[#39] * Add support for custom Role permissions.
[#36] * Define default values for source outputs and CodeBuild inputs.
[#40] * Add a "preview" mode that outputs the generated CloudFormation templates.

  [#40] * How would we preview changes that would be made by an update?

[#29] * Add a "destroy" mode.
[#38] * Add support for Lambda actions?
[#38] * Differentiate between "source" and "deploy" S3 actions.
[#37] * Support inline buildspec? I'm inclined to say no.
[#42] * Support image pull credentials?

Design Decisions
================

[#27] * Simplify inputs/outputs configuration for common patterns.
[#36] * Add sentinel resolver values: unique per-system value that can be referenced similarly to input values.
[#45] * Determine how to handle binary inputs (if at all)
[#32] * Should we re-prompt for input values that are already known?
[#44] * The inputs stack will currently overwrite non-secret values. What to do about that?
[#44] * Rather than assuming stack drift on non-secret input updates,
   should we instead send the values as parameters to the inputs stack?


Research
========

[#33] * Do wait conditions re-create on stack updates? (I think no)
[#34] * If I update a stack with a dynamic reference and the only thing that changed is the value in the referenced location,
   does the stack update? (I think no)
