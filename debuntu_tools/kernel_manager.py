# Debian and Ubuntu system administration tools.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: November 17, 2018
# URL: https://debuntu-tools.readthedocs.io

"""
Usage: debuntu-kernel-manager [OPTIONS] -- [APT_OPTIONS]

Detect and remove old Linux kernel header, image and modules packages that can
be safely removed to conserve disk space and speed up apt-get runs that install
or remove kernels.

By default old packages are detected and reported on the command line but no
changes are made. To actually remove old packages you need to use the -c,
--clean or --remove option. Using the following command you can perform
a dry run that shows you what will happen without actually doing it:

  $ debuntu-kernel-manager --remove -- --dry-run

The debuntu-kernel-manager program is currently in alpha status, which means
a first attempt at a usable program has been published but there are no
guarantees about what it actually does. You have been warned :-).

Supported options:

  -c, --clean, --remove

   Remove Linux kernel header and/or image packages that are deemed to be safe
   to remove. The use of this option requires sudo access on the system in
   order to run the 'apt-get remove' command.

  -f, --force

    When more than one Linux kernel meta package is installed the -c, --clean
    and --remove options will refuse to run apt-get and exit with an error
    instead. Use the -f or --force option to override this sanity check.

  -p, --preserve-count=NUMBER

    Preserve the NUMBER newest versions of the kernel packages (defaults to 2).

  -r, --remote-host=ALIAS

    Detect and remove old Linux kernel header and image packages on a remote
    host over SSH. The ALIAS argument gives the SSH alias that should be used
    to connect to the remote host.

  -v, --verbose

    Increase verbosity (can be repeated).

  -q, --quiet

    Decrease verbosity (can be repeated).

  -h, --help

    Show this message and exit.
"""

# Standard library modules.
import collections
import getopt
import re
import sys

# External dependencies.
import coloredlogs
from deb_pkg_tools.version import Version
from executor import ExternalCommandFailed
from executor.contexts import create_context
from humanfriendly import AutomaticSpinner, Timer, compact, concatenate, pluralize
from humanfriendly.terminal import ansi_wrap, usage, warning
from property_manager import PropertyManager, cached_property, key_property, required_property
from verboselogs import VerboseLogger

REBOOT_REQUIRED_FILE = "/var/run/reboot-required"
"""The absolute pathname of the file that exists when a system reboot is required (a string)."""

REBOOT_REQUIRED_PACKAGES_FILE = "/var/run/reboot-required.pkgs"
"""The absolute pathname of a file with details about why a system reboot is required (a string)."""

# Compiled regular expression pattern to split package names
# on dashes while ignoring dashes with a digit on both sides.
PACKAGE_NAME_TOKENIZATION_PATTERN = re.compile(
    r"""
    # A dash with non-digits on both sides is fine.
    (?<=\D) - (?=\D) |
    # A dash with a non-digit on the left side is fine.
    (?<=\D) - (?=\d) |
    # A dash with a non-digit on the right side is fine.
    (?<=\d) - (?=\D)
""",
    re.VERBOSE,
)

# Compiled regular expression pattern to match kernel versions encoded
# in package names (assuming tokens are split on the pattern above).
KERNEL_VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+-\d+")

# Initialize a logger for this module.
logger = VerboseLogger(__name__)


