# Debian and Ubuntu system administration tools.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 27, 2018
# URL: https://debuntu-tools.readthedocs.io

"""
Usage: upgrade-remote-system [OPTIONS] [SSH_ALIAS]

Upgrade the system packages on a remote Debian or Ubuntu system, reboot the
system if required due to security updates, remove old Linux kernel and header
packages and optionally remove 'auto-removable' system packages.

If the given SSH alias matches a section in the 'unlock-remote-system'
configuration, the root disk encryption of the remote system will be
automatically unlocked when the system is rebooted.

Supported options:

  -s, --shell

    Start an interactive shell on the remote system afterwards.

  -v, --verbose

    Increase logging verbosity (can be repeated).

  -q, --quiet

    Decrease logging verbosity (can be repeated).

  -h, --help

    Show this message and exit.
"""

# Standard library modules.
import getopt
import sys

# External dependencies.
import coloredlogs
from apt_mirror_updater import AptMirrorUpdater
from humanfriendly.terminal import usage, warning
from executor.contexts import RemoteContext
from verboselogs import VerboseLogger

# Modules included in our package.
from debuntu_tools import start_interactive_shell
from debuntu_tools.kernel_manager import REBOOT_REQUIRED_FILE, KernelPackageManager, CleanupError
from debuntu_tools.remote_reboot import reboot_remote_system

# Initialize a logger for this module.
logger = VerboseLogger(__name__)


def main():
    """Command line interface for ``upgrade-remote-system``."""
    # Initialize logging to the terminal and system log.
    coloredlogs.install(syslog=True)
    # Parse the command line arguments.
    do_shell = False
    try:
        options, arguments = getopt.gnu_getopt(sys.argv[1:], 'svqh', [
            'shell', 'verbose', 'quiet', 'help',
        ])
        for option, value in options:
            if option in ('-s', '--shell'):
                do_shell = True
            elif option in ('-v', '--verbose'):
                coloredlogs.increase_verbosity()
            elif option in ('-q', '--quiet'):
                coloredlogs.decrease_verbosity()
            elif option in ('-h', '--help'):
                usage(__doc__)
                sys.exit(0)
            else:
                raise Exception("Unhandled option!")
        if not arguments:
            usage(__doc__)
            sys.exit(0)
        elif len(arguments) > 1:
            raise Exception("only one positional argument allowed")
    except Exception as e:
        warning("Failed to parse command line arguments! (%s)", e)
        sys.exit(1)
    # Upgrade the remote system.
    try:
        context = RemoteContext(ssh_alias=arguments[0])
        upgrade_remote_system(context)
        if do_shell:
            start_interactive_shell(context)
    except Exception:
        logger.exception("Aborting due to unexpected exception!")
        sys.exit(2)


def upgrade_remote_system(context):
    """
    Perform standard system maintenance tasks on a remote Debian or Ubuntu system.

    :param context: An execution context created by :mod:`executor.contexts`.

    This function performs the following system maintenance tasks:

    1. The ``apt-get update`` command is run (using the Python API of the
       ``apt-mirror-updater`` program, see :mod:`apt_mirror_updater`).
    2. The ``apt-get dist-upgrade`` command is run [1]_.
    3. The ``apt-get clean`` command is run.
    4. If the file ``/var/run/reboot-required`` exists (indicating that a
       reboot is required due to security updates) the remote system is
       rebooted using the Python API of the ``reboot-remote-system`` program,
       to enable automatic unlocking of remote root disk encryption.
    5. Old kernel packages are removed (using the Python API of the
       ``debuntu-kernel-manager`` program). If more than one meta package is
       installed a warning message is logged but no exception is raised.
    6. The ``apt-get autoremove --purge`` command is run to optionally [1]_
       remove any 'auto-removable' system packages.

    .. [1] Because the ``apt-get`` option ``--yes`` is not used, the operator
           will be asked to confirm using an interactive confirmation prompt.
    """
    # Run 'apt-get update' (with compensation if things break).
    updater = AptMirrorUpdater(context=context)
    updater.smart_update()
    # Run 'apt-get dist-upgrade'.
    logger.info("Upgrading system packages on %s ..", context)
    context.execute('apt-get', 'dist-upgrade', sudo=True, tty=True)
    # Run 'apt-get clean'.
    logger.info("Cleaning up downloaded archives on %s ..", context)
    context.execute('apt-get', 'clean', sudo=True)
    # Reboot if required due to security updates.
    if context.exists(REBOOT_REQUIRED_FILE):
        logger.info("Rebooting %s (required due to security updates).", context)
        reboot_remote_system(context=context)
    # Cleanup old kernel packages (after rebooting, so that we're running on the newest kernel).
    manager = KernelPackageManager(
        apt_options=['--yes'],
        context=context,
    )
    try:
        manager.cleanup_packages()
    except CleanupError as e:
        # Don't error out when multiple meta packages are installed.
        logger.warning(e)
    # Prompt to remove packages that seem to no longer be needed.
    logger.info("Removing 'auto-removable' system packages ..")
    context.execute('apt-get', 'autoremove', '--purge', sudo=True, tty=True)
    logger.info("Done!")
