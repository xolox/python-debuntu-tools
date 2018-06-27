#!/usr/bin/env python

# Setup script for the `debuntu-tools' package.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 27, 2018
# URL: https://debuntu-tools.readthedocs.io

"""
Setup script for the `debuntu-tools` package.

**python setup.py install**
  Install from the working directory into the current Python environment.

**python setup.py sdist**
  Build a source distribution archive.

**python setup.py bdist_wheel**
  Build a wheel distribution archive.
"""

# Standard library modules.
import codecs
import os
import re
import sys

# De-facto standard solution for Python packaging.
from setuptools import find_packages, setup

# The dependencies installed by requests[security] but expanded because
# we can't actually refer to requests[security] from extras_require.
SECURITY_REQUIREMENTS = ('pyOpenSSL>=0.14', 'cryptography>=1.3.4', 'idna>=2.0.0')


def get_contents(*args):
    """Get the contents of a file relative to the source distribution directory."""
    with codecs.open(get_absolute_path(*args), 'r', 'UTF-8') as handle:
        return handle.read()


def get_version(*args):
    """Extract the version number from a Python module."""
    contents = get_contents(*args)
    metadata = dict(re.findall('__([a-z]+)__ = [\'"]([^\'"]+)', contents))
    return metadata['version']


def get_install_requires():
    """Add conditional dependencies (when creating source distributions)."""
    install_requires = get_requirements('requirements.txt')
    if 'bdist_wheel' not in sys.argv:
        if sys.version_info[:3] < (2, 7, 9):
            install_requires.extend(SECURITY_REQUIREMENTS)
    return sorted(install_requires)


def get_extras_require():
    """Add conditional dependencies (when creating wheel distributions)."""
    extras_require = {}
    if have_environment_marker_support():
        # The following environment markers are intended to automatically pull
        # in the security requirements (but only when needed because pyOpenSSL
        # has build dependencies and I want to avoid those when possible).
        # Using rich comparisons here would break backwards compatibility [1]
        # so I went with a pragmatic / ugly / robust solution inspired by how
        # bpython solved the same problem [2].
        #
        # [1] https://www.python.org/dev/peps/pep-0426/#compatible-release-comparisons-in-environment-markers
        # [2] https://github.com/bpython/bpython/commit/1caf2430d1352a7b2645f203fc9ac252c9836f21
        expression = ':%s' % ' or '.join([
            'python_version == "2.6"',
            'python_full_version == "2.7.0"',
            'python_full_version == "2.7.1"',
            'python_full_version == "2.7.2"',
            'python_full_version == "2.7.3"',
            'python_full_version == "2.7.4"',
            'python_full_version == "2.7.5"',
            'python_full_version == "2.7.6"',
            'python_full_version == "2.7.7"',
            'python_full_version == "2.7.8"',
        ])
        extras_require[expression] = list(SECURITY_REQUIREMENTS)
    return extras_require


def get_requirements(*args):
    """Get requirements from pip requirement files."""
    requirements = set()
    contents = get_contents(*args)
    for line in contents.splitlines():
        # Strip comments.
        line = re.sub(r'^#.*|\s#.*', '', line)
        # Ignore empty lines
        if line and not line.isspace():
            requirements.add(re.sub(r'\s+', '', line))
    return sorted(requirements)


def get_absolute_path(*args):
    """Transform relative pathnames into absolute pathnames."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *args)


def have_environment_marker_support():
    """
    Check whether setuptools has support for PEP-426 environment marker support.

    Based on the ``setup.py`` script of the ``pytest`` package:
    https://bitbucket.org/pytest-dev/pytest/src/default/setup.py
    """
    try:
        from pkg_resources import parse_version
        from setuptools import __version__
        return parse_version(__version__) >= parse_version('0.7.2')
    except Exception:
        return False


setup(name='debuntu-tools',
      version=get_version('debuntu_tools', '__init__.py'),
      description="Debian and Ubuntu system administration tools",
      long_description=get_contents('README.rst'),
      url='https://debuntu-tools.readthedocs.org/',
      author="Peter Odding",
      author_email='peter@peterodding.com',
      license='MIT',
      packages=find_packages(),
      entry_points=dict(console_scripts=[
          'debuntu-kernel-manager = debuntu_tools.kernel_manager:main',
          'debuntu-nodejs-installer = debuntu_tools.nodejs_installer:main',
          'reboot-remote-system = debuntu_tools.remote_reboot:main',
          'unlock-remote-system = debuntu_tools.remote_unlock:main',
          'upgrade-remote-system = debuntu_tools.upgrade_system:main',
      ]),
      install_requires=get_install_requires(),
      extras_require=get_extras_require(),
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: Information Technology',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: MIT License',
          'Natural Language :: English',
          'Operating System :: POSIX',
          'Operating System :: POSIX :: Linux',
          'Operating System :: Unix',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: Implementation :: CPython',
          'Topic :: Software Development',
          'Topic :: Software Development :: Libraries',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System :: Systems Administration',
          'Topic :: Utilities',
      ])