def main():
    """Command line interface for ``debuntu-kernel-manager``."""
    # Initialize logging to the terminal and system log.
    coloredlogs.install(syslog=True)
    # Parse the command line arguments.
    action = "render_summary"
    context_opts = dict()
    manager_opts = dict()
    try:
        options, arguments = getopt.getopt(
            sys.argv[1:],
            "cfp:r:vqh",
            ["clean", "remove", "force", "preserve-count=", "remote-host=", "verbose", "quiet", "help"],
        )
        for option, value in options:
            if option in ("-c", "--clean", "--remove"):
                action = "cleanup_packages"
            elif option in ("-f", "--force"):
                manager_opts["force"] = True
            elif option in ("-p", "--preserve-count"):
                manager_opts["preserve_count"] = int(value)
            elif option in ("-r", "--remote-host"):
                context_opts["ssh_alias"] = value
            elif option in ("-v", "--verbose"):
                coloredlogs.increase_verbosity()
            elif option in ("-q", "--quiet"):
                coloredlogs.decrease_verbosity()
            elif option in ("-h", "--help"):
                usage(__doc__)
                return
            else:
                raise Exception("Unhandled option!")
        # Any positional arguments are passed to apt-get.
        manager_opts["apt_options"] = arguments
    except Exception as e:
        warning("Failed to parse command line arguments! (%s)", e)
        sys.exit(1)
    # Execute the requested action(s).
    context = create_context(**context_opts)
    try:
        manager = KernelPackageManager(context=context, **manager_opts)
        getattr(manager, action)()
    except (CleanupError, ExternalCommandFailed) as e:
        logger.error("%s", e)
        sys.exit(1)
    except Exception:
        logger.exception("Encountered unexpected exception on %s!", context)
        sys.exit(1)


