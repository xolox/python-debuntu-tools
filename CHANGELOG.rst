Changelog
=========

The purpose of this document is to list all of the notable changes to this
project. The format was inspired by `Keep a Changelog`_. This project adheres
to `semantic versioning`_.

.. contents::
   :local:

.. _Keep a Changelog: http://keepachangelog.com/
.. _semantic versioning: http://semver.org/

`Release 0.6`_ (2018-06-28)
---------------------------

- Added ``upgrade-remote-system`` program.
- Improved ``reboot-remote-system`` API (it's now possible to give a name to
  ``reboot_remote_system()`` and leave it up to that function to get the
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
- Improved ``reboot_remote_system()`` API documentation.
- Added this changelog, restructured the online documentation.
- Integrated ``property_manager.sphinx`` in online documentation.
- Added ``license='MIT'`` key to ``setup.py`` script.
- Include documentation in source distributions.
- Fixed broken reStructuredText reference in ``nodejs_installer.py``.
- Fixed unaligned reStructuredText headings.

.. _Release 0.5: https://github.com/xolox/python-debuntu-tools/compare/0.4.1...0.5

`Release 0.4.1`_ (2018-04-03)
-----------------------------

- Bug fix for unlocking in ``reboot-remote-system``.
- Set ``interactive=False`` for ``unlock-remote-system --watch --all``.
- Cleanup ``debuntu_tools.remote_unlock.main()``.

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

The initial release of `debuntu-tools` contained only the program
``debuntu-kernel-manager``. Half the value for me in creating this program was
getting to know how Debian and Ubuntu kernel image/header meta packages worked.
My initial goal was to create a safer alternative to ``sudo apt-get autoremove
--purge`` with the ultimate goal of completely automating the cleanup of old
kernel packages.

.. _Release 0.1: https://github.com/xolox/python-debuntu-tools/tree/0.1
