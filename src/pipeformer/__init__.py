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
"""pipeformer."""
import uuid
from typing import Iterator, Optional

from .deploy import Deployer
from .identifiers import __version__
from .input_handling import DefaultInputHandler
from .internal.arg_parsing import parse_args
from .internal.logging_utils import setup_logger
from .internal.structures import Config
from .internal.template_builder import config_to_templates

__all__ = ("__version__", "cli")


def cli(raw_args: Optional[Iterator[str]] = None):
    """CLI entry point.  Processes arguments, sets up the key provider, and processes requested action.

    :returns: Execution return value intended for ``sys.exit()``
    """
    args = parse_args(raw_args)

    setup_logger(args.verbosity, args.quiet)

    # 1. parse config file
    project = Config.from_file(args.config)

    # TODO: Use a better prefix
    prefix = "pipeformer-" + str(uuid.uuid4()).split("-")[-1]

    project_deployer = Deployer(project=project, stack_prefix=prefix)

    project_deployer.deploy_standalone()