class KernelPackageManager(PropertyManager):

    """Python API for automated Linux kernel image package cleanup on Debian based systems."""

    @required_property
    def apt_options(self):
        """A list of strings with command line options to pass to ``apt-get``."""
        return []

    @required_property(repr=False)
    def context(self):
        """An execution context created by :mod:`executor.contexts`."""

    @required_property
    def force(self):
        """Whether to continue with removal despite warnings (a boolean, defaults to :data:`False`)."""
        return False

    @required_property
    def preserve_count(self):
        """The number of kernel packages to preserve (an integer, defaults to 2)."""
        return 2

    @property
    def dry_run(self):
        """:data:`True` if :attr:`cleanup_command` performs a dry run, :data:`False` otherwise."""
        return any(
            re.match("^-[^-]", argument)
            and "s" in argument
            or argument in ("--simulate", "--just-print", "--dry-run", "--recon", "--no-act")
            for argument in self.apt_options
        )

    @cached_property
    def installed_packages(self):
        """
        A dictionary that maps package names (strings) to :class:`MaybeKernelPackage` objects.

        The value of this property is generated by parsing the output of the
        ``dpkg --list`` command.
        """
        mapping = {}
        output = self.context.capture("dpkg", "--list")
        for line in output.splitlines():
            tokens = line.split()
            if len(tokens) >= 3:
                status, name, version = tokens[:3]
                if len(status) == 2 and status.isalnum():
                    mapping[name] = MaybeKernelPackage(name=name, version=Version(version), status=status)
        return mapping

    @cached_property
    def installed_header_packages(self):
        """A list of :class:`MaybeKernelPackage` objects for the installed Linux kernel header packages."""
        return sorted(
            (
                package
                for package in self.installed_packages.values()
                if package.is_installed and package.is_header_package
            ),
            key=lambda package: (package.version, package.name),
        )

    @cached_property
    def installed_kernel_packages(self):
        """A list of :class:`MaybeKernelPackage` objects for the installed kernel images."""
        return sorted(
            (
                package
                for package in self.installed_packages.values()
                if package.is_installed and package.is_kernel_package
            ),
            key=lambda package: (package.version, package.name),
        )

    @cached_property
    def installed_modules_packages(self):
        """A list of :class:`MaybeKernelPackage` objects for the installed kernel modules packages."""
        return sorted(
            (
                package
                for package in self.installed_packages.values()
                if package.is_installed and package.is_modules_package
            ),
            key=lambda package: (package.version, package.name),
        )

    @cached_property
    def installed_header_meta_packages(self):
        """A list of :class:`MaybeKernelPackage` objects with installed meta packages for kernel headers."""
        # We change the sort key for meta packages from (name, version) to just
        # the version so that the meta packages are listed in version order
        # despite the names being different.
        return sorted(
            (
                package
                for package in self.installed_packages.values()
                if package.is_installed and package.is_header_meta_package
            ),
            key=lambda p: p.version,
        )

    @cached_property
    def installed_image_meta_packages(self):
        """A list of :class:`MaybeKernelPackage` objects with installed meta packages for kernel images."""
        # We change the sort key for meta packages from (name, version) to just
        # the version so that the meta packages are listed in version order
        # despite the names being different.
        return sorted(
            (
                package
                for package in self.installed_packages.values()
                if package.is_installed and package.is_image_meta_package
            ),
            key=lambda p: p.version,
        )

    @cached_property
    def installed_package_groups(self):
        """A list of sets with :class:`MaybeKernelPackage` objects for installed header and kernel packages."""
        grouped_packages = collections.defaultdict(list)
        for package in self.installed_packages.values():
            if package.is_installed and package.is_supported_package:
                grouped_packages[package.version_in_name].append(package)
        return sorted(grouped_packages.values(), key=lambda group: group[0].version)

    @cached_property
    def active_kernel_release(self):
        """The output of ``uname --kernel-release`` (a string)."""
        return self.context.capture("uname", "--kernel-release")

    @cached_property
    def active_kernel_package(self):
        """The package name for the running kernel (a string)."""
        return "linux-image-%s" % self.active_kernel_release

    @cached_property
    def reboot_required(self):
        """:data:`True` if :data:`REBOOT_REQUIRED_FILE` exists, :data:`False` otherwise."""
        return self.context.exists(REBOOT_REQUIRED_FILE)

    @cached_property
    def removable_package_groups(self):
        """
        A list of sets with :class:`MaybeKernelPackage` objects considered to be removable.

        Candidates for removal are selected from :attr:`installed_package_groups`,
        ignoring :attr:`active_kernel_package` and the newest
        :attr:`preserve_count` kernel images (minus one when
        :attr:`active_kernel_package` was ignored).
        """
        may_remove = []
        will_remove = []
        preserve_count = self.preserve_count
        for group in self.installed_package_groups:
            if any(package.name == self.active_kernel_package for package in group):
                # Never remove the package group for the active kernel image.
                preserve_count -= 1
            elif not any(package.is_kernel_package for package in group):
                # Ignore package groups that don't contain a kernel image.
                will_remove.append(group)
            else:
                # Consider removing nonactive package groups with a kernel image.
                may_remove.append(group)
        if preserve_count > 0:
            # Prefer new kernels over old kernels and respect
            # the configured number of packages to preserve.
            may_remove = may_remove[:-preserve_count]
        return will_remove + may_remove

    @cached_property
    def removable_header_packages(self):
        """A list of :class:`MaybeKernelPackage` objects for header packages considered to be removable."""
        return sorted(pkg for grp in self.removable_package_groups for pkg in grp if pkg.is_header_package)

    @cached_property
    def removable_kernel_packages(self):
        """A list of :class:`MaybeKernelPackage` objects for kernel packages considered to be removable."""
        return sorted(pkg for grp in self.removable_package_groups for pkg in grp if pkg.is_kernel_package)

    @cached_property
    def removable_modules_packages(self):
        """A list of :class:`MaybeKernelPackage` objects for modules packages considered to be removable."""
        return sorted(pkg for grp in self.removable_package_groups for pkg in grp if pkg.is_modules_package)

    @cached_property
    def removable_packages(self):
        """A list of :class:`MaybeKernelPackage` objects for kernel related packages considered to be removable."""
        return self.removable_header_packages + self.removable_kernel_packages + self.removable_modules_packages

    @cached_property
    def running_newest_kernel(self):
        """:data:`True` if the newest kernel is currently active, :data:`False` otherwise."""
        return any(package.name == self.active_kernel_package for package in self.installed_package_groups[-1])

    @cached_property
    def cleanup_command(self):
        """A list of strings with the ``apt-get`` command to remove old packages."""
        command_line = []
        if self.removable_packages:
            command_line.extend(["apt-get", "remove", "--purge"])
            command_line.extend(self.apt_options)
            for group in self.removable_package_groups:
                command_line.extend(sorted(package.name for package in group))
        return command_line

    def render_summary(self):
        """Render a summary of installed and removable kernel packages on the terminal."""
        logger.verbose("Sanity checking meta packages on %s ..", self.context)
        with AutomaticSpinner(label="Gathering information about %s" % self.context):
            # Report the installed Linux kernel image meta package(s).
            if self.installed_image_meta_packages:
                logger.info(
                    "Found %s installed:",
                    pluralize(len(self.installed_image_meta_packages), "Linux kernel image meta package"),
                )
                for package in self.installed_image_meta_packages:
                    logger.info(" - %s (%s)", package.name, package.version)
                if len(self.installed_image_meta_packages) > 1:
                    names = concatenate(pkg.name for pkg in self.installed_image_meta_packages)
                    logger.warning(
                        compact(
                            """
                            You have more than one Linux kernel image meta
                            package installed ({names}) which means automatic
                            package removal can be unreliable!
                            """,
                            names=names,
                        )
                    )
                    logger.verbose(
                        compact(
                            """
                            I would suggest to stick to one Linux kernel image
                            meta package, preferably the one that matches the
                            newest kernel :-)
                            """
                        )
                    )
            else:
                logger.warning(
                    compact(
                        """
                        It looks like there's no Linux kernel image meta
                        package installed! I hope you've thought about how to
                        handle security updates?
                        """
                    )
                )
            # Report the installed Linux kernel header/image package(s).
            logger.verbose("Checking for removable packages on %s ..", self.context)
            package_types = (
                (self.installed_kernel_packages, "image", True),
                (self.installed_header_packages, "header", False),
                (self.installed_modules_packages, "modules", False),
            )
            for collection, label, expected in package_types:
                if collection:
                    logger.info("Found %s:", pluralize(len(collection), "installed Linux kernel %s package" % label))
                    for group in self.installed_package_groups:
                        matching_packages = sorted(package.name for package in group if package in collection)
                        active_group = any(package.name == self.active_kernel_package for package in group)
                        removable_group = group in self.removable_package_groups
                        if matching_packages:
                            logger.info(
                                " - %s (%s)",
                                concatenate(matching_packages),
                                ansi_wrap("removable", color="green")
                                if removable_group
                                else ansi_wrap(
                                    "the active kernel"
                                    if active_group
                                    else ("one of %i newest kernels" % self.preserve_count),
                                    color="blue",
                                ),
                            )
                elif expected:
                    logger.warning("No installed %s packages found, this can't be right?!", label)
            # Report the removable packages.
            if self.removable_packages:
                logger.info("Found %s that can be removed.", pluralize(len(self.removable_packages), "package"))
                # Report the shell command to remove the packages.
                logger.verbose("Command to remove packages: %s", " ".join(self.cleanup_command))
            else:
                logger.info("No packages need to be removed! :-)")

    def cleanup_packages(self, **options):
        """
        Run ``apt-get`` to cleanup removable kernel related packages.

        :param options: Any keyword arguments are passed on to the
                        :func:`~executor.contexts.AbstractContext.execute()`
                        method of the :class:`context` object.
        :returns: :data:`True` if a system reboot is required (to switch to the
                  newest installed kernel image or because security updates
                  have been installed), :data:`False` otherwise.
        :raises: :exc:`CleanupError` when multiple Linux kernel meta packages
                 are installed and :attr:`force` is :data:`False`.
        """
        timer = Timer()
        self.render_summary()
        if self.cleanup_command:
            if len(self.installed_image_meta_packages) > 1 and not self.force:
                raise CleanupError(
                    compact(
                        """
                        Refusing to cleanup kernel related packages on {system}
                        because results can be unreliable when multiple Linux
                        kernel image meta packages are installed! You can use
                        the -f, --force option to override this sanity check.
                        """,
                        system=self.context,
                    )
                )
            # Check if the packaging system has signaled that a system reboot
            # is required before we run the `apt-get remove' command.
            reboot_required_before = self.reboot_required
            # Get the set of installed packages before we run `apt-get remove'.
            installed_packages_before = set(p for p in self.installed_packages.values() if p.is_installed)
            # Actually run the `apt-get remove' command.
            logger.info("Removing %s on %s ..", pluralize(len(self.removable_packages), "package"), self.context)
            self.context.execute(*self.cleanup_command, sudo=True, **options)
            # Make sure `/etc/apt/apt.conf.d/01autoremove-kernels' is up to date.
            auto_removal_script = "/etc/kernel/postinst.d/apt-auto-removal"
            logger.verbose("Checking if %s needs to be run ..", auto_removal_script)
            if self.context.test("test", "-x", auto_removal_script):
                if self.dry_run:
                    logger.verbose("Skipping %s script because we're performing a dry-run.", auto_removal_script)
                else:
                    logger.verbose("Running %s script ..", auto_removal_script)
                    auto_removal_command = [auto_removal_script, self.active_kernel_release]
                    if not self.context.execute(*auto_removal_command, check=False, sudo=True, tty=False):
                        logger.warning(
                            "Failed to update auto-remove statuses! (%s reported an error)", auto_removal_script
                        )
            logger.info("Done! (took %s)", timer)
            # The `apt-get remove' command invalidates all of our cached data
            # so we need to refresh our cached properties to avoid stale data.
            self.clear_cached_properties()
            # Check if it is safe to remove /var/run/reboot-required.
            if self.running_newest_kernel and not reboot_required_before:
                # Get the set of installed packages after running `apt-get remove'.
                installed_packages_after = set(p for p in self.installed_packages.values() if p.is_installed)
                if installed_packages_after.issubset(installed_packages_before):
                    # We can remove the signal file(s) iff:
                    # 1. A system reboot wasn't already required.
                    # 2. We're already running on the newest kernel.
                    # 3. We only removed packages but didn't install or upgrade any.
                    if self.dry_run:
                        logger.info("Skipping signal file removal because we're performing a dry-run.")
                    else:
                        logger.info("System reboot is avoidable! Removing signal file(s) ..")
                        self.context.execute(
                            "rm", "--force", REBOOT_REQUIRED_FILE, REBOOT_REQUIRED_PACKAGES_FILE, sudo=True, tty=False
                        )
        # Inform the operator and caller about whether a reboot is required.
        if not self.running_newest_kernel:
            logger.info("System reboot needed (not yet running the newest kernel).")
            return True
        elif self.reboot_required:
            logger.info("System reboot needed (%s exists).", REBOOT_REQUIRED_FILE)
            return True
        else:
            logger.info("System reboot is not necessary.")
            return False


