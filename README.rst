debuntu-tools: Debian and Ubuntu system administration tools
============================================================

The `debuntu-tools` package is my playground for experiments in automating
system administration tasks on Debian and Ubuntu Linux systems. Right now
there's just two programs and no test suite, but I intend to keep working
on this package in order make it a lot more useful. For usage instructions
please refer to following sections and the documentation_.

**Contents**

.. contents::
   :local:
   :depth: 2

Status
------

Right now `debuntu-tools` is just an experiment and as such I'm not making any
claims about or commitments towards usability, reliability or backwards
compatibility. I guess we'll see how long it's going to take me to consider
this more than an experiment :-).

Installation
------------

The `debuntu-tools` package is available on PyPI_ which means installation
should be as simple as:

.. code-block:: sh

   $ pip install debuntu-tools

There's actually a multitude of ways to install Python packages (e.g. the `per
user site-packages directory`_, `virtual environments`_ or just installing
system wide) and I have no intention of getting into that discussion here, so
if this intimidates you then read up on your options before returning to these
instructions ;-).

Requirements
~~~~~~~~~~~~

- Several Python packages are required by `debuntu-tools` but installation of
  the Python package should automatically pull in those dependencies for you.

- You need to be running a Debian or Ubuntu derived Linux distribution, or at
  least you need a functional dpkg_ installation. This enables e.g. version
  sorting according to the semantics used by dpkg_, which is quite significant
  if your goal is to remove *older* kernels but preserve *newer* ones :-).

- To actually install and remove packages you need apt-get_ and ``sudo``
  privileges on the relevant system.

Usage
-----

There are two ways to use the `debuntu-tools` package:

1. The command line interfaces which are described below.
2. The Python API which is documented on `Read the Docs`_.

The following programs are documented here:

.. contents::
   :local:
   :depth: 2

debuntu-kernel-manager
~~~~~~~~~~~~~~~~~~~~~~

.. A DRY solution to avoid duplication of the `debuntu-kernel-manager --help' text:
..
.. [[[cog
.. from humanfriendly.usage import inject_usage
.. inject_usage('debuntu_tools.kernel_manager')
.. ]]]

**Usage:** `debuntu-kernel-manager [OPTIONS] -- [APT_OPTIONS]`

Detect and remove old Linux kernel header and image packages that can be safely removed to conserve disk space and speed up apt-get runs that install or remove kernels.

By default old packages are detected and reported on the command line but no changes are made. To actually remove old packages you need to use the ``-c``, ``--clean`` or ``--remove`` option. Using the following command you can perform a dry run that shows you what will happen without actually doing it:

.. code-block:: sh

  $ debuntu-kernel-manager --remove -- --dry-run

The debuntu-kernel-manager program is currently in alpha status, which means a first attempt at a usable program has been published but there are no guarantees about what it actually does. You have been warned :-).

**Supported options:**

.. csv-table::
   :header: Option, Description
   :widths: 30, 70


   "``-c``, ``--clean``, ``--remove``","Remove Linux kernel header and/or image packages that are deemed to be safe
   to remove. The use of this option requires sudo access on the system in
   order to run the 'apt-get remove' command."
   "``-f``, ``--force``","When more than one Linux kernel meta package is installed the ``-c``, ``--clean``
   and ``--remove`` options will refuse to run apt-get and exit with an error
   instead. Use the ``-f`` or ``--force`` option to override this sanity check."
   "``-r``, ``--remote-host=ALIAS``","Detect and remove old Linux kernel header and image packages on a remote
   host over SSH. The ``ALIAS`` argument gives the SSH alias that should be used
   to connect to the remote host."
   "``-v``, ``--verbose``",Increase verbosity (can be repeated).
   "``-q``, ``--quiet``",Decrease verbosity (can be repeated).
   "``-h``, ``--help``","Show this message and exit.
   "

.. [[[end]]]

debuntu-nodejs-installer
~~~~~~~~~~~~~~~~~~~~~~~~

.. A DRY solution to avoid duplication of the `debuntu-nodejs-installer --help' text:
..
.. [[[cog
.. from humanfriendly.usage import inject_usage
.. inject_usage('debuntu_tools.nodejs_installer')
.. ]]]

**Usage:** `debuntu-nodejs-installer [OPTIONS]`

Install an up to date Node.js binary distribution on a Debian or Ubuntu system by configuring and using the NodeSource binary package repositories.

Due to the time it takes for new software releases to find their way into the Debian and Ubuntu ecosystems versus the speed with which the Node.js community is currently moving, the system packages that provide Node.js are hopelessly out of date. Fortunately the folks at NodeSource maintain Debian and Ubuntu package repositories that provide up to date Node.js binary distributions.

NodeSource makes installation scripts available and the suggested way to run these is to download and pipe them straight to a shell. That kind of rubs me the wrong way :-) but I've nevertheless had to set up NodeSource installations a dozen times now. One thing led to another and now there is this program.

**Supported options:**

.. csv-table::
   :header: Option, Description
   :widths: 30, 70


   "``-i``, ``--install``","Configure the system to use one of the NodeSource binary package
   repositories and install the 'nodejs' package from the repository."
   "``-V``, ``--version=NODEJS_VERSION``","Set the version of Node.js to be installed. You can find a list of
   available versions on the following web page:
   https://github.com/nodesource/distributions/
   
   Default: node_4.x"
   "``-s``, ``--sources-file=FILENAME``","Set the pathname of the 'package resource list' that will be added to the
   system during configuration of the NodeSource binary package repository.
   
   Default: /etc/apt/sources.list.d/nodesource.list"
   "``-r``, ``--remote-host=ALIAS``","Perform the requested action(s) on a remote host over SSH. The ``ALIAS``
   argument gives the SSH alias that should be used to connect to the remote
   host."
   "``-v``, ``--verbose``",Increase verbosity (can be repeated).
   "``-q``, ``--quiet``",Decrease verbosity (can be repeated).
   "``-h``, ``--help``","Show this message and exit.
   "

.. [[[end]]]

Contact
-------

The latest version of `debuntu-tools` is available on PyPI_ and GitHub_. The
documentation is hosted on `Read the Docs`_. For bug reports please create an
issue on GitHub_. If you have questions, suggestions, etc. feel free to send me
an e-mail at `peter@peterodding.com`_.

License
-------

This software is licensed under the `MIT license`_.

© 2016 Peter Odding.

.. External references:
.. _apt-get: https://en.wikipedia.org/wiki/apt-get
.. _documentation: https://debuntu-tools.readthedocs.io
.. _dpkg: https://en.wikipedia.org/wiki/dpkg
.. _GitHub: https://github.com/xolox/python-debuntu-tools
.. _MIT license: http://en.wikipedia.org/wiki/MIT_License
.. _per user site-packages directory: https://www.python.org/dev/peps/pep-0370/
.. _peter@peterodding.com: peter@peterodding.com
.. _PyPI: https://pypi.python.org/pypi/debuntu-tools
.. _Read the Docs: https://debuntu-tools.readthedocs.org/en/latest/#api-documentation
.. _virtual environments: http://docs.python-guide.org/en/latest/dev/virtualenvs/
