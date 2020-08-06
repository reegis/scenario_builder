========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |appveyor| |requires|
        | |coveralls| |codecov|
        | |landscape| |scrutinizer| |codacy| |codeclimate|
    * - package
      - | |commits-since|

..
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|


.. |docs| image:: https://readthedocs.org/projects/scenario_builder/badge/?style=flat
    :target: https://readthedocs.org/projects/scenario_builder
    :alt: Documentation Status

.. |travis| image:: https://api.travis-ci.org/reegis/scenario_builder.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/reegis/scenario_builder

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/reegis/scenario_builder?branch=master&svg=true
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/uvchik/scenario-builder

.. |requires| image:: https://requires.io/github/reegis/scenario_builder/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/reegis/scenario_builder/requirements/?branch=master

.. |coveralls| image:: https://coveralls.io/repos/reegis/scenario_builder/badge.svg?branch=master&service=github
    :alt: Coverage Status
    :target: https://coveralls.io/r/reegis/scenario_builder

.. |codecov| image:: https://codecov.io/gh/reegis/scenario_builder/branch/master/graphs/badge.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/reegis/scenario_builder

.. |landscape| image:: https://landscape.io/github/reegis/scenario_builder/master/landscape.svg?style=flat
    :target: https://landscape.io/github/reegis/scenario_builder/master
    :alt: Code Quality Status

.. |codacy| image:: https://app.codacy.com/project/badge/Grade/08b09905fed64405a311dae925713d31
    :target: https://www.codacy.com/gh/reegis/scenario_builder?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=reegis/scenario_builder&amp;utm_campaign=Badge_Grade
    :alt: Codacy Code Quality Status

.. |codeclimate| image:: https://api.codeclimate.com/v1/badges/bd6d8bb6b3f0f16f5a1a/maintainability
   :target: https://codeclimate.com/github/reegis/scenario_builder/maintainability
   :alt: CodeClimate Maintainability
..
    .. |version| image:: https://img.shields.io/pypi/v/scenario-builder.svg
        :alt: PyPI Package latest release
        :target: https://pypi.org/project/scenario-builder

    .. |wheel| image:: https://img.shields.io/pypi/wheel/scenario-builder.svg
        :alt: PyPI Wheel
        :target: https://pypi.org/project/scenario-builder

    .. |supported-versions| image:: https://img.shields.io/pypi/pyversions/scenario-builder.svg
        :alt: Supported versions
        :target: https://pypi.org/project/scenario-builder

    .. |supported-implementations| image:: https://img.shields.io/pypi/implementation/scenario-builder.svg
        :alt: Supported implementations
        :target: https://pypi.org/project/scenario-builder

.. |commits-since| image:: https://img.shields.io/github/commits-since/reegis/scenario_builder/v0.0.1.svg
    :alt: Commits since latest release
    :target: https://github.com/reegis/scenario_builder/compare/v0.0.1...master


.. |scrutinizer| image:: https://img.shields.io/scrutinizer/quality/g/reegis/scenario_builder/master.svg
    :alt: Scrutinizer Status
    :target: https://scrutinizer-ci.com/g/reegis/scenario_builder/


.. end-badges

Tools to build scenario inputs from historical data or future assumptions

* Free software: MIT license

Installation
============

::

    pip install scenario-builder

You can also install the in-development version with::

    pip install https://github.com/reegis/scenario_builder/archive/master.zip


Documentation
=============


https://scenario_builder.readthedocs.io/


Development
===========

To run all the tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