class MaybeKernelPackage(PropertyManager):

    """Dumb container for entries parsed from ``dpkg --list`` output."""

    # Explicitly define the sort order of the key properties.
    key_properties = "name", "version"

    @key_property
    def name(self):
        """The name of the package (a string)."""

    @key_property
    def version(self):
        """The version of the package (a :class:`~deb_pkg_tools.version.Version` object)."""

    @required_property
    def status(self):
        """The status of the package (a string of two characters, refer to the ``dpkg`` man pages for details)."""

    @property
    def is_installed(self):
        """:data:`True` if the package is installed (or configuration files remain), :data:`False` otherwise."""
        return self.status in ("ii", "rc")

    @cached_property
    def tokenized_name(self):
        """
        The tokenized name of the package (a list of strings).

        The value of this property is computed by calling
        :func:`tokenize_package_name()` on :attr:`name`.
        """
        return tokenize_package_name(self.name)

    @cached_property
    def is_header_meta_package(self):
        """:data:`True` if the package is a Linux kernel header meta package, :data:`False` otherwise."""
        return (
            len(self.tokenized_name) >= 3
            and self.tokenized_name[0] == "linux"
            and "headers" in self.tokenized_name
            and not any(map(is_kernel_version, self.tokenized_name))
        )

    @cached_property
    def is_image_meta_package(self):
        """:data:`True` if the package is a Linux kernel image meta package, :data:`False` otherwise."""
        return (
            len(self.tokenized_name) >= 3
            and self.tokenized_name[0] == "linux"
            and "image" in self.tokenized_name
            and not any(map(is_kernel_version, self.tokenized_name))
        )

    @cached_property
    def is_header_package(self):
        """:data:`True` if the package is a specific version of the Linux kernel headers, :data:`False` otherwise."""
        return (
            # linux-headers-$VERSION-generic
            len(self.tokenized_name) >= 3
            and self.tokenized_name[0] == "linux"
            and self.tokenized_name[1] == "headers"
            and is_kernel_version(self.tokenized_name[2])
        ) or (
            # linux-raspi2-headers-$VERSION
            len(self.tokenized_name) >= 4
            and self.tokenized_name[0] == "linux"
            and self.tokenized_name[1].isalnum()
            and self.tokenized_name[2] == "headers"
            and is_kernel_version(self.tokenized_name[3])
        )

    @cached_property
    def is_kernel_package(self):
        """:data:`True` if the package is a specific version of the Linux kernel image, :data:`False` otherwise."""
        return (
            (
                # linux-image-$VERSION
                len(self.tokenized_name) >= 3
                and self.tokenized_name[0] == "linux"
                and self.tokenized_name[1] == "image"
                and is_kernel_version(self.tokenized_name[2])
            )
            or (
                # linux-image-extra-$VERSION
                len(self.tokenized_name) >= 4
                and self.tokenized_name[0] == "linux"
                and self.tokenized_name[1] == "image"
                and self.tokenized_name[2] == "extra"
                and is_kernel_version(self.tokenized_name[3])
            )
            or (
                # linux-signed-image-$VERSION
                len(self.tokenized_name) >= 4
                and self.tokenized_name[0] == "linux"
                and self.tokenized_name[1] == "signed"
                and self.tokenized_name[2] == "image"
                and is_kernel_version(self.tokenized_name[3])
            )
        )

    @cached_property
    def is_modules_package(self):
        """:data:`True` if the package contains Linux kernel modules, :data:`False` otherwise."""
        return (
            # linux-modules-$VERSION-$VARIANT
            len(self.tokenized_name) >= 3
            and self.tokenized_name[0] == "linux"
            and self.tokenized_name[1] == "modules"
            and is_kernel_version(self.tokenized_name[2])
        ) or (
            # linux-modules-extra-$VERSION-$VARIANT
            len(self.tokenized_name) >= 4
            and self.tokenized_name[0] == "linux"
            and self.tokenized_name[1] == "modules"
            and self.tokenized_name[2] == "extra"
            and is_kernel_version(self.tokenized_name[3])
        )

    @cached_property
    def is_supported_package(self):
        """:data:`True` if the package concerns a Linux kernel image or modules or headers, :data:`False` otherwise."""
        return self.is_header_package or self.is_kernel_package or self.is_modules_package

    @cached_property
    def version_in_name(self):
        """The version encoded in the name of the package (a string or :data:`None`)."""
        if self.is_supported_package:
            for token in self.tokenized_name:
                if is_kernel_version(token):
                    return token

    @cached_property
    def kernel_type(self):
        """The kernel type encoded in the name of the package (a string or :data:`None`)."""
        if self.is_supported_package:
            if self.tokenized_name[-1].isalpha():
                return self.tokenized_name[-1]


