# Debian and Ubuntu system administration tools.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: October 24, 2018
# URL: https://debuntu-tools.readthedocs.io

"""
Usage: unlock-remote-system [OPTIONS] PRE_BOOT [POST_BOOT]

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

Supported options:

  -i, --identity-file=KEY_FILE

    Use the private key stored in KEY_FILE for SSH connections to the pre-boot
    environment. The post-boot environment is expected to use your default
    private key or have a suitable configuration in ~/.ssh/config.

  -k, --known-hosts=HOSTS_FILE

    Use HOSTS_FILE as the "known hosts file" for SSH connections to the
    pre-boot environment. When this option is not given host key verification
    will be disabled to avoid conflicts between the host keys of the different
    SSH servers running in the pre-boot and post-boot environments.

  -p, --password=NAME

    Get the password for the root disk encryption of the remote system from
    the local password store in ~/.password-store using the 'pass' program.
    The NAME argument gives the full name of the password.

  -r, --remote-host=SSH_ALIAS

    Connect to the remote system through an SSH proxy.

  -s, --shell

    Start an interactive shell on the remote
    system after it has finished booting.

  -w, --watch

    Start monitoring the remote system and automatically unlock the root disk
    encryption when the remote system is rebooted. The monitoring continues
    indefinitely.

  -a, --all

    Enable monitoring of all configured systems when combined with --watch.

  -v, --verbose

    Increase logging verbosity (can be repeated).

  -q, --quiet

    Decrease logging verbosity (can be repeated).

  -h, --help

    Show this message and exit.
"""

# Standard library modules.
import getopt
import getpass
import multiprocessing
import os
import pwd
import re
import shutil
import sys
import tempfile
import time

# External dependencies.
import coloredlogs
from executor import ExternalCommandFailed, execute, quote
from executor.contexts import LocalContext, RemoteContext
from executor.ssh.client import RemoteConnectFailed, SSH_PROGRAM_NAME
from humanfriendly import (
    AutomaticSpinner,
    Timer,
    compact,
    format,
    format_timespan,
    parse_path,
    parse_timespan,
    pluralize,
)
from humanfriendly.prompts import prompt_for_confirmation
from humanfriendly.terminal import connected_to_terminal, usage, warning
from property_manager import (
    PropertyManager,
    key_property,
    lazy_property,
    mutable_property,
    required_property,
)
from six.moves import configparser
from update_dotdee import ConfigLoader
from verboselogs import VerboseLogger

# Modules included in our package.
from debuntu_tools import start_interactive_shell

EXPRESSION_PATTERN = re.compile('''
    ^ ( (?P<user> [^@]+ ) @ )?
    (?P<host> .+? )
    ( : (?P<port> \d+ ) )? $
''', re.VERBOSE)
"""A compiled regular expression pattern to parse connection profile expressions."""

HOST_KEYS_FILE = '~/.config/unlock-remote-system.d/known-hosts.ini'
"""The configuration file that's used to store SSH host keys (a string)."""

# Public identifiers that require documentation.
__all__ = (
    'BootTimeoutError',
    'ConnectionProfile',
    'EXPRESSION_PATTERN',
    'EncryptedSystem',
    'EncryptedSystemError',
    'HOST_KEYS_FILE',
    'ServerDetails',
    'SystemUnreachableError',
    'UnlockAbortedError',
    'UnsupportedSystemError',
    'find_local_username',
    'get_password_from_store',
    'logger',
    'main',
    'prompt_for_password',
)

# Initialize a logger for this module.
logger = VerboseLogger(__name__)


