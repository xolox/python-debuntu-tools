#!/usr/bin/env python

# Debian and Ubuntu system administration tools.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: September 7, 2016
# URL: https://debuntu-tools.readthedocs.io

"""Setup script for the `debuntu-tools` package."""

# Standard library modules.
import codecs
import os
import re

# De-facto standard solution for Python packaging.
from setuptools import find_packages, setup


def get_contents(*args):
    """Get the contents of a file relative to the source distribution directory."""
    with codecs.open(get_absolute_path(*args), 'r', 'UTF-8') as handle:
        return handle.read()


def get_version(*args):
    """Extract the version number from a Python module."""
    contents = get_contents(*args)
    metadata = dict(re.findall('__([a-z]+)__ = [\'"]([^\'"]+)', contents))
    return metadata['version']


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


setup(name='debuntu-tools',
      version=get_version('debuntu_tools', '__init__.py'),
      description="Debian and Ubuntu system administration tools",
      long_description=get_contents('README.rst'),
      url='https://debuntu-tools.readthedocs.org/',
      author="Peter Odding",
      author_email='peter@peterodding.com',
      packages=find_packages(),
      entry_points=dict(console_scripts=[
          'debuntu-kernel-manager = debuntu_tools.kernel_manager:main',
          'debuntu-nodejs-installer = debuntu_tools.nodejs_installer:main',
      ]),
      install_requires=get_requirements('requirements.txt'),
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
