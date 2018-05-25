# Debian and Ubuntu system administration tools.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: May 25, 2018
# URL: https://debuntu-tools.readthedocs.io

"""
Usage: reboot-remote-system [OPTIONS] [SSH_ALIAS]

Reboot a remote system and wait for the system to come back online. If the SSH
alias matches a section in the 'unlock-remote-system' configuration, the root disk
encryption of the remote system will be unlocked after it is rebooted.

Supported options:

  -s, --shell

    Start an interactive shell on the remote system
    after it has finished booting.

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
import time

# External dependencies.
import coloredlogs
from humanfriendly import Timer, compact, format_timespan
from humanfriendly.terminal import usage, warning
from executor.contexts import RemoteContext
from executor.ssh.client import RemoteConnectFailed
from linux_utils.crypttab import parse_crypttab
from update_dotdee import ConfigLoader
from verboselogs import VerboseLogger

# Modules included in our package.
from debuntu_tools import start_interactive_shell
from debuntu_tools.remote_unlock import EncryptedSystemError, EncryptedSystem

# Initialize a logger for this module.
logger = VerboseLogger(__name__)


def main():
    """Command line interface for ``reboot-remote-system``."""
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
    # Reboot the remote system.
    try:
        context = RemoteContext(ssh_alias=arguments[0])
        reboot_remote_system(context)
        if do_shell:
            start_interactive_shell(context)
    except EncryptedSystemError as e:
        logger.error("Aborting due to error: %s", e)
        sys.exit(2)
    except Exception:
        logger.exception("Aborting due to unexpected exception!")
        sys.exit(3)


def reboot_remote_system(context):
    """
    Reboot a remote Linux system (unattended).

    :param context: A :class:`~executor.contexts.RemoteContext` object.
    :raises: :exc:`~exceptions.ValueError` when the remote system appears to be
             using root disk encryption but there's no ``unlock-remote-system``
             configuration section available. The reasoning behind this is to
             err on the side of caution when we suspect we won't be able to get
             the remote system back online.

    This function reboots a remote Linux system, waits for the system to go
    down and then waits for it to come back up.

    If the :attr:`~executor.ssh.client.RemoteAccount.ssh_alias` of the context
    matches a section in the `unlock-remote-system` configuration, the root disk
    encryption of the remote system will be unlocked after it is rebooted.
    """
    timer = Timer()
    # Sanity check the execution context.
    if not isinstance(context, RemoteContext):
        msg = "Expected a RemoteContext object, got %s instead!"
        raise TypeError(msg % type(context))
    logger.info("Preparing to reboot %s ..", context)
    # Check if the name matches a configuration section.
    loader = ConfigLoader(program_name='unlock-remote-system')
    have_config = (context.ssh_alias in loader.section_names)
    # Check if the remote system is using root disk encryption.
    needs_unlock = is_encrypted(context)
    # Refuse to reboot if we can't get the system back online.
    if needs_unlock and not have_config:
        raise ValueError(compact("""
            It looks like the {context} is using root disk encryption but
            there's no configuration defined for this system! Refusing to
            reboot the system because we won't be able to unlock it.
        """, context=context))
    # Get the current uptime of the remote system.
    old_uptime = get_uptime(context)
    logger.info("Rebooting after %s of uptime ..", format_timespan(old_uptime))
    # Issue the `reboot' command.
    try:
        context.execute('reboot', shell=False, silent=True, sudo=True)
    except RemoteConnectFailed:
        logger.notice(compact("""
            While issuing the `reboot' command the SSH client reported dropping
            the connection. We will proceed under the assumption that this was
            caused by the remote SSH server being shut down as a result of the
            `reboot' command.
        """))
    # Wait for the system to have been rebooted.
    if have_config:
        # Unlock the root disk encryption.
        options = dict(
            config_loader=loader,
            config_section=context.ssh_alias,
        )
        with EncryptedSystem(**options) as program:
            program.unlock_system()
    else:
        # Wait for a successful SSH connection to report a lower uptime.
        logger.info("Waiting for %s to come back online ..", context)
        while True:
            try:
                new_uptime = get_uptime(context)
                if old_uptime > new_uptime:
                    break
                else:
                    time.sleep(1)
            except RemoteConnectFailed:
                time.sleep(0.1)
        logger.success("Took %s to reboot %s.", timer, context)


def get_uptime(context):
    """
    Get the uptime of a remote system.

    :param context: An execution context created by :mod:`executor.contexts`.
    :returns: The uptime of the remote system (as a :class:`float`).

    This function is used by :func:`reboot_remote_system()` to
    wait until a remote system has been successfully rebooted.
    """
    contents = context.capture('cat', '/proc/uptime', silent=True)
    return next(float(t) for t in contents.split())


def is_encrypted(context):
    """
    Detect whether a remote system is using root disk encryption.

    :param context: A :class:`~executor.contexts.RemoteContext` object.
    :returns: :data:`True` if root disk encryption is being used,
              :data:`False` otherwise.
    """
    logger.info("Checking root disk encryption on %s ..", context)
    for entry in parse_crypttab(context=context):
        logger.verbose("Checking if %s contains root filesystem ..", entry.source_device)
        listing = context.capture('lsblk', entry.source_device)
        if '/' in listing.split():
            logger.info("Yes it looks like the system is using root disk encryption.")
            return True
    logger.info("No it doesn't look like the system is using root disk encryption.")
    return False