def main():
    """Command line interface for ``unlock-remote-system``."""
    # Initialize logging to the terminal and system log.
    coloredlogs.install(syslog=True)
    # Parse the command line arguments.
    program_opts = {}
    identity_file = None
    do_shell = False
    do_watch = False
    watch_all = False
    try:
        options, arguments = getopt.gnu_getopt(sys.argv[1:], 'i:k:p:r:swavqh', [
            'identity-file=', 'known-hosts=', 'password=', 'remote-host=',
            'shell', 'watch', 'all', 'verbose', 'quiet', 'help',
        ])
        for option, value in options:
            if option in ('-i', '--identity-file'):
                identity_file = parse_path(value)
            elif option in ('-k', '--known-hosts'):
                program_opts['known_hosts_file'] = parse_path(value)
            elif option in ('-p', '--password'):
                program_opts['password'] = get_password_from_store(value)
            elif option in ('-r', '--remote-host'):
                program_opts['ssh_proxy'] = value
            elif option in ('-s', '--shell'):
                do_shell = True
            elif option in ('-w', '--watch'):
                do_watch = True
            elif option in ('-a', '--all'):
                watch_all = True
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
        elif len(arguments) > 2:
            raise Exception("only two positional arguments allowed")
        # Create a ConfigLoader object and prepare to pass it to the program to
        # avoid scanning for configuration files more than once (which isn't a
        # real problem but does generate somewhat confusing log output).
        loader = ConfigLoader(program_name='unlock-remote-system')
        program_opts['config_loader'] = loader
        # Check if a single positional argument was given that matches the name
        # of a user defined configuration section.
        if len(arguments) == 1 and arguments[0] in loader.section_names:
            logger.info("Loading configuration section '%s' ..", arguments[0])
            program_opts['config_section'] = arguments[0]
        else:
            # The SSH connection profile of the pre-boot environment
            # is given as the first positional argument.
            program_opts['pre_boot'] = ConnectionProfile(expression=arguments[0], identity_file=identity_file)
            # The SSH connection profile of the post-boot environment
            # can be given as the second positional argument, otherwise
            # it will be inferred from the connection profile of
            # the pre-boot environment.
            if len(arguments) == 2:
                program_opts['post_boot'] = ConnectionProfile(expression=arguments[1])
            else:
                # By default we don't use root to login to the post-boot environment.
                program_opts['post_boot'] = ConnectionProfile(expression=arguments[0])
                program_opts['post_boot'].username = find_local_username()
            # Prompt the operator to enter the disk encryption password for the remote host?
            if not program_opts.get('password'):
                program_opts['password'] = prompt_for_password(program_opts['pre_boot'].hostname)
    except Exception as e:
        warning("Failed to parse command line arguments! (%s)", e)
        sys.exit(1)
    # Try to unlock the remote system.
    try:
        if do_watch and watch_all:
            watch_all_systems(loader)
        else:
            with EncryptedSystem(**program_opts) as program:
                if do_watch:
                    program.watch_system()
                else:
                    program.unlock_system()
                    if do_shell:
                        start_interactive_shell(program.post_context)
    except EncryptedSystemError as e:
        logger.error("Aborting due to error: %s", e)
        sys.exit(2)
    except Exception:
        logger.exception("Aborting due to unexpected exception!")
        sys.exit(3)


def find_local_username():
    """Find the username of the current user on the local system."""
    for name in 'USER', 'LOGNAME':
        if os.environ.get(name):
            return os.environ[name]
    entry = pwd.getpwuid(os.getuid())
    return entry.pw_name


def get_password_from_store(name, store=None):
    """Get the disk encryption password from the 'pass' program."""
    options = dict(capture=True, shell=False, tty=True)
    options['environment'] = dict(GPG_TTY=execute('tty', **options))
    if store:
        options['environment']['PASSWORD_STORE_DIR'] = parse_path(store)
    output = execute('pass', 'show', name, **options)
    lines = output.splitlines()
    if lines and lines[0]:
        return lines[0]
    else:
        logger.warning("Failed to get disk encryption password using 'pass' program!")


def prompt_for_password(hostname):
    """Prompt the operator to interactively enter the disk encryption password."""
    prompt_text = "Enter disk encryption password for '%s': "
    return getpass.getpass(prompt_text % hostname)


def watch_all_systems(loader):
    """
    Spawn :mod:`multiprocessing` workers to monitor all configured systems.

    :param loader: A :class:`~update_dotdee.ConfigLoader` object.
    """
    pool = multiprocessing.Pool(len(loader.section_names))
    try:
        pool.map(watch_worker, loader.section_names)
    finally:
        pool.terminate()


def watch_worker(name):
    """
    A :mod:`multiprocessing` worker used by :func:`watch_all_systems()`.

    :param name: The value for :attr:`~EncryptedSystem.config_section` (a string).

    The :class:`EncryptedSystem` object is initialized with
    :attr:`~EncryptedSystem.config_section` set to `name` and
    :attr:`~EncryptedSystem.interactive` set to :data:`False`.
    """
    options = dict(
        config_section=name,
        interactive=False,
    )
    with EncryptedSystem(**options) as program:
        program.watch_system()


