##########
pipeformer
##########

.. image:: https://img.shields.io/pypi/v/pipeformer.svg
   :target: https://pypi.python.org/pypi/pipeformer
   :alt: Latest Version

.. image:: https://img.shields.io/pypi/pyversions/pipeformer.svg
   :target: https://pypi.python.org/pypi/pipeformer
   :alt: Supported Python Versions

.. image:: https://img.shields.io/badge/code_style-black-000000.svg
   :target: https://github.com/ambv/black
   :alt: Code style: black

.. image:: https://readthedocs.org/projects/pipeformer/badge/
   :target: https://pipeformer.readthedocs.io/en/stable/
   :alt: Documentation Status

.. image:: https://travis-ci.org/awslabs/pipeformer.svg?branch=master
   :target: https://travis-ci.org/awslabs/pipeformer

.. image:: https://ci.appveyor.com/api/projects/status/REPLACEME/branch/master?svg=true
   :target: https://ci.appveyor.com/project/REPLACEME

Tool for generating CodePipeline pipelines and related resources from a simple configuration.


********
Abstract
********

Services like CodePipeline and CodeBuild are great building blocks,
but can be complicated to set up and use in a consistent way.

CloudFormation makes it possible to create and update resources in a consistent and repeatable way,
but can be complicated and verbose to define.

The goal of Pipeformer is combine these properties by providing a very simple, but extensible,
way to use these services with your project.

Tenets
======

* Simple

  * For the majority of projects, the majority of resource configurations will be identical.
    Only require the user to set the values that are actually important to them.
  * The user should not need to know about resources that they will not directly touch.

* Flexible

  * While most users should not need to, users must be able to override most settings if they do need to.

**********
How to Use
**********

1. Define your configuration file.
1. Deploy with pipeformer.

User Experience
===============

The primary operating mode for pipeformer is to take your configuration,
use it to generate CloudFormation templates that describe the needed resources,
and then deploy those templates.

Configuration
=============

`Configuration File Format <CONFIG_FORMAT.rst>`_

What Does it Do?
================

`Resources Created <RESOURCES.rst>`_

***************
Getting Started
***************

Required Prerequisites
======================

* Supported Python versions

  * 3.6+

Installation
============

.. code::

   $ pip install pipeformer

***********
Development
***********

Prerequisites
=============

* Required

  * Python 3.6+
  * `tox`_ : We use tox to drive all of our testing and package management behavior.
     Any tests that you want to run should be run using tox.

* Optional

  * `pyenv`_ : If you want to test against multiple versions of Python and are on Linux or MacOS,
    we recommend using pyenv to manage your Python runtimes.
  * `tox-pyenv`_ : Plugin for tox that enables it to use pyenv runtimes.
  * `detox`_ : Parallel plugin for tox. Useful for running a lot of test environments quickly.

Setting up pyenv
----------------

If you are using pyenv, make sure that you have set up all desired runtimes and configured the environment
before attempting to run any tests.

1. Install all desired runtimes.

   * ex: ``pyenv install 3.7.0``
   * **NOTE:** You can only install one runtime at a time with the ``pyenv install`` command.

1. In the root of the checked out repository for this package, set the runtimes that pyenv should use.

   * ex: ``pyenv local 3.7.0 3.6.4``
   * **NOTE:** This creates the ``.python-version`` file that pyenv will use. Pyenv treats the first
     version in that file as the default Python version.


Running tests
=============

There are two criteria to consider when running our tests:
what version of Python do you want to use and what type of tests do you want to run?

For a full listing of the available types of tests available,
see the ``[testenv]commands`` section of the ``tox.ini`` file.

All tests should be run using tox.
To do this, identify the test environment that you want tox to run using the ``-e ENV_NAME`` flag.
The standard test environments are named as a combination of the Python version
and the test type in the form ``VERSION-TYPE``.
For example, to run the ``local`` tests against CPython 3.7:

.. code-block:: bash

    tox -e py37-local

If you want to provide custom parameters to pytest to manually identify what tests you want to run,
use the ``manual`` test type. Any arguments you want to pass to pytest must follow the ``--`` argument.
Anything before that argument is passed to tox. Everything after that argument is passed to pytest.

.. code-block:: bash

    tox -e py37-manual -- test/unit/test_example_file.py

Before submitting a pull request
================================

Before submitting a pull request, please run the ``lint`` tox environment.
This will ensure that your submission meets our code formatting requirements
and will pass our continous integration code formatting tests.


.. _tox: http://tox.readthedocs.io/
.. _detox: https://pypi.org/project/detox/
.. _tox-pyenv: https://pypi.org/project/tox-pyenv/
.. _pyenv: https://github.com/pyenv/pyenv
