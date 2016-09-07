#!/usr/bin/env python

# Debian and Ubuntu system administration tools.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 15, 2016
# URL: https://debuntu-tools.readthedocs.io
#
# This script assumes an Ubuntu 14.04 test host.

"""Generate sample ``debuntu-kernel-manager`` outputs and convert them to HTML."""

# Standard library modules.
import codecs
import os
import re
import sys

# External dependencies.
import coloredlogs
from capturer import CaptureOutput
from coloredlogs.converter import convert
from executor import execute
from executor.contexts import RemoteContext
from humanfriendly.terminal import warning


def main():
    """Command line interface for ``update-samples.py``."""
    # Enable verbose logging to the terminal.
    coloredlogs.install(level='INFO')
    # Validate the command line arguments.
    arguments = sys.argv[1:]
    if len(arguments) != 1:
        warning("Please provide the SSH alias of a test host (a single argument).")
        sys.exit(1)
    # Construct the remote context.
    context = RemoteContext(ssh_alias=arguments[0])
    # Prepare Linux kernel packages on the test host.
    context.execute(
        'apt-get', 'install', '--yes',
        'linux-headers-3.13.0-63',
        'linux-headers-3.13.0-63-generic',
        'linux-headers-3.13.0-88',
        'linux-headers-generic-lts-xenial',
        'linux-image-3.13.0-63-generic',
        'linux-image-3.13.0-73-generic',
        'linux-image-4.4.0-21',
        'linux-image-4.4.0-21-generic',
        'linux-image-extra-3.13.0-63-generic',
        'linux-image-generic-lts-wily',
        'linux-image-generic-lts-xenial',
        environment=dict(DEBIAN_FRONTEND='noninteractive'),
        sudo=True,
        tty=False,
    )
    samples_directory = os.path.join(os.path.dirname(__file__), '..', 'docs')
    os.environ['COLOREDLOGS_FIELD_STYLES'] = ';'.join([
        'asctime=green',
        'levelname=black,bold',
    ])
    os.environ['COLOREDLOGS_LEVEL_STYLES'] = ';'.join([
        'verbose=green',
        'warning=yellow',
        'error=red',
    ])
    os.environ['COLOREDLOGS_LOG_FORMAT'] = ' '.join([
        '%(asctime)s',
        '%(levelname)s',
        '%(message)s',
    ])
    # Capture a run that is expected to fail.
    with CaptureOutput() as capturer:
        execute(
            'debuntu-kernel-manager',
            '--remote-host=%s' % context.ssh_alias,
            '--remove',
            '--verbose',
            check=False,
            tty=False,
        )
        capture_html(capturer, os.path.join(samples_directory, 'sanity-check-says-no.html'))
    # Capture a run that is expected to succeed.
    with CaptureOutput() as capturer:
        execute(
            'debuntu-kernel-manager',
            '--remote-host=%s' % context.ssh_alias,
            '--remove',
            '--force',
            '--verbose',
            '--',
            '--dry-run',
            '--quiet',
            '--quiet',
            tty=False,
        )
        capture_html(capturer, os.path.join(samples_directory, 'operator-says-yes.html'))


def capture_html(capturer, sample_file):
    """Convert a command's output to HTML and use that to update a sample output file."""
    html_text = convert(u"\n".join(
        line for line in capturer.get_lines()
        # Ignore lots of boring apt-get output.
        # if line[:4].isdigit()
    ))
    # Replace <br> elements with newline characters.
    html_text = re.sub(ur'\s*<\s*[Bb][Rr]\s*/?\s*>\s*', ur'\n', html_text)
    # Replace non-breaking spaces that are surrounded by non-whitespace
    # characters with regular spaces (to improve text wrapping).
    html_text = re.sub(ur'(\S)&nbsp;(\S)', ur'\1 \2', html_text)
    # Wrap the terminal output in a pre-formatted text block.
    html_text = u"<pre>%s</pre>\n" % html_text.strip()
    with codecs.open(sample_file, 'w', 'UTF-8') as handle:
        handle.write(html_text)


if __name__ == '__main__':
    main()
