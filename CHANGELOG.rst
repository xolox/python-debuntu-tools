Changelog
=========

The purpose of this document is to list all of the notable changes to this
project. The format was inspired by `Keep a Changelog`_. This project adheres
to `semantic versioning`_.

.. contents::
   :local:

.. _Keep a Changelog: http://keepachangelog.com/
.. _semantic versioning: http://semver.org/

`Release 0.9`_ (2020-05-20)
---------------------------

**Noteworthy changes:**

- Switch from :pypi:`requests` to :pypi:`six` (``six.moves.urllib.request``).

  The ``debuntu-nodejs-installer`` program needs to make two HTTPS requests and
  until now used :pypi:`requests` to do so. However :pypi:`requests` pulls in
  quite a few dependencies (:pypi:`certifi`, :pypi:`chardet`, :pypi:`idna` and
  :pypi:`urllib3`).

  On older Python 2.7 releases :pypi:`requests` was needed to provide proper
  TLS support including SNI, however with most of the world moving on to modern
  Python releases the simple responsibility of making two HTTPS requests no
  longer warrants five dependencies...

  Besides, :pypi:`six` was already part of the transitive requirements and the
  code changes required were minimal. I also got to remove most of the
  complexity from ``setup.py``.

- Make it possible to instruct the Python API of ``upgrade-remote-system`` to
  perform a reboot regardless of whether this is required by package updates.

- Updated the usage messages embedded in the readme.

**Miscellaneous changes:**

- Update Ubuntu releases mentioned in readme.
- Update PyPI and RTD links in readme.
- Use console highlighting in readme.
- Refactored makefile (use Python 3 for local development, treat Sphinx
  warnings as errors, etc).
- Fixed existing Sphinx reference warnings.
- Bumped requirements, fixed deprecated imports.

.. _Release 0.9: https://github.com/xolox/python-debuntu-tools/compare/0.8...0.9

`Release 0.8`_ (2019-06-23)
---------------------------

- debuntu-nodejs-installer: Bump Node.js version to 10.x. This was triggered by
  the build failure at https://travis-ci.org/xolox/python-npm-accel/jobs/549226950
  which caused me to wonder why I had never bothered to update this default. So
  here it is :-).

- Bug fix for reboot-remote-system: Don't run :man:`lsblk` on regular files.

- Bug fix for reboot-remote-system: Ignore usernames in config check.

.. _Release 0.8: https://github.com/xolox/python-debuntu-tools/compare/0.7...0.8

`Release 0.7`_ (2019-04-10)
---------------------------

- Improved ``upgrade-remote-system`` (reboot when running old kernel).
- Bug fix for ``reboot-remote-system`` (always confirm SSH connectivity).
- Updated the remote root disk encryption how to (Ubuntu 18.04 compatibility).

.. _Release 0.7: https://github.com/xolox/python-debuntu-tools/compare/0.6.4...0.7

`Release 0.6.4`_ (2018-11-17)
-----------------------------

The ``debuntu-kernel-manager`` program now supports cleaning up Linux kernel
modules packages (``linux-modules-*``).

.. _Release 0.6.4: https://github.com/xolox/python-debuntu-tools/compare/0.6.3...0.6.4

`Release 0.6.3`_ (2018-10-24)
-----------------------------

Bump connection timeout of ``unlock-remote-system`` from 60 seconds to 2 minutes.

In the past months the ``reboot-remote-system`` command has failed to reboot my
Raspberry Pi in an unattended fashion in about half of my attempts, because
after the reboot command is given it takes more than 60 seconds for the
pre-boot environment to become available... 😒

Now on the one hand this is just a single use case based on crappy hardware,
and I could have just configured a longer ``connect-timeout`` in the
configuration file of course. On the other hand I do intend for tools like
``reboot-remote-system`` to be as much "do what I mean" as possible and picking
reasonable defaults is part of that.

