debuntu-tools: Debian and Ubuntu system administration tools
============================================================

The `debuntu-tools` package is my playground for experiments in automating
system administration tasks on Debian and Ubuntu Linux systems. Right now
there's just four programs and no test suite, but I intend to keep working
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
this more than an experiment 😊. The programs in this package have been
manually tested on and are being used to manage headless Linux servers running
Ubuntu 16.04 and 18.04.

Installation
------------

The `debuntu-tools` package is available on PyPI_ which means installation
should be as simple as:

.. code-block:: console

   $ pip install debuntu-tools

There's actually a multitude of ways to install Python packages (e.g. the `per
user site-packages directory`_, `virtual environments`_ or just installing
system wide) and I have no intention of getting into that discussion here, so
if this intimidates you then read up on your options before returning to these
instructions ;-).

Requirements
~~~~~~~~~~~~

- Several Python packages are required by debuntu-tools but installation of
  the Python package should automatically pull in those dependencies for you.

- The ``debuntu-kernel-manager`` program expects to be running on a Debian or
  Ubuntu derived Linux distribution, more specifically you need a functional
  dpkg_ installation. This enables version sorting according to the semantics
  used by dpkg_, which is quite significant if your goal is to remove *older*
  kernels but preserve *newer* ones :-). To actually install and remove kernel
  packages you need apt-get_ and sudo_ privileges on the system whose kernels
  are being managed.

- The ``unlock-remote-system`` program expects a remote Linux system that has been
  configured in such a way that the pre-boot environment (the initial ramdisk)
  enables a static IP address and starts an SSH server like dropbear_. More
  information about how to set this up is `available in the documentation
  <https://debuntu-tools.readthedocs.io/en/latest/unlock-remote-system.html>`_.

- The ``upgrade-remote-system`` builds on top of ``debuntu-kernel-manager`` as
  well as ``unlock-remote-system`` (in the form of ``reboot-remote-system``)
  and so all of the requirements above apply.

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

Detect and remove old Linux kernel header, image and modules packages that can
be safely removed to conserve disk space and speed up apt-get runs that install
or remove kernels.

By default old packages are detected and reported on the command line but no
changes are made. To actually remove old packages you need to use the ``-c``,
``--clean`` or ``--remove`` option. Using the following command you can perform
a dry run that shows you what will happen without actually doing it:

.. code-block:: sh

  $ debuntu-kernel-manager --remove -- --dry-run

The debuntu-kernel-manager program is currently in alpha status, which means
a first attempt at a usable program has been published but there are no
guarantees about what it actually does. You have been warned :-).

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
   "``-p``, ``--preserve-count=NUMBER``",Preserve the ``NUMBER`` newest versions of the kernel packages (defaults to 2).
   "``-r``, ``--remote-host=ALIAS``","Detect and remove old Linux kernel header and image packages on a remote
   host over SSH. The ``ALIAS`` argument gives the SSH alias that should be used
   to connect to the remote host."
   "``-v``, ``--verbose``",Increase verbosity (can be repeated).
   "``-q``, ``--quiet``",Decrease verbosity (can be repeated).
   "``-h``, ``--help``",Show this message and exit.

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

Install an up to date Node.js binary distribution on a Debian or Ubuntu
system by configuring and using the NodeSource binary package repositories.

Due to the time it takes for new software releases to find their way into the
Debian and Ubuntu ecosystems versus the speed with which the Node.js community
is currently moving, the system packages that provide Node.js are hopelessly
out of date. Fortunately the folks at NodeSource maintain Debian and Ubuntu
package repositories that provide up to date Node.js binary distributions.

NodeSource makes installation scripts available and the suggested way to run
these is to download and pipe them straight to a shell. That kind of rubs me
the wrong way :-) but I've nevertheless had to set up NodeSource installations
a dozen times now. One thing led to another and now there is this program.

**Supported options:**

.. csv-table::
   :header: Option, Description
   :widths: 30, 70


   "``-i``, ``--install``","Configure the system to use one of the NodeSource binary package
   repositories and install the 'nodejs' package from the repository."
   "``-V``, ``--version=NODEJS_VERSION``","Set the version of Node.js to be installed. You can find a list of
   available versions on the following web page:
   https://github.com/nodesource/distributions/
   
   Default: node_10.x (active LTS)"
   "``-s``, ``--sources-file=FILENAME``","Set the pathname of the 'package resource list' that will be added to the
   system during configuration of the NodeSource binary package repository.
   
   Default: /etc/apt/sources.list.d/nodesource.list"
   "``-r``, ``--remote-host=ALIAS``","Perform the requested action(s) on a remote host over SSH. The ``ALIAS``
   argument gives the SSH alias that should be used to connect to the remote
   host."
   "``-v``, ``--verbose``",Increase verbosity (can be repeated).
   "``-q``, ``--quiet``",Decrease verbosity (can be repeated).
   "``-h``, ``--help``",Show this message and exit.

