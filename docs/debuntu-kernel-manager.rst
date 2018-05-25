Sample output of debuntu-kernel-manager
=======================================

On this page you can find sample outputs of ``debuntu-kernel-manager``.

**Contents**

.. contents::
   :local:

Removal forbidden
-----------------

The following sample output shows that ``debuntu-kernel-manager`` detects the
presence of multiple Linux kernel image meta packages and refuses to remove any
packages.

.. raw:: html
   :file: sanity-check-says-no.html

Forced removal
--------------

The following sample output shows that ``debuntu-kernel-manager`` detects the
presence of multiple Linux kernel image meta packages but blindly marches on at
the explicit request of the operator (it's just a dry run after all :-). The
result is what I intended to do though!

.. raw:: html
   :file: operator-says-yes.html
