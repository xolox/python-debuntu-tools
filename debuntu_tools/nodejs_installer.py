# Debian and Ubuntu system administration tools.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: September 7, 2016
# URL: https://debuntu-tools.readthedocs.io

"""
Usage: debuntu-nodejs-installer [OPTIONS]

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

Supported options:

  -i, --install

    Configure the system to use one of the NodeSource binary package
    repositories and install the 'nodejs' package from the repository.

  -V, --version=NODEJS_VERSION

    Set the version of Node.js to be installed. You can find a list of
    available versions on the following web page:
    https://github.com/nodesource/distributions/

    Default: node_4.x

  -s, --sources-file=FILENAME

    Set the pathname of the 'package resource list' that will be added to the
    system during configuration of the NodeSource binary package repository.

    Default: /etc/apt/sources.list.d/nodesource.list

  -r, --remote-host=ALIAS

    Perform the requested action(s) on a remote host over SSH. The ALIAS
    argument gives the SSH alias that should be used to connect to the remote
    host.

  -v, --verbose

    Increase verbosity (can be repeated).

  -q, --quiet

    Decrease verbosity (can be repeated).

  -h, --help

    Show this message and exit.
"""

# Standard library modules.
import getopt
import logging
import sys

# External dependencies.
import coloredlogs
import requests
from apt_mirror_updater import AptMirrorUpdater
from executor import ExternalCommandFailed, quote
from executor.contexts import create_context
from humanfriendly.terminal import usage, warning
from humanfriendly.text import compact, dedent, format
from property_manager import PropertyManager, lazy_property, mutable_property, required_property
from verboselogs import VerboseLogger

# Initialize a logger for this module.
logger = VerboseLogger(__name__)


def main():
    """Command line interface for ``debuntu-nodejs-installer``."""
    # Initialize logging to the terminal and system log.
    coloredlogs.install(syslog=True)
    silence_urllib_logger()
    # Parse the command line arguments.
    action = None
    context_opts = dict()
    installer_opts = dict()
    try:
        options, arguments = getopt.getopt(sys.argv[1:], 'iV:s:r:vqh', [
            'install', 'version=', 'sources-file=',
            'remote-host=', 'verbose', 'quiet', 'help',
        ])
        for option, value in options:
            if option in ('-i', '--install'):
                action = 'install'
            elif option in ('-V', '--version'):
                installer_opts['nodejs_version'] = value
            elif option in ('-s', '--sources-file'):
                installer_opts['sources_file'] = value
            elif option in ('-r', '--remote-host'):
                context_opts['ssh_alias'] = value
            elif option in ('-v', '--verbose'):
                coloredlogs.increase_verbosity()
            elif option in ('-q', '--quiet'):
                coloredlogs.decrease_verbosity()
            elif option in ('-h', '--help'):
                usage(__doc__)
                sys.exit(0)
            else:
                raise Exception("Unhandled option!")
        if arguments:
            raise Exception("This program doesn't accept any positional arguments!")
        if not action:
            usage(__doc__)
            sys.exit(0)
    except Exception as e:
        warning("Failed to parse command line arguments! (%s)", e)
        sys.exit(1)
    # Execute the requested action.
    context = create_context(**context_opts)
    try:
        installer = NodeInstaller(
            context=context,
            **installer_opts
        )
        getattr(installer, action)()
    except (UnsupportedSystemError, ExternalCommandFailed) as e:
        logger.error("%s", e)
        sys.exit(1)
    except Exception:
        logger.exception("Encountered unexpected exception on %s!", context)
        sys.exit(1)


def silence_urllib_logger():
    """Silence useless ``INFO`` messages from the ``requests.packages.urllib3.connectionpool`` logger."""
    logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)