.. [[[end]]]

reboot-remote-system
~~~~~~~~~~~~~~~~~~~~

.. A DRY solution to avoid duplication of the `reboot-remote-system --help' text:
..
.. [[[cog
.. from humanfriendly.usage import inject_usage
.. inject_usage('debuntu_tools.remote_reboot')
.. ]]]

**Usage:** `reboot-remote-system [OPTIONS] [SSH_ALIAS]`

Reboot a remote system and wait for the system to come back online. If the SSH
alias matches a section in the 'unlock-remote-system' configuration, the root disk
encryption of the remote system will be unlocked after it is rebooted.

**Supported options:**

.. csv-table::
   :header: Option, Description
   :widths: 30, 70


   "``-s``, ``--shell``","Start an interactive shell on the remote system
   after it has finished booting."
   "``-v``, ``--verbose``",Increase logging verbosity (can be repeated).
   "``-q``, ``--quiet``",Decrease logging verbosity (can be repeated).
   "``-h``, ``--help``",Show this message and exit.

.. [[[end]]]

unlock-remote-system
~~~~~~~~~~~~~~~~~~~~

.. A DRY solution to avoid duplication of the `unlock-remote-system --help' text:
..
.. [[[cog
.. from humanfriendly.usage import inject_usage
.. inject_usage('debuntu_tools.remote_unlock')
.. ]]]

**Usage:** `unlock-remote-system [OPTIONS] PRE_BOOT [POST_BOOT]`

Boot a remote Linux system that's waiting for the root disk encryption password
to be entered into an interactive prompt by connecting to the remote system
over the network using SSH and entering the password non-interactively. The
remote Linux system needs to be configured in such a way that the pre-boot
environment enables a static IP address and starts an SSH server like Dropbear.

The PRE_BOOT argument defines how to connect to the pre-boot environment:

- Its value is assumed to be a host name, IP address or SSH alias.
- It can optionally start with a username followed by an '@' sign.
- It can optionally end with a ':' followed by a port number.

The default username is 'root' and the default port number 22. The optional
POST_BOOT argument defines how to connect to the post-boot environment, this
is useful when the pre and post-boot environments run SSH servers on different
port numbers.

If the PRE_BOOT argument matches the name of a user defined configuration
section the options in that section define how unlock-remote-system operates.

**Supported options:**

.. csv-table::
   :header: Option, Description
   :widths: 30, 70


   "``-i``, ``--identity-file=KEY_FILE``","Use the private key stored in ``KEY_FILE`` for SSH connections to the pre-boot
   environment. The post-boot environment is expected to use your default
   private key or have a suitable configuration in ~/.ssh/config."
   "``-k``, ``--known-hosts=HOSTS_FILE``","Use ``HOSTS_FILE`` as the ""known hosts file"" for SSH connections to the
   pre-boot environment. When this option is not given host key verification
   will be disabled to avoid conflicts between the host keys of the different
   SSH servers running in the pre-boot and post-boot environments."
   "``-p``, ``--password=NAME``","Get the password for the root disk encryption of the remote system from
   the local password store in ~/.password-store using the 'pass' program.
   The ``NAME`` argument gives the full name of the password."
   "``-r``, ``--remote-host=SSH_ALIAS``",Connect to the remote system through an SSH proxy.
   "``-s``, ``--shell``","Start an interactive shell on the remote
   system after it has finished booting."
   "``-w``, ``--watch``","Start monitoring the remote system and automatically unlock the root disk
   encryption when the remote system is rebooted. The monitoring continues
   indefinitely."
   "``-a``, ``--all``",Enable monitoring of all configured systems when combined with ``--watch``.
   "``-v``, ``--verbose``",Increase logging verbosity (can be repeated).
   "``-q``, ``--quiet``",Decrease logging verbosity (can be repeated).
   "``-h``, ``--help``",Show this message and exit.

.. [[[end]]]

upgrade-remote-system
~~~~~~~~~~~~~~~~~~~~~

