# Vallen AE Python Tools

[![CI](https://github.com/vallen-systems/pyVallenAE/workflows/CI/badge.svg)](https://github.com/vallen-systems/pyVallenAE/actions)
[![Documentation Status](https://readthedocs.org/projects/pyvallenae/badge/?version=latest)](https://pyvallenae.readthedocs.io/en/latest/?badge=latest)
[![Coverage Status](https://coveralls.io/repos/github/vallen-systems/pyVallenAE/badge.svg?branch=master)](https://coveralls.io/github/vallen-systems/pyVallenAE)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/pypi/v/vallenae)](https://pypi.org/project/vallenae)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/vallenae)](https://pypi.org/project/vallenae)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**[Documentation](https://pyvallenae.readthedocs.io/) · [Examples](https://pyvallenae.readthedocs.io/en/stable/examples)**

Python tools to extract and analyze Acoustic Emission measurement data.
The package includes following modules:

- vallenae.**io**: Reading (and writing) of Vallen Systeme SQLite database files (*.pridb, *.tradb, *.trfdb)
- vallenae.**features**: Extraction of Acoustic Emission features
- vallenae.**timepicker**: Timepicking algorithms for arrival time estimations

> **Note**:
> A free/lite version of the Vallen AE Suite is available since the release R2020.
> If offers the basic features for real-time data visualization and analysis with VisualAE.
> So you could write you own pridb/tradb files and have real-time visualizations with VisualAE.
>
> The Vallen AE Suite can be downloaded [here](https://www.vallen.de/downloads/).

## Installation

Install the latest version from [PyPI](https://pypi.org/project/vallenae):

```shell
$ pip install vallenae
```

Please note, that `vallenae` requires Python 3.6 or newer. On Linux systems, `pip` is usually mapped to Python 2, so use `pip<version>` (e.g. `pip3` or `pip3.7`) instead. Alternatively, you can run `pip` from your specific Python version with `python<version> -m pip`.

## Contributing

Feature requests, bug reports and fixes are always welcome!
Just [create an issue](https://github.com/vallen-systems/pyVallenAE/issues/new) or make a pull-request.

After cloning the repository, you can easily install the development environment and tools 
([pylint](https://www.pylint.org), [mypy](http://mypy-lang.org), [pytest](https://pytest.org), [tox](https://tox.readthedocs.io), [sphinx](https://www.sphinx-doc.org)).

```shell
# Clone this repository
$ git clone https://github.com/vallen-systems/pyVallenAE.git
$ cd pyVallenAE

# Install package and dependencies
$ pip install -e .[dev]

# Run the test suite with tox
$ tox

# Build the documentation with Sphinx
$ cd docs
$ make html  # on Linux
$ ./make.bat html  # on Windows
```