class NodeInstaller(PropertyManager):

    """
    Python API for the Node.js installer.

    The logic in this installer is based on the `manual installation`_
    instructions and setup scripts provided by NodeSource_ and my experience
    with system administration of Debian and Ubuntu systems.

    The main method of this class is :func:`install()` and the behavior of this
    method can be configured by setting the :attr:`context`,
    :attr:`nodejs_version` and :attr:`sources_file` properties by passing
    keyword arguments to the class initializer.

    .. _manual installation: https://github.com/nodesource/distributions#manual-installation
    """

    @required_property
    def context(self):
        """An execution context created using :mod:`executor.contexts`."""

    @mutable_property
    def nodejs_version(self):
        """The Node.js version to install (a string, defaults to ``node_4.x``)."""
        return 'node_4.x'

    @mutable_property
    def sources_file(self):
        """
        The absolute pathname of the 'package resource list' used to enable the NodeSource repositories (a string).

        Defaults to ``/etc/apt/sources.list.d/nodesource.list``.
        """
        return '/etc/apt/sources.list.d/nodesource.list'

    def install(self):
        """
        Enable the NodeSource repository and install the ``nodejs`` package.

        :raises: :exc:`UnsupportedSystemError` when :func:`validate_system()` fails.
        """
        self.validate_system()
        self.install_signing_key()
        self.install_https_transport()
        self.install_sources_file()
        self.update_package_lists()
        self.install_package()

    def validate_system(self):
        """
        Make sure the system is running a supported version of Debian or Ubuntu.

        :raises: :exc:`UnsupportedSystemError` when validation fails.
        """
        # Make sure we're dealing with a Debian or Ubuntu system.
        logger.verbose("Validating operating system distribution ..")
        if self.distributor_id.lower() not in ('debian', 'ubuntu'):
            raise UnsupportedSystemError(compact("""
                According to the output of the 'lsb_release --id' command you
                are running an unsupported operating system distribution!
                (output: {output})
            """, output=repr(self.distributor_id)))
        # Make sure we're dealing with a supported version of Debian or Ubuntu.
        base_url = format('https://deb.nodesource.com/{version}/dists/{codename}/',
                          version=self.nodejs_version, codename=self.distribution_codename.lower())
        logger.info("Validating repository availability (%s) ..", base_url)
        if not requests.get(base_url).ok:
            raise UnsupportedSystemError(compact("""
                Based on the output of the 'lsb_release --codename' command
                ({codename}) it seems that your version of {distro} isn't
                supported by NodeSource! (more specifically, it seems that
                {url} isn't available)
            """, distro=self.distributor_id, codename=self.distribution_codename, url=base_url))

    @lazy_property
    def distributor_id(self):
        """The operating system's distributor ID (a string)."""
        return self.context.capture('lsb_release', '--short', '--id')

    @lazy_property
    def distribution_codename(self):
        """The operating system distribution codename (a string)."""
        return self.context.capture('lsb_release', '--short', '--codename')

    def install_signing_key(self, key_url='https://deb.nodesource.com/gpgkey/nodesource.gpg.key'):
        """Install the signing key for the NodeSource repositories."""
        logger.info("Downloading and installing NodeSource signing key (%s) ..", key_url)
        response = requests.get(key_url, verify=True)
        response.raise_for_status()
        self.context.execute('apt-key', 'add', '-', input=response.text, sudo=True)

    def install_https_transport(self):
        """Install the ``apt-transport-https`` system package."""
        if self.context.exists('/usr/lib/apt/methods/https'):
            logger.verbose("It seems that the HTTPS transport for apt is already installed.")
        else:
            logger.info("Installing HTTPS transport support for apt ..")
            self.context.execute('apt-get', 'install', '--yes', 'apt-transport-https', sudo=True)

    def install_sources_file(self):
        """Install a 'package resource list' that points ``apt`` to the NodeSource repository."""
        logger.info("Installing package resource list (%s) ..", self.sources_file)
        sources_list = dedent('''
            # {filename}:
            # Get NodeJS binaries from the NodeSource repository.
            deb https://deb.nodesource.com/{version} {codename} main
            deb-src https://deb.nodesource.com/{version} {codename} main
        ''', filename=self.sources_file, version=self.nodejs_version, codename=self.distribution_codename)
        # TODO It would be nicer if context.write_file() accepted sudo=True!
        self.context.execute('cat > %s' % quote(self.sources_file), input=sources_list, sudo=True)

    def update_package_lists(self):
        """Run ``apt-get update`` (with compensation if things break)."""
        AptMirrorUpdater(context=self.context).smart_update()

    def install_package(self):
        """Install the Node.js package on a Debian or Ubuntu system."""
        logger.verbose("Checking for existing NodeJS package ..")
        if self.context.test('dpkg -s nodejs'):
            logger.info("Removing currently installed NodeJS package (to enable downgrading) ..")
            self.context.execute('dpkg', '--remove', '--force-depends', 'nodejs', sudo=True)
        logger.info("Installing NodeJS from the NodeSource repositories ..")
        self.context.execute('apt-get', 'install', '--yes', 'nodejs', sudo=True)


class UnsupportedSystemError(EnvironmentError):

    """Raised when an unsupported operating system is detected."""
