Remote root disk encryption
===========================

This document contains notes about setting up remote root disk encryption on a
Linux_ server. My experiences are based on Ubuntu_ 12.04, 14.04, 16.04 and
18.04 but I'm guessing most of these things will work very similar on Debian_
and its derivatives_. In fact some of these notes apply to all Linux
distributions.

We will configure the system to enable network connectivity in the initramfs_
so that we can connect using SSH_ and inject the root disk encryption pass
phrase into the boot process. This makes it possible to set this up for
headless_ servers.

**Contents**

.. contents::
   :local:

Set up root disk encryption
---------------------------

It's much easier to start an Ubuntu_ installation with root disk encryption
than to set this up later [#]_ because the installer takes care of a lot of the
details involved. Of course doing this on a headless_ server assumes you have
access to something like a VNC_ connection.

.. [#] It is possible to add root disk encryption to an existing system, but it
       can be a bit tricky to get all the details right and not end up with a
       system that won't boot :-).

Enable SSH in the initramfs
---------------------------

Dropbear_ is a lightweight SSH_ server and BusyBox_ is a lightweight collection
of command line utilities. We'll need both of these in our initramfs_. They can
be installed on Debian/Ubuntu using the following command:

.. code-block:: sh

 $ sudo apt-get install busybox dropbear

This should [#]_ automatically configure Dropbear to start in the initramfs_
using the shell script ``/usr/share/initramfs-tools/hooks/dropbear``. Depending
on the version of the ``dropbear`` package this may or may not generate an SSH_
public/private key pair during installation:

- If a key pair is generated then the private key file will be located at
  ``/etc/initramfs-tools/root/.ssh/id_rsa``. You can download this file and
  remove it from the server, because it won't be needed there.

- If a key pair isn't generated, or if you prefer to use your own key pair, you
  can install your own public key into the initramfs_ (see the next section).

.. [#] The script ``/usr/share/initramfs-tools/hooks/dropbear`` should
       automatically include Dropbear_ in the initramfs_ image when it detects
       root disk encryption. If this doesn't work you can force Dropbear to be
       included by adding (or uncommenting) the line ``DROPBEAR=y`` in
       ``/usr/share/initramfs-tools/conf-hooks.d/dropbear``.

Install your own SSH key
~~~~~~~~~~~~~~~~~~~~~~~~

You can install your own public SSH key using the following steps:

.. contents::
   :local:

On Ubuntu >= 18.04
++++++++++++++++++

1. Open the file ``/etc/dropbear-initramfs/authorized_keys`` in a text
   editor of your choosing to add your public key::

   $ sudo vim /etc/dropbear-initramfs/authorized_keys

2. Update your initramfs_ images to include the key you added::

   $ sudo update-initramfs -uk all

On Ubuntu < 18.04
+++++++++++++++++

1. First make sure the ``/etc/initramfs-tools/root/.ssh`` directory exists::

   $ sudo mkdir -p /etc/initramfs-tools/root/.ssh

2. Open the file ``/etc/initramfs-tools/root/.ssh/authorized_keys`` in a text
   editor of your choosing to add your public key::

   $ sudo vim /etc/initramfs-tools/root/.ssh/authorized_keys

3. Update your initramfs_ images to include the key you added::

   $ sudo update-initramfs -uk all

Enable networking in the initramfs
----------------------------------

The network interfaces of Debian/Ubuntu servers are usually configured in
``/etc/network/interfaces`` which is not available in initramfs_ images. What
we can do instead is to provide a suitable (static) network configuration
directly to the kernel via a kernel parameter. On Debian/Ubuntu this is done
by changing the ``GRUB_CMDLINE_LINUX`` variable defined in the configuration
file ``/etc/default/grub``. Here's an example based on my VPS_::

 GRUB_CMDLINE_LINUX="ip=149.210.193.173::149.210.193.1:255.255.255.0::eth0:none"

As you can see this compresses an entire static network interface configuration
into a single ``ip=…`` kernel parameter, with fields separated by colons. The
kernel documentation contains `details on the 'ip' kernel parameter
<https://www.kernel.org/doc/Documentation/filesystems/nfs/nfsroot.txt>`_, but
for your convenience here is an overview of the supported fields::

 ip=<client-ip>:<server-ip>:<gw-ip>:<netmask>:<hostname>:<device>:<autoconf>:<dns0-ip>:<dns1-ip>

To elaborate even further, here is how the values in the example above map to
the named fields:

- **client-ip** is ``149.210.193.173``
- **server-ip** is empty (we're not using an NFS root)
- **gw-ip** is the gateway IP, in this case ``149.210.193.1``
  (if you hadn't already guessed, my VPS_ is hosted at TransIP 😉)
- **netmask** is ``255.255.255.0``
- **hostname** is empty (we're not using DHCP so there's no point in
  configuring a DHCP client id)
- **device** is ``eth0``
- **autoconf** is ``none`` (to disable autoconfiguration)

Make sure to run the following command after editing ``/etc/default/grub``::

 $ sudo update-grub

Consistent device naming
~~~~~~~~~~~~~~~~~~~~~~~~

The example above uses the device name ``eth0`` however with the introduction
of `consistent network device naming`_ the ``eth*`` names were retired. If you
need or want them back you can add the kernel parameters ``biosdevname=0`` and
``net.ifnames=0`` to the ``$GRUB_CMDLINE_LINUX`` variable.

.. _consistent network device naming: https://en.wikipedia.org/wiki/Consistent_Network_Device_Naming

On a Raspberry Pi
~~~~~~~~~~~~~~~~~

In June 2018 I got Ubuntu 16.04 with root disk encryption running on a
Raspberry Pi. Because the boot process of a Raspberry Pi is very different from
a regular computer, the way you configure it is also different. In this case I
needed to add the ``ip=…`` kernel parameter to the file
``/boot/firmware/cmdline.txt``.

Slow boot issues
~~~~~~~~~~~~~~~~

When the ``ip=`` kernel parameter and ``/etc/network/interfaces`` both
define a static network interface configuration, you may encounter slow boot
issues. If you were to look at the messages emitted by the boot process you
would most likely see a message along the lines of::

 Waiting for network configuration..

This can slow down the boot process by two or three minutes, making you doubt
whether a server is going to come back online! Fortunately there's an easy way
to avoid this problem. Open ``/etc/network/interfaces`` in your favorite text
editor and add the line ``pre-up ip addr flush dev eth0``, similar to this::

 auto lo
 iface lo inet loopback

 auto eth0
 iface eth0 inet static
   address 149.210.193.173
   netmask 255.255.255.0
   gateway 149.210.193.1
   pre-up ip addr flush dev eth0

I originally found this trick on the `Ubuntu Forums`_ in October 2014 when I
created my first headless server with root disk encryption based on Ubuntu
12.04 and I still need the workaround at the time of writing, on that same
server, which has since been upgraded to 14.04 and then to 16.04.

External references
-------------------

- The ``cryptsetup`` package on Debian/Ubuntu contains notes on how to setup
  remote unlocking in ``/usr/share/doc/cryptsetup/README.remote.gz``, this is
  how I initially got started back in 2014.

- The StackExchange question `SSH to decrypt encrypted LVM during headless
  server boot? <https://unix.stackexchange.com/questions/5017/>`_ received
  some interesting answers including a honorable mention of Mandos [#]_.

.. [#] You would not believe how much time I've invested in getting Mandos
       to unlock my servers unattended, I even went so far as to (cross)
       compile the "latest & greatest" versions for multiple CPU architectures
       in a desperate attempt to get it to work. I never did.

.. _Debian: https://en.wikipedia.org/wiki/Debian
.. _derivatives: https://en.wikipedia.org/wiki/Debian#Derivatives
.. _headless: https://en.wikipedia.org/wiki/Headless_computer
.. _initramfs: https://en.wikipedia.org/wiki/Initial_ramdisk
.. _Linux: https://en.wikipedia.org/wiki/Linux
.. _LUKS: https://en.wikipedia.org/wiki/Linux_Unified_Key_Setup
.. _SSH: https://en.wikipedia.org/wiki/Secure_Shell
.. _Ubuntu: https://en.wikipedia.org/wiki/Ubuntu_(operating_system)
.. _VNC: https://en.wikipedia.org/wiki/Virtual_Network_Computing
.. _Dropbear: https://en.wikipedia.org/wiki/Dropbear_(software)
.. _VPS: https://en.wikipedia.org/wiki/Virtual_private_server
.. _Ubuntu Forums: https://ubuntuforums.org/showthread.php?t=2085267
.. _BusyBox: https://en.wikipedia.org/wiki/BusyBox