class EncryptedSystem(PropertyManager):

    """
    Python API for the `unlock-remote-system` program.

    This class implements a Python API for remote unlocking of Linux systems
    with root disk encryption over SSH. The internals of this class
    differentiate between the pre-boot and post-boot environments:

    - The :attr:`pre_boot` and :attr:`post_boot` properties are :class:`ConnectionProfile`
      objects that define how to connect to the SSH server in the pre-boot environment
      (usually this is Dropbear running in the initial ram disk) and the SSH
      server in the post-boot environment (usually this is OpenSSH).

    - The :attr:`pre_context` and :attr:`post_context` properties are
      :class:`~executor.contexts.RemoteContext` objects that enable command
      execution in the pre-boot and post-boot environments. The values of these
      properties are created based on the corresponding connection profiles.

    - In addition to the command execution contexts for the pre-boot and
      post-boot environments there is the :attr:`context` property which
      provides a command execution context for commands outside of the remote
      system. This defaults to the local system on which `unlock-remote-system` is
      running but will be a remote system when :attr:`ssh_proxy` is set.
    """

    @mutable_property(cached=True)
    def boot_timeout(self):
        """The number of seconds to wait for the system to boot (a number, defaults to 5 minutes)."""
        return int(parse_timespan(self.config.get('boot-timeout', '5m')))

    @lazy_property
    def config(self):
        """
        A dictionary with configuration options.

        See also :attr:`config` and :attr:`config_section`.
        """
        if self.config_section:
            if self.config_section in self.config_loader.section_names:
                return self.config_loader.get_options(self.config_section)
        return {}

    @mutable_property(cached=True)
    def config_loader(self):
        """
        A :class:`~update_dotdee.ConfigLoader` object.

        See also :attr:`config` and :attr:`config_section`.
        """
        return ConfigLoader(program_name='unlock-remote-system')

    @mutable_property
    def config_section(self):
        """
        The configuration section to use (a string or :data:`None`).

        When this option is set :attr:`config` can be loaded and
        :func:`store_host_keys()` can persist SSH host keys.

        See also :attr:`config` and :attr:`config_loader`.
        """

    @mutable_property(cached=True)
    def connect_timeout(self):
        """How long to wait for the system to become reachable (an integer, defaults to 2 minutes)."""
        return int(parse_timespan(self.config.get('connect-timeout', '2m')))

    @lazy_property
    def context(self):
        """
        The command execution context from which the remote system is being controlled.

        The computed value of this property is a command execution context
        created by :mod:`executor.contexts`. When :attr:`ssh_proxy` is set this
        will be a :class:`~executor.contexts.RemoteContext` object, otherwise
        it will be a :class:`~executor.contexts.LocalContext` object.
        """
        return RemoteContext(ssh_alias=self.ssh_proxy) if self.ssh_proxy else LocalContext()

    @mutable_property
    def control_directory(self):
        """A temporary directory for SSH control sockets (a string)."""
        raise Exception("You need to use EncryptedSystem as a context manager!")

    @mutable_property
    def cryptroot_config(self):
        """
        The pathname of the 'cryptroot' configuration file (a string).

        The value of this property sets the pathname of the 'cryptroot'
        configuration file in the pre-boot environment (the initial ram disk).
        It defaults to '/conf/conf.d/cryptroot'.
        """
        return self.config.get('cryptroot-config', '/conf/conf.d/cryptroot')

    @mutable_property
    def cryptroot_program(self):
        """
        The pathname of the 'cryptroot' program (a string).

        The value of this property sets the pathname of the 'cryptroot' program
        in the pre-boot environment (the initial ram disk). It defaults to
        '/scripts/local-top/cryptroot'.
        """
        return self.config.get('cryptroot-program', '/scripts/local-top/cryptroot')

    @property
    def have_cryptroot_config(self):
        """
        :data:`True` if :attr:`cryptroot_config` exists, :data:`False` otherwise.

        The existence of the ``/conf/conf.d/cryptroot`` configuration file is
        taken as confirmation that the remote system is currently in its
        pre-boot environment (initial ram disk).
        """
        logger.info("Checking if configuration is available (%s) ..", self.cryptroot_config)
        return self.pre_context.is_file(self.cryptroot_config)

    @property
    def have_cryptroot_program(self):
        """:data:`True` if :attr:`cryptroot_program` exists, :data:`False` otherwise."""
        logger.info("Checking if program is available (%s) ..", self.cryptroot_program)
        return self.pre_context.is_file(self.cryptroot_program)

    @property
    def have_named_pipe(self):
        """
        :data:`True` if :attr:`named_pipe` exists, :data:`False` otherwise.

        The named pipe configured by the :attr:`named_pipe` property provides a
        simple and robust way to inject the root disk encryption pass phrase
        into the boot sequence. When the named pipe is available it will be
        used as the preferred method.

        In my experience this works on Ubuntu 16.04 but it doesn't work on
        Ubuntu 14.04 (because the named pipe doesn't exist).
        """
        logger.info("Checking if named pipe is available (%s) ..", self.named_pipe)
        return self.pre_context.test('test', '-p', self.named_pipe)

    @mutable_property(cached=True)
    def interactive(self):
        """
        :data:`True` to allow user interaction, :data:`False` otherwise.

        The value of :attr:`interactive` defaults to the return value
        of :func:`~humanfriendly.terminal.connected_to_terminal()`
        when given :data:`sys.stdin`.
        """
        return connected_to_terminal(sys.stdin)

    @mutable_property
    def key_script(self):
        """The pathname of the generated key script (defaults to ``'/tmp/keyscript.sh'``)."""
        return self.config.get('key-script', '/tmp/keyscript.sh')

    @mutable_property
    def known_hosts_file(self):
        """The filename of the "known hosts file" to use (a string or :data:`None`)."""
        return self.config.get('known-hosts-file')

    @mutable_property
    def named_pipe(self):
        """
        The pathname of the named pipe used by cryptsetup_ (a string).

        The value of this property sets the pathname of the named pipe used by
        cryptsetup_ in the pre-boot environment (the initial ram disk). It
        defaults to '/lib/cryptsetup/passfifo'.

        .. _cryptsetup: https://manpages.debian.org/cryptsetup
        """
        return self.config.get('named-pipe', '/lib/cryptsetup/passfifo')

    @mutable_property(cached=True, repr=False)
    def password(self):
        """
        The password that unlocks the root filesystem of the remote host (a string or :data:`None`).

        If the configuration section contains the option `password-name` then
        :func:`get_password_from_store()` will be used to get the password by
        executing the ``pass`` program.

        The optional configuration option `password-store` can be used to set
        the ``$PASSWORD_STORE_DIR`` environment variable.
        """
        if 'password' in self.config:
            return self.config['password']
        elif 'password-name' in self.config:
            return get_password_from_store(
                name=self.config['password-name'],
                store=self.config.get('password-store'),
            )

    @required_property(cached=True)
    def post_boot(self):
        """A connection profile for the post-boot environment (a :class:`ConnectionProfile` object)."""
        if self.config_section or 'post-boot' in self.config:
            return ConnectionProfile(expression=self.config.get('post-boot', self.config_section))

    @lazy_property
    def post_context(self):
        """
        A command execution context for the post-boot environment.

        The computed value of this property is a command execution context
        created by :mod:`executor.contexts`, more specifically it's a
        :class:`~executor.contexts.RemoteContext` object.
        """
        return RemoteContext(
            identity_file=self.post_boot.identity_file,
            port=self.post_boot.port_number,
            ssh_alias=self.post_boot.hostname,
            ssh_user=self.post_boot.username,
            tty=False,
        )

    @required_property
    def pre_boot(self):
        """A connection profile for the pre-boot environment (a :class:`ConnectionProfile` object)."""
        if self.config_section or 'pre-boot' in self.config:
            return ConnectionProfile(
                expression=self.config.get('pre-boot', self.config_section),
                identity_file=(
                    parse_path(self.config['identity-file'])
                    if 'identity-file' in self.config else None
                ),
                username='root',
            )

    @lazy_property
    def pre_context(self):
        """
        The command execution context inside the pre-boot environment.

        The computed value of this property is a command execution context
        created by :mod:`executor.contexts`, more specifically it's a
        :class:`~executor.contexts.RemoteContext` object.
        """
        # Prepare the remote context options.
        options = dict(
            identity_file=self.pre_boot.identity_file,
            port=self.pre_boot.port_number,
            shell=False,
            ssh_alias=self.pre_boot.hostname,
            ssh_command=[
                SSH_PROGRAM_NAME,
                '-o', 'ControlMaster=auto',
                '-o', 'ControlPersist=60',
                '-o', format('ControlPath={d}/%r@%h:%p', d=self.control_directory),
            ],
            ssh_user=self.pre_boot.username,
            tty=False,
        )
        # Use the configured SSH proxy?
        if self.ssh_proxy:
            options['ssh_command'].extend((
                '-o', format('ProxyCommand=ssh %s -W %s:%i',
                             quote(self.ssh_proxy),
                             quote(self.pre_boot.hostname),
                             self.pre_boot.port_number)
            ))
        # Decide what to do about the `known_hosts' file.
        if self.known_hosts_file:
            options['known_hosts_file'] = self.known_hosts_file
        else:
            options['ignore_known_hosts'] = True
        # Create the remote context object.
        return RemoteContext(**options)

    @mutable_property(cached=True)
    def retry_interval(self):
        """The time between connection attempts (an integer, defaults to 1 second)."""
        return int(parse_timespan(self.config.get('retry-interval', '1s')))

    @mutable_property(cached=True)
    def scan_timeout(self):
        """The timeout for ssh-keyscan_ (an integer, defaults to 5 seconds)."""
        return int(parse_timespan(self.config.get('scan-timeout', '5s')))

    @mutable_property
    def ssh_proxy(self):
        """The SSH alias of a proxy to the remote system (a string or :data:`None`)."""
        return self.config.get('ssh-proxy')

    @mutable_property(cached=True)
    def watch_interval(self):
        """The time between pre-boot environment checks (an integer, defaults to 60 seconds)."""
        return int(parse_timespan(self.config.get('watch-interval', '1m')))

    def __enter__(self):
        """Prepare :attr:`control_directory`."""
        self.control_directory = tempfile.mkdtemp()
        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        """Cleanup :attr:`control_directory`."""
        shutil.rmtree(self.control_directory)
        delattr(self, 'control_directory')

    def check_ssh_connection(self):
        """Verify SSH connectivity to the pre-boot environment."""
        if self.test_ssh_connection(self.pre_boot, self.pre_context):
            logger.info("Successfully connected and authenticated over SSH.")
        else:
            msg = format(
                "Failed to authenticate to %s:%i!",
                self.pre_boot.hostname,
                self.pre_boot.port_number,
            )
            if self.pre_boot.username == 'root':
                msg += " " + compact("""
                    Maybe you're accidentally connecting to the post-boot
                    environment and you don't have 'root' access there?
                """)
            raise SystemUnreachableError(msg)

    def create_key_script(self):
        """
        Create a key script in the pre-boot environment (initial ram disk).

        This method creates a minimal key script (a shell script containing a
        single ``echo`` command) in the pre-boot environment and modifies the
        :attr:`cryptroot_config` file so that the key script is used to unlock
        the root disk.
        """
        logger.info("Creating key script: %s", self.key_script)
        self.write_file(self.key_script, 'echo -n %s\n' % quote(self.password))
        self.pre_context.execute('chmod', '700', self.key_script)
        logger.info("Updating configuration file: %s", self.cryptroot_config)
        contents = self.pre_context.read_file(self.cryptroot_config)
        self.write_file(self.cryptroot_config, ''.join(
            '%s,keyscript=%s\n' % (line.strip(), self.key_script)
            for line in contents.splitlines()
        ))

    def find_process_id(self, program, **options):
        """
        Determine the process id of a program or script in the pre-boot environment.

        :param program: The name of a program or script (a string).
        :returns: A process id (an integer) or :data:`None`.
        """
        logger.verbose("Looking for process id of '%s' ..", program)
        listing = self.pre_context.capture('ps', **options)
        for line in listing.splitlines():
            tokens = line.split()
            logger.debug("Parsing entry in 'ps' output: %s", tokens)
            if len(tokens) > 1 and tokens[0].isdigit():
                pid = int(tokens[0])
                if program in tokens and pid != 1:
                    logger.verbose("Matched process id %i.", pid)
                    return pid

    def get_known_host_keys(self, option_name):
        """
        Get the configured SSH host keys.

        :param option_name: The name of the configuration option
                            that holds known host keys (a string).
        :returns: A :class:`set` of strings.
        """
        return set(self.config.get(option_name, '').split())

    def kill_emergency_shell(self):
        """Kill the emergency shell process to resume the boot process."""
        logger.info("Looking for emergency shell process (/bin/sh -i) ..")
        pid = self.find_process_id('/bin/sh', check=False)
        if pid:
            logger.info("Killing emergency shell with process id %i ..", pid)
            try:
                self.pre_context.execute('kill', '-9', str(pid))
            except ExternalCommandFailed as e:
                if isinstance(e, RemoteConnectFailed):
                    raise
        # Warn the operator if we fail to identify and kill the emergency
        # shell process, but continue (as opposed to aborting) in the hope
        # that there is no interactive prompt or its not blocking.
        logger.notice(compact("""
            Failed to identify and kill the emergency shell process.
            Booting of the remote system may block until the emergency
            shell is terminated, in this case manual intervention will
            be required.
        """))

    def kill_interactive_prompt(self):
        """Kill the process responsible for the interactive prompt in the pre-boot environment."""
        logger.info("Looking for '%s' process ..", self.cryptroot_program)
        pid = self.find_process_id(self.cryptroot_program)
        if pid:
            logger.info("Killing interactive prompt with process id %i ..", pid)
            if self.pre_context.execute('kill', '-9', str(pid), check=False):
                return
        # Warn the operator if we fail to identify and kill the interactive
        # prompt, but continue (as opposed to aborting) in the hope that
        # there is no interactive prompt or its not blocking.
        logger.notice(compact("""
            Failed to identify and kill the process that's responsible
            for the interactive prompt! The remote system may block on
            the interactive prompt, in this case manual intervention
            will be required.
        """))

    def offer_password(self):
        """
        Make the root disk encryption pass phrase available to the remote host.

        :raises: :exc:`UnsupportedSystemError` when :attr:`have_named_pipe`,
                 :attr:`have_cryptroot_config` and :attr:`have_cryptroot_program`
                 are all :data:`False`.

        If :attr:`have_named_pipe` is :data:`True` and :attr:`password` is set,
        the internal method :func:`write_to_named_pipe()` is used to write
        :attr:`password` to the named pipe. This is the preferred way to make
        the password available to the remote host because it's simple and
        robust.

        When the named pipe isn't available but :attr:`have_cryptroot_config`
        is :data:`True` the following internal methods are used instead:

        - :func:`kill_interactive_prompt()`
        - :func:`create_key_script()` (this is only called when
          :attr:`password` is set)
        - :func:`run_cryptroot_program()`
        - :func:`kill_emergency_shell()`

        This is more convoluted than the named pipe but it works :-).
        """
        # The following two non-interactive methods only work when
        # the caller provided us the root disk encryption password.
        if self.password:
            # If the named pipe is available that's all we need!
            if self.have_named_pipe:
                self.write_to_named_pipe()
                return
            # If /conf/conf.d/cryptroot is available we can use a key script.
            if self.have_cryptroot_config:
                self.kill_interactive_prompt()
                self.create_key_script()
                self.run_cryptroot_program(interactive=False)
                self.kill_emergency_shell()
                return
            # Explain why non-interactive unlocking isn't supported.
            logger.warning(compact("""
                The named pipe '%s' and the configuration file '%s' are both
                missing. This makes it impossible to non-interactively offer
                the root disk encryption pass phrase.
            """, self.named_pipe, self.cryptroot_config))
        else:
            # Explain why non-interactive unlocking isn't supported.
            logger.notice(compact("""
                No password was provided, this makes it impossible to
                non-interactively offer the root disk encryption pass phrase.
            """))
        # If /scripts/local-top/cryptroot is available we can run it interactively.
        if self.have_cryptroot_program:
            logger.info("I'll try to open an interactive prompt instead ..")
            self.kill_interactive_prompt()
            self.run_cryptroot_program(interactive=True)
            self.kill_emergency_shell()
            return
        # If all else fails we'll give up with a clear error message.
        raise UnsupportedSystemError(compact("""
            The named pipe '%s', configuration file '%s' and program file '%s'
            are all missing. Could it be that the system has already booted and
            we don't need to do anything?
        """, self.named_pipe, self.cryptroot_config, self.cryptroot_program))

    def parse_host_keys(self, cmd):
        """
        Find the SSH host keys in the output of ssh-keyscan_.

        :param cmd: A :class:`~executor.ssh.client.RemoteCommand` object.
        :returns: A :class:`set` of strings.
        """
        host_keys = set()
        for line in cmd.stdout.splitlines():
            tokens = line.split()
            if len(tokens) >= 3:
                hostname, key_type, base64_key = tokens[:3]
                host_keys.add(base64_key.decode('ascii'))
        if host_keys:
            logger.verbose("Found %s in ssh-keyscan output.", pluralize(len(host_keys), "host key"))
        else:
            logger.verbose("Didn't find any host keys in ssh-keyscan output!")
        return host_keys

    def parse_server_header(self, cmd):
        """
        Find the SSH server header in the output of ssh-keyscan_.

        :param cmd: A :class:`~executor.ssh.client.RemoteCommand` object.
        :returns: The SSH server header (a string).
        """
        for line in cmd.stderr.splitlines():
            tokens = line.decode('ascii').split()
            if len(tokens) >= 3 and tokens[0] == '#':
                comment, hostname, header = tokens[:3]
                logger.verbose("Found header in ssh-keyscan output: %s", header)
                return header
        logger.verbose("Didn't find header in ssh-keyscan output!")
        return ''

    def scan_ssh_server(self, profile):
        """
        Get the SSH server header and host keys.

        :param profile: A :class:`ConnectionProfile` object.
        :returns: A :class:`ServerDetails` object.

        The :func:`scan_ssh_server()` method runs ssh-keyscan_ in
        :attr:`context` and parses its output to get the SSH server
        header and host keys.

        .. _ssh-keyscan: https://manpages.debian.org/ssh-keyscan
        """
        timer = Timer()
        logger.verbose("Using ssh-keyscan to scan %s:%i  ..", profile.hostname, profile.port_number)
        cmd = self.context.execute(
            'ssh-keyscan', '-p', '%i' % profile.port_number, '-T', '%i' % self.scan_timeout,
            profile.hostname, capture=True, capture_stderr=True, check=False,
        )
        logger.verbose("Took %s to run ssh-keyscan program.", timer)
        return ServerDetails(
            header=self.parse_server_header(cmd),
            host_keys=frozenset(self.parse_host_keys(cmd)),
        )

    def run_cryptroot_program(self, interactive=True):
        """Unlock the root disk encryption by running :attr:`cryptroot_program`."""
        logger.info("Restarting %s program ..", self.cryptroot_program)
        self.pre_context.execute(self.cryptroot_program, tty=interactive)

    def store_host_keys(self, pre_server, post_server):
        """
        Store the SSH host keys in the configuration.

        :param pre_server: The :class:`ServerDetails` object from :func:`wait_for_pre_boot()`.
        :param post_server: The :class:`ServerDetails` object from :func:`wait_for_post_boot()`.
        """
        if self.config_section:
            items = (('pre-boot-host-keys', pre_server), ('post-boot-host-keys', post_server))
            options = dict((name, '\n'.join(sorted(server.host_keys))) for name, server in items)
            if not all(self.config.get(name) == value for name, value in options.items()):
                logger.info("Storing SSH host keys in %s ..", HOST_KEYS_FILE)
                filename = parse_path(HOST_KEYS_FILE)
                directory = os.path.dirname(filename)
                if not os.path.isdir(directory):
                    os.makedirs(directory)
                parser = configparser.RawConfigParser()
                parser.read(filename)
                if not parser.has_section(self.config_section):
                    parser.add_section(self.config_section)
                for name, value in options.items():
                    parser.set(self.config_section, name, value)
                with open(filename, 'w') as handle:
                    parser.write(handle)
        else:
            logger.verbose("Not storing SSH host keys (no configuration available).")

    def test_ssh_connection(self, profile, context):
        """Verify SSH connectivity to the pre-boot environment."""
        logger.info("Testing SSH connection to %s:%s ..", profile.hostname, profile.port_number)
        return context.test('test', '-e', '/')

    def unlock_system(self, server=None):
        """
        Validate the pre-boot environment and unlock the root filesystem encryption.

        :param server: A :class:`ServerDetails` object or :data:`None`.

        When the `server` argument isn't given :func:`wait_for_pre_boot()`
        is used to wait for the pre-boot environment to become available.
        """
        timer = Timer()
        if not server:
            server = self.wait_for_pre_boot()
        self.check_ssh_connection()
        self.offer_password()
        self.wait_for_post_boot(server)
        logger.success("Unlocked remote system in %s.", timer)

    def wait_for_post_boot(self, pre_server):
        """
        Wait for the post-boot environment to come online.

        :param pre_server: A :class:`ServerDetails` object created by :func:`wait_for_pre_boot()`.
        """
        method_timer = Timer()
        check_keys = bool(pre_server.host_keys)
        check_headers = (self.pre_boot.port_number == self.post_boot.port_number)
        logger.info("Waiting for post-boot environment based on SSH %s ..",
                    "host keys" if check_keys else ("server headers" if check_headers else "port numbers"))
        with AutomaticSpinner("Waiting for post-boot environment", show_time=True):
            while True:
                iteration_timer = Timer()
                if check_headers or check_keys:
                    post_server = self.scan_ssh_server(self.post_boot)
                    if check_keys and post_server.host_keys:
                        logger.verbose("Checking if SSH host keys have changed ..")
                        if post_server.host_keys != pre_server.host_keys:
                            logger.info("Detected change in SSH host keys.")
                            self.store_host_keys(pre_server, post_server)
                            break
                    if check_headers and pre_server.header and post_server.header:
                        logger.verbose("Checking if SSH server header has changed ..")
                        if post_server.header != pre_server.header:
                            logger.info("Detected change in SSH server header.")
                            break
                elif self.test_ssh_connection(self.post_boot, self.post_context):
                    logger.info("Detected change in SSH port number.")
                    break
                if method_timer.elapsed_time >= self.boot_timeout:
                    raise BootTimeoutError(format(
                        "Timed out waiting for post-boot environment of %s to come online within %s!",
                        self.post_context, format_timespan(self.boot_timeout),
                    ))
                iteration_timer.sleep(self.retry_interval)
        logger.info("Waited %s for post-boot environment.", method_timer)

    def wait_for_pre_boot(self):
        """
        Wait for the pre-boot environment to become available.

        :returns: A :class:`ServerDetails` object.
        :raises: The following exceptions can be raised:

                 - :exc:`SystemUnreachableError` when :attr:`connect_timeout`
                   seconds have passed and we still haven't managed to query
                   the SSH server in the pre-boot environment.
                 - :exc:`UnlockAbortedError` when the post-boot environment is
                   detected and the operator aborts the unlock sequence.
        """
        method_timer = Timer()
        logger.info("Waiting for pre-boot environment to become available ..")
        with AutomaticSpinner("Waiting for pre-boot environment", show_time=True):
            while True:
                iteration_timer = Timer()
                server = self.scan_ssh_server(self.pre_boot)
                known_keys = self.get_known_host_keys('pre-boot-host-keys')
                if server.host_keys and known_keys:
                    logger.verbose("Checking if SSH host keys match known keys ..")
                    if server.host_keys & known_keys:
                        logger.info("Matched known SSH host keys of pre-boot environment.")
                        break
                    else:
                        logger.warning(compact("""
                            Detected post-boot environment while waiting for
                            pre-boot environment to become available, will keep
                            retrying...
                        """))
                elif server.match_header('dropbear'):
                    logger.info("Detected Dropbear in pre-boot environment (as expected).")
                    break
                elif server.match_header('openssh'):
                    logger.warning(compact("""
                        Detected OpenSSH server while connecting to pre-boot
                        environment where I was expecting Dropbear instead!
                        Could it be that you're accidentally connecting
                        to the post-boot environment?
                    """))
                    if self.interactive:
                        if prompt_for_confirmation("Continue connecting anyway?"):
                            logger.info("Continuing unlock sequence with operator consent ..")
                        else:
                            raise UnlockAbortedError("Unlock sequence aborted by operator.")
                    break
                if method_timer.elapsed_time >= self.connect_timeout:
                    raise SystemUnreachableError(format(
                        "Timed out waiting for pre-boot environment of %s to become available within %s!",
                        self.pre_context, format_timespan(self.connect_timeout),
                    ))
                iteration_timer.sleep(self.retry_interval)
        logger.info("Waited %s for pre-boot environment.", method_timer)
        return server

    def watch_system(self):
        """
        Start monitoring the remote system for reboots.

        When the remote system is rebooted, the root disk encryption will
        be unlocked automatically. The monitoring continues indefinitely.
        """
        known_keys = self.get_known_host_keys('pre-boot-host-keys')
        while True:
            # FIXME Check post-boot instead?!
            server = self.scan_ssh_server(self.pre_boot)
            if known_keys & server.host_keys:
                logger.info("Watch detected pre-boot environment, starting unlock sequence ..")
                self.unlock_system(server)
            else:
                logger.info("Watch detected post-boot environment, going back to sleep ..")
            time.sleep(self.watch_interval)

    def write_file(self, filename, contents):
        """
        Write a file in the initial ram disk of the pre-boot environment.

        :param filename: The pathname of the file to write (a string).
        :param contents: The contents to write to the file (a string).

        This method writes a file in the initial ram disk by running a remote
        'sh' shell that redirects its standard input to the given filename.
        """
        self.pre_context.execute('sh', '-c', 'cat > %s' % quote(filename), input=contents)

    def write_to_named_pipe(self):
        """Write :attr:`password` to the named pipe configured by :attr:`named_pipe`."""
        logger.info("Unlocking root filesystem using named pipe ..")
        unlock_cmd = 'echo -n %s > %s' % (quote(self.password), quote(self.named_pipe))
        self.pre_context.execute(input=unlock_cmd)