.. A DRY solution to avoid duplication of the `upgrade-remote-system --help' text:
..
.. [[[cog
.. from humanfriendly.usage import inject_usage
.. inject_usage('debuntu_tools.upgrade_system')
.. ]]]

**Usage:** `upgrade-remote-system [OPTIONS] [SSH_ALIAS]`

Upgrade the system packages on a remote Debian or Ubuntu system, reboot the
system when this is required due to security updates or because the system
isn't yet running the newest kernel, remove old Linux kernel and header
packages and optionally remove 'auto-removable' system packages.

If the given SSH alias matches a section in the 'unlock-remote-system'
configuration, the root disk encryption of the remote system will be
automatically unlocked when the system is rebooted.

**Supported options:**

.. csv-table::
   :header: Option, Description
   :widths: 30, 70


   "``-s``, ``--shell``",Start an interactive shell on the remote system afterwards.
   "``-v``, ``--verbose``",Increase logging verbosity (can be repeated).
   "``-q``, ``--quiet``",Decrease logging verbosity (can be repeated).
   "``-h``, ``--help``",Show this message and exit.

.. [[[end]]]

Configuration files
-------------------

unlock-remote-system
~~~~~~~~~~~~~~~~~~~~

.. [[[cog
.. from update_dotdee import inject_documentation
.. inject_documentation(program_name='unlock-remote-system')
.. ]]]

Configuration files are text files in the subset of `ini syntax`_ supported by
Python's configparser_ module. They can be located in the following places:

=========  ==================================  =======================================
Directory  Main configuration file             Modular configuration files
=========  ==================================  =======================================
/etc       /etc/unlock-remote-system.ini       /etc/unlock-remote-system.d/\*.ini
~          ~/.unlock-remote-system.ini         ~/.unlock-remote-system.d/\*.ini
~/.config  ~/.config/unlock-remote-system.ini  ~/.config/unlock-remote-system.d/\*.ini
=========  ==================================  =======================================

The available configuration files are loaded in the order given above, so that
user specific configuration files override system wide configuration files.

.. _configparser: https://docs.python.org/3/library/configparser.html
.. _ini syntax: https://en.wikipedia.org/wiki/INI_file

.. [[[end]]]

Each section of the configuration applies to a single host.
The following options are supported in these sections:

====================  ================================
Configuration option  Default value
====================  ================================
boot-timeout_         5 minutes
connect-timeout_      60 seconds
cryptroot-config_     ``/conf/conf.d/cryptroot``
cryptroot-program_    ``/scripts/local-top/cryptroot``
key-script_           ``/tmp/keyscript.sh``
known-hosts-file_     (no value)
named-pipe_           ``/lib/cryptsetup/passfifo``
password_             (no value)
password-name_        (no value)
password-store_       (no value)
post-boot_            (no value)
pre-boot_             (no value)
retry-interval_       1 second
scan-timeout_         5 seconds
ssh-proxy_            (no value)
====================  ================================

The links in the table above lead to the Python API documentation
which explains the purpose of each of these options.

Contact
-------

The latest version of `debuntu-tools` is available on PyPI_ and GitHub_. The
documentation is hosted on `Read the Docs`_ and includes a changelog_. For bug
reports please create an issue on GitHub_. If you have questions, suggestions,
etc. feel free to send me an e-mail at `peter@peterodding.com`_.

License
-------

This software is licensed under the `MIT license`_.

© 2018 Peter Odding.

.. _apt-get: https://manpages.debian.org/apt-get
.. _boot-timeout: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.boot_timeout
.. _changelog: https://debuntu-tools.readthedocs.io/en/latest/changelog.html
.. _connect-timeout: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.connect_timeout
.. _cryptroot-config: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.cryptroot_config
.. _cryptroot-program: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.cryptroot_program
.. _documentation: https://debuntu-tools.readthedocs.io
.. _dpkg: https://manpages.debian.org/dpkg
.. _dropbear: https://manpages.debian.org/dropbear
.. _GitHub: https://github.com/xolox/python-debuntu-tools
.. _key-script: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.key_script
.. _known-hosts-file: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.known_hosts_file
.. _MIT license: http://en.wikipedia.org/wiki/MIT_License
.. _named-pipe: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.named_pipe
.. _password-name: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.password
.. _password-store: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.password
.. _password: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.password
.. _per user site-packages directory: https://www.python.org/dev/peps/pep-0370/
.. _peter@peterodding.com: peter@peterodding.com
.. _post-boot: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.post_boot
.. _pre-boot: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.pre_boot
.. _PyPI: https://pypi.org/project/debuntu-tools
.. _Read the Docs: https://debuntu-tools.readthedocs.io/en/latest/#api-documentation
.. _retry-interval: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.retry_interval
.. _scan-timeout: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.scan_timeout
.. _ssh-proxy: https://debuntu-tools.readthedocs.io/en/latest/api.html#debuntu_tools.remote_unlock.EncryptedSystem.ssh_proxy
.. _sudo: https://manpages.debian.org/sudo
.. _virtual environments: http://docs.python-guide.org/en/latest/dev/virtualenvs/
