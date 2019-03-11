****
TODO
****

Features
========

* Add support for updating an existing pipeformer deployment.
* Implement value expansion behavior

  * List to replica
  * Brace expansion

* Collapse CloudFormation ``CHANGE_SET_REPLACE`` + ``CHANGE_SET_EXECUTE`` pattern into a single virtual action.
* Add support for partial deployment (ex: buckets/CMK/roles already exist).

  * This will be necessary for later work.

* Periodically poll CloudFormation for the status of the stack deployment.
   We need to fail gracefully if the stack create/update fails.
* Add support for custom Role permissions.
* Define default values for source outputs and CodeBuild inputs.
* Add a "preview" mode that outputs the generated CloudFormation templates.

  * How would we preview changes that would be made by an update?

* Add a "destroy" mode.
* Add support for Lambda actions?
* Differentiate between "source" and "deploy" S3 actions.
* Support inline buildspec? I'm inclined to say no.
* Support image pull credentials?

Design Decisions
================

* Simplify inputs/outputs configuration for common patterns.
* Add sentinel resolver values: unique per-system value that can be referenced similarly to input values.
* Determine how to handle binary inputs (if at all)
* Should we re-prompt for input values that are already known?
* The inputs stack will currently overwrite non-secret values. What to do about that?
* Rather than assuming stack drift on non-secret input updates,
   should we instead send the values as parameters to the inputs stack?


Research
========

* Do wait conditions re-create on stack updates? (I think no)
* If I update a stack with a dynamic reference and the only thing that changed is the value in the referenced location,
   does the stack update? (I think no)