class ConnectionProfile(PropertyManager):

    """SSH connection profiles."""

    @mutable_property
    def expression(self):
        """The SSH connection profile encoded as a string."""
        tokens = []
        if self.username:
            tokens.append(self.username)
            tokens.append('@')
        tokens.append(self.hostname)
        if self.port_number:
            tokens.append(':')
            tokens.append(str(self.port_number))
        return ''.join(tokens)

    @expression.setter
    def expression(self, value):
        """Parse an SSH connection profile expression provided by the caller."""
        match = EXPRESSION_PATTERN.match(value)
        if not match:
            msg = "Failed to parse connection profile expression! (%r)"
            raise ValueError(format(msg, value))
        self.username = match.group('user') or 'root'
        self.hostname = match.group('host')
        self.port_number = int(match.group('port') or '22')
        self.identity_file = None

    @required_property
    def hostname(self):
        """The host name, IP address or SSH alias of the remote system (a string)."""

    @mutable_property
    def port_number(self):
        """The port number for SSH connections (an integer, defaults to 22)."""
        return 22

    @mutable_property
    def username(self):
        """The username used to log in to the remote system (a string, defaults to 'root')."""
        return 'root'

    @mutable_property
    def identity_file(self):
        """The pathname of the identity file used to connect to the remote system (a string or :data:`None`)."""


