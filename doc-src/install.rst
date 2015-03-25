.. Copyright (c) Los Alamos National Security, LLC, and others.

Installing QUAC
***************

QUAC can be installed on most UNIX-based systems, though installation is
easiest on OS X and Debian/Ubuntu. Patches to increase portability are very
welcome.

.. contents::
   :depth: 2
   :local:

PyPI and virtualenv (recommended)
=================================

This method installs QUAC and its Python dependencies inside a virtual
environment with its own Python binary and libraries. This isolates QUAC from
other Python stuff you may have on your system, reducing conflicts.

These instructions assume that virtualenvs are installed under
`~/.virtualenvs` and QUAC will be installed in `~/quac`.

#. Install prerequisites. The following are required:

   * Git.

   * Python 3.4 including development libraries.

   * `virtualenv` and `virtualenvwrapper`.

   * Programs and libraries needed by Python packages (e.g., HDF5 command-line
     tools, GEOS). Installation failures along the way should guide you here.
     Known `.deb` packages needed on Ubuntu Trusty:

     * `cmdtest`
     * `hdf5-tools`
     * `libdgal-dev`
     * `python-pip`
     * `python-virtualenv`
     * `virtualenvwrapper`

   Installation of these things is outside the scope of this guide.

#. Download QUAC using Git::

     $ cd
     $ git clone https://github.com/reidpr/quac.git
     $ cd quac

#. Create virtual environment, and then deactivate it because you are going to
   be messing with it::

     $ mkvirtualenv --python=/usr/bin/python3 quac
     $ deactivate

#. Add to virtualenv post-activate hook
   (`~/.virtualenvs/quac/bin/postactivate`):

   .. code-block:: sh

     OLD_PYTHONPATH="$PYTHONPATH"
     export PYTHONPATH=~/quac/lib
     OLD_PATH="$PATH"
     export PATH=~/tw/quac/bin:$PATH

#. Add to virtualenv pre-deactivate hook
   (`~/.virtualenvs/quac/bin/predeactivate`):

   .. code-block:: sh

     export PYTHONPATH="$OLD_PYTHONPATH"
     export PATH="$OLD_PATH"

#. Activate virtual environment::

     $ workon quac

#. Install GDAL Python bindings (adjust include paths and version if needed)::

     $ CPLUS_INCLUDE_PATH=/usr/include/gdal C_INCLUDE_PATH=/usr/include/gdal pip install gdal==1.10.0

   This must be done manually because the bindings have a buggy include path.
   Note also that the version must match the system GDAL libraries or the
   build will fail in strange ways.

#. Install `APSW <http://rogerbinns.github.io/apsw/>`_ (alternate SQLite
   bindings). This cannot be done using :samp:`pip` because the install script
   requires options, and :samp:`pip` `cannot provide them
   <http://rogerbinns.github.io/apsw/download.html#easy-install-pip-pypi>`_.
   For example (the latest version is probably the best choice)::

     $ pushd /usr/local/src
     $ wget https://github.com/rogerbinns/apsw/releases/download/3.8.8.2-r1/apsw-3.8.8.2-r1.zip
     $ unzip apsw-3.8.8.2-r1.zip
     $ cd apsw-3.8.8.2-r1
     $ python setup.py fetch --all --missing-checksum-ok build --enable-all-extensions install test
     $ popd

   The tests take 5-10 minutes to run; you can omit if you want to live
   dangerously, or proceed in another terminal while they run.

   You can also install APSW at the system level and configure your virtualenv
   to pass system modules through.

#. Install remaining Python dependencies::

     $ pip install -r requirements.txt

#. Build executables and the documentation::

     $ make

#. Run the tests (this is actually pretty important, as it tells you whether
   you've installed all the dependencies correctly)::

     $ ./runtests

   Some tests require additional data or resources; if they are not available,
   then the tests are skipped.

   (While some parts of QUAC will work if some tests fail, we recommend
   installing everything necessary to make them pass, as this will make your
   life much easier going forward.)

.. note:: If you plan to :doc:`contribute to QUAC <contributing>`, you should
          do two things differently. First, fork the repository on Github and
          clone your own fork instead. Second, the Git wrapper `hub
          <https://github.com/defunkt/hub>`_ is recommended.


Self-compile (not recommended)
==============================

.. warning:: This installation method should only be used if the normal way
             does not work. It is rarely tested and likely to be broken. In
             particular, it has not been updated since before the Python 3
             upgrade.

             Essentially, it re-implements the most basic functionality of a
             package manager, and it does so rather poorly and without regard
             to what you already have installed.

This method does not require root, and it will take a little while to run,
since it has to download and compile a fair amount of stuff. There are
separate scripts to download and install, in case you want to QUAC on a system
that doesn't have good access to the Internet.

Prerequisites:

* Some basic dependencies such as GNU Make 3.81 and C/C++/Fortran compilers.
  Exactly what is currently unknown, but it "Works For Me™".

* The `Environment Modules <http://modules.sourceforge.net/>`_ package. You
  probably have this if your system has a ``module`` command. This isn't
  strictly needed, as you can get the same effect by editing your shell init
  files appropriately.

The below assumes that you have unpacked QUAC into ``$QUACBASE``.

First, install the dependencies::

   $ mkdir $QUACBASE/deps
   $ cd $QUACBASE/deps
   $ ../misc/manual-download  # creates $QUACBASE/deps/src
   $ ../misc/manual-install

Optional:

* ``manual-install`` takes an argument which is the number of processes to use
  while compiling (``make -j``).

* You can run ``manual-download`` anywhere and move the resulting ``src``
  directory into ``$QUACBASE/deps`` manually.

Second, configure your environment. Add following to your ``.bashrc``::

   $ module use --append $QUACBASE/misc
   $ module load quac-module

Note that in addition to making all the dependencies available, this module
adds the QUAC libraries and binaries themselves to your various paths. Be
aware of this if you have multiple QUAC working directories. (For example,
suppose a colleague has installed QUAC and its dependencies in location
:math:`A`, and you've loaded ``quac-module`` from :math:`A` because you don't
want to duplicate the tedious installation. You have your own QUAC working
directory at :math:`B` so you can hack on it. If you simply type
``quacreduce``, you will get the one in :math:`A` even if you are working in
:math:`B`, unless you take measures to prevent this.)


..  LocalWords:  MYPREFIX Rv setuptools Sv defunkt QUACBASE deps src
