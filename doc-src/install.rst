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
   For example (use the latest version)::

     $ pushd /usr/local/src
     $ wget https://github.com/rogerbinns/apsw/releases/download/3.8.9-r1/apsw-3.8.9-r1.zip
     $ unzip apsw-3.8.9-r1.zip
     $ cd apsw-3.8.9-r1
     $ python setup.py fetch --all build --enable-all-extensions install test
     $ popd

   The tests take 5-10 minutes to run; you can omit if you want to live
   dangerously, or proceed in another terminal while they run.

   You can also install APSW at the system level and configure your virtualenv
   to pass system modules through.

   .. warning:: APSW version 3.8.9, and hence SQLite 3.8.9, or higher is
                required. This is because prior versions of SQLite incorrectly
                enforce memory limits that QUAC depends on, leading to a
                memory leak. See the 3rd item in the `release notes
                <http://www.sqlite.org/releaselog/3_8_9.html>`_ and the
                `relevant commit
                <http://www.sqlite.org/cgi/src/vinfo/6fc4e79a2350295a?sbs=0>`_.

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


Self-compile
============

This installation method is useful when internet access is available and/or
system libraries are insufficient. Root access is not required.

.. warning:: This installation method is unsupported and poorly tested. Use it
             only as a last resort.

Prerequisites
-------------

* A staging machine with git, :code:`pip` (either Python 2 or 3 is fine),
  :code:`wget`, and internet access.

* Target machine needs basic dependencies such as GNU Make 3.81 and
  C/C++/Fortran compilers. Exactly what is currently unknown, but it "Works
  For Me™" on a RHEL6.6 box.

Install :code:`pip2pi`
----------------------

It's OK if you install :code:`pip2pi` using a different Python version than
you will be using for QUAC, as it's only used to build a :code:`pip`
repository on the staging machine.

::

   $ pip install pip2pi


Prepare the dependency package
------------------------------

In this step, you will download source code for QUAC's dependencies and create
a package that can be transferred elsewhere. After unpacking QUAC into
:code:`$QUACBASE`::

   $ deactivate          # if you have a virtualenv active
   $ cd $QUACBASE
   $ ./misc/manual-download

The script will create a file :code:`deps.tar.gz`. Copy this to your target
QUAC working directory.

Compile and install
-------------------

On the target machine::

   $ cd $QUACBASE
   $ tar xf deps.tar.gz
   $ ./misc/manual-install

Test
----

::

   $ ./runtests


..  LocalWords:  MYPREFIX Rv setuptools Sv defunkt QUACBASE deps src