class ServerDetails(PropertyManager):

    """Properties that can be used to uniquely identify SSH servers."""

    @key_property
    def header(self):
        """
        The SSH server header (a string).

        This is the first line of output emitted by the SSH server when a
        client opens a TCP connection.
        """
        return ''

    @key_property
    def host_keys(self):
        """The SSH server host keys (a :class:`frozenset` of strings)."""
        return frozenset()

    def match_header(self, substring):
        """
        Check if :attr:`header` contains the given substring.

        :param substring: The substring to check (a string).
        :returns: :data:`True` if the header matches the substring,
                  :data:`False` otherwise.
        """
        if self.header:
            logger.verbose("Checking if SSH header matches substring '%s' ..", substring)
            return substring.lower() in self.header.lower()


class EncryptedSystemError(Exception):

    """Base class for custom exceptions raised by :mod:`debuntu_tools.remote_unlock`."""


class UnlockAbortedError(EncryptedSystemError):

    """Raised when the operator changes their minds."""


class SystemUnreachableError(EncryptedSystemError):

    """Raised when connecting to the SSH server in the pre-boot environment fails."""


class BootTimeoutError(EncryptedSystemError):

    """Raised when the remote system doesn't boot properly after unlocking."""


class UnsupportedSystemError(EncryptedSystemError):

    """Raised when the configuration file '/conf/conf.d/cryptroot' is not found."""
