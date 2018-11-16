# Debian and Ubuntu system administration tools.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: November 17, 2018
# URL: https://debuntu-tools.readthedocs.io

"""The top level :mod:`debuntu_tools` module."""

# External dependencies.
from executor import ExternalCommandFailed
from verboselogs import VerboseLogger

# Public identifiers that require documentation.
__all__ = (
    '__version__',
    'logger',
    'start_interactive_shell',
)

# Semi-standard module versioning.
__version__ = '0.6.4'
"""The global version number of the `debuntu-tools` package (a string)."""

# Initialize a logger for this module.
logger = VerboseLogger(__name__)


def start_interactive_shell(context):
    """
    Start an interactive shell in the given execution context.

    :param context: An execution context created by :mod:`executor.contexts`.

    Swallows return code 130 which can be caused by the
    operator typing Control-C followed by Control-D.
    """
    try:
        context.start_interactive_shell()
    except ExternalCommandFailed as e:
        if e.returncode == 130:
            logger.notice("Ignoring return code %i from remote shell.", e.returncode)
        else:
            raise