Also I have plenty of experience with server hardware and I know that some of
those servers take more than a minute to finish initializing their hardware and
actually booting the OS, so even with fancy hardware boot times can be long 😇.

Because I didn't see the harm in bumping the ``connect-timeout`` for all users
I decided to do that instead of configuring this on my end, potentially
"obscuring a bad default". Anyone who disagrees is free to define a more
restrictive ``connect-timeout`` using a configuration file.

.. _Release 0.6.3: https://github.com/xolox/python-debuntu-tools/compare/0.6.2...0.6.3

`Release 0.6.2`_ (2018-10-24)
-----------------------------

- Improve header package detection of ``debuntu-kernel-manager``: While doing
  routine maintenance on the Raspberry Pi that handles DHCP and DNS in my home
  network I noticed that while the package ``linux-headers-4.4.0-1096-raspi2``
  was recognized the package ``linux-raspi2-headers-4.4.0-1096`` was not
  suggested for removal by ``debuntu-kernel-manager``. This is now fixed.

- I've also reduced code duplication in ``debuntu-kernel-manager``. While this
  isn't intended to change the behavior of the program I haven't gone to great
  lengths to actually verify this, however it seems to me that only in obscure
  theoretical corner cases would there be an actual observable difference in
  behavior.

.. _Release 0.6.2: https://github.com/xolox/python-debuntu-tools/compare/0.6.1...0.6.2

`Release 0.6.1`_ (2018-07-03)
-----------------------------

Bumped :pypi:`linux-utils` requirement to pull in an upstream bug fix:

- An exception was being raised by the ``upgrade-remote-system`` program (at
  the point where it calls into ``reboot-remote-system``) because the file
  ``/etc/crypttab`` didn't exist.

- However experience tells me that ``/etc/crypttab`` doesn't exist in default
  Debian and Ubuntu installations (unless that system was specifically set up
  with root disk encryption using the installation wizard).

- Furthermore this was in the code path responsible for figuring out whether a
  given system has any encrypted filesystems. Because "none" is definitely a
  valid answer, I've changed :pypi:`linux-utils` to log a notice that the file
  couldn't be found but not raise any exceptions.

.. _Release 0.6.1: https://github.com/xolox/python-debuntu-tools/compare/0.6...0.6.1

`Release 0.6`_ (2018-06-28)
---------------------------

- Added ``upgrade-remote-system`` program.
- Improved ``reboot-remote-system`` API (it's now possible to give a name to
  :func:`.reboot_remote_system()` and leave it up to that function to get the
  execution context from the configuration file).
- Documentation about remote root disk encryption on Raspberry Pi.

.. _Release 0.6: https://github.com/xolox/python-debuntu-tools/compare/0.5...0.6

`Release 0.5`_ (2018-05-26)
---------------------------

- Make it possible to interactively enter the root disk encryption password
  into an interactive prompt on the remote system, while connected over SSH.
- Added `documentation about remote root disk encryption
  <https://debuntu-tools.readthedocs.io/en/latest/unlock-remote-system.html>`_.
- Fixed a confusing typo in logging output of ``reboot-remote-system``.
- Improved :func:`.reboot_remote_system()` API documentation.
- Added this changelog, restructured the online documentation.
- Integrated :mod:`property_manager.sphinx` in online documentation.
- Added ``license='MIT'`` key to ``setup.py`` script.
- Include documentation in source distributions.
- Fixed broken reStructuredText reference in ``nodejs_installer.py``.
- Fixed unaligned reStructuredText headings.

.. _Release 0.5: https://github.com/xolox/python-debuntu-tools/compare/0.4.1...0.5

`Release 0.4.1`_ (2018-04-03)
-----------------------------

- Bug fix for unlocking in ``reboot-remote-system``.
- Set ``interactive=False`` for ``unlock-remote-system --watch --all``.
- Cleanup :func:`debuntu_tools.remote_unlock.main()`.

.. _Release 0.4.1: https://github.com/xolox/python-debuntu-tools/compare/0.4...0.4.1

