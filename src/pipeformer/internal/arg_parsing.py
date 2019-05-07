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
"""Helper functions for parsing and processing input arguments."""
import argparse
import os
from typing import Iterator, Optional

from pipeformer.identifiers import __version__

__all__ = ("parse_args",)


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser.

    :returns: Constructed argument parser
    """
    parser = argparse.ArgumentParser(description="Build continuous delivery pipelines powered by AWS CodePipeline.")

    version_or_config = parser.add_mutually_exclusive_group(required=True)

    version_or_config.add_argument("--version", action="version", version="pipeformer/{}".format(__version__))
    version_or_config.add_argument("--config", help="Path to pipeformer config file.")

    parser.add_argument(
        "-v",
        dest="verbosity",
        action="count",
        help="Enables logging and sets detail level. Multiple -v options increases verbosity (max: 4).",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppresses most warning and diagnostic messages")

    return parser


def parse_args(raw_args: Optional[Iterator[str]] = None) -> argparse.Namespace:
    """Handle argparse to collect the needed input values.

    :param raw_args: List of arguments
    :returns: parsed arguments
    """
    parser = _build_parser()
    parsed_args = parser.parse_args(raw_args)

    if not os.path.isfile(parsed_args.config):
        parser.error('Invalid filename: "{}"'.format(parsed_args.config))

    return parsed_args