def tokenize_package_name(package_name):
    """
    Split a (kernel) package name into tokens.

    :param package_name: The name of a package (a string).
    :returns: A list of strings.

    The :func:`tokenize_package_name()` function uses a regular expression to
    tokenize package names by splitting on dashes while ignoring dashes with a
    digit on both sides (i.e. dashes that are part of a version number). For
    example:

    >>> from debuntu_tools.kernel_manager import tokenize_package_name
    >>> tokenize_package_name('linux-image-4.4.0-72-generic')
    ['linux', 'image', '4.4.0-72', 'generic']
    """
    return PACKAGE_NAME_TOKENIZATION_PATTERN.split(package_name)


def is_kernel_version(token):
    """
    Check whether a token in a package name looks like a kernel version.

    :param token: The token to check (a string).
    :returns: :data:`True` if the token looks like a kernel version,
              :data:`False` otherwise.

    The :func:`is_kernel_version()` function uses a regular expression
    to check whether the given string looks like a kernel version of
    the form ``4.4.0-72``. The string is assumed to be a package
    name token returned by :func:`tokenize_package_name()`.
    """
    return KERNEL_VERSION_PATTERN.match(token) is not None


class CleanupError(Exception):

    """
    Custom exception to detect known problems.

    Raised by :class:`~KernelPackageManager` when multiple Linux kernel meta
    packages are installed but :attr:`~.KernelPackageManager.force` is
    :data:`False`.
    """