`Release 0.4`_ (2018-04-01)
---------------------------

- Added the ``unlock-remote-system`` program for unattended unlocking of remote
  root disk encryption over SSH.
- Added the ``reboot-remote-system`` program for rebooting of remote systems
  (optionally with root disk encryption).

.. _Release 0.4: https://github.com/xolox/python-debuntu-tools/compare/0.3.8...0.4

`Release 0.3.8`_ (2017-07-11)
-----------------------------

- Try to improve security requirements handling.
- Changed the Sphinx theme of the online documentation.

.. _Release 0.3.8: https://github.com/xolox/python-debuntu-tools/compare/0.3.7...0.3.8

`Release 0.3.7`_ (2017-04-17)
-----------------------------

Improved package name parsing in ``debuntu-kernel-manager``.

Recently I installed the Linux kernel image meta package
``linux-image-generic-hwe-16.04`` on my Ubuntu 16.04 laptop
and since then I noticed that ``debuntu-kernel-manager``
got confused by the ``-16.04`` suffix. This is now fixed.

.. _Release 0.3.7: https://github.com/xolox/python-debuntu-tools/compare/0.3.6...0.3.7

`Release 0.3.6`_ (2017-01-18)
-----------------------------

Reduced tty usage and code duplication in ``debuntu-kernel-manager``.

.. _Release 0.3.6: https://github.com/xolox/python-debuntu-tools/compare/0.3.5...0.3.6

`Release 0.3.5`_ (2016-10-31)
-----------------------------

Expose the "kernel preserve count" in the ``debuntu-kernel-manager`` command line interface.

.. _Release 0.3.5: https://github.com/xolox/python-debuntu-tools/compare/0.3.4...0.3.5

`Release 0.3.4`_ (2016-10-31)
-----------------------------

Bug fix: Always run ``apt-auto-removal`` script with root privileges.

.. _Release 0.3.4: https://github.com/xolox/python-debuntu-tools/compare/0.3.3...0.3.4

`Release 0.3.3`_ (2016-10-25)
-----------------------------

Bug fix: Automatically update the list of auto-removable kernels after cleanup.

.. _Release 0.3.3: https://github.com/xolox/python-debuntu-tools/compare/0.3.2...0.3.3

`Release 0.3.2`_ (2016-10-25)
-----------------------------

- Bug fix: Never remove signal files when performing a dry-run.
- Simplified the ``dpkg -l`` package status handling.

.. _Release 0.3.2: https://github.com/xolox/python-debuntu-tools/compare/0.3.1...0.3.2

`Release 0.3.1`_ (2016-10-25)
-----------------------------

Bug fix: Don't complain when multiple header meta packages are installed.

.. _Release 0.3.1: https://github.com/xolox/python-debuntu-tools/compare/0.3...0.3.1

`Release 0.3`_ (2016-09-07)
---------------------------

Added the ``debuntu-nodejs-installer`` program to install Node.js from the
NodeSource binary repositories.

.. _Release 0.3: https://github.com/xolox/python-debuntu-tools/compare/0.2...0.3

`Release 0.2`_ (2016-06-23)
---------------------------

- Remove the ``/var/run/reboot-required`` file when it seems safe to do so.
- Rename ``s/collector/manager/g`` throughout the package.

.. _Release 0.2: https://github.com/xolox/python-debuntu-tools/compare/0.1...0.2

`Release 0.1`_ (2016-06-15)
---------------------------

The initial release of :pypi:`debuntu-tools` contained only the program
``debuntu-kernel-manager``. Half the value for me in creating this program was
getting to know how Debian and Ubuntu kernel image/header meta packages worked.
My initial goal was to create a safer alternative to ``sudo apt-get autoremove
--purge`` with the ultimate goal of completely automating the cleanup of old
kernel packages.

.. _Release 0.1: https://github.com/xolox/python-debuntu-tools/tree/0.1
