.. Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

Installing QUAC
***************

QUAC can be installed on most UNIX-based systems, though installation is
easiest on OS X and Debian/Ubuntu. Patches to increase portability are very
welcome.

Summary
=======

#. Download the code using Git::

     git clone https://github.com/reidpr/quac.git

#. Install the dependencies using system-specific instructions below.

#. Build executables and the documentation::

     cd quac
     make

#. Run the tests (this is actually pretty important, as it tells you whether
   you've installed all the dependencies correctly)::

     ./runtests

   Some tests require additional data or resources; if they are not available,
   then the tests are skipped.

   (While some parts of QUAC will work if some tests fail, we recommend
   installing everything necessary to make them pass, as this will make your
   life much easier going forward.)

.. note:: If you plan to :doc:`contribute to QUAC <contributing>`, you should
          do two things differently. First, fork the repository on Github and
          clone your own fork instead. Second, the ``git`` wrapper `hub
          <https://github.com/defunkt/hub>`_ is recommended.


Installing dependencies
=======================

Most dependencies are available through (a) either the Debian/Ubuntu (Linux)
or Homebrew (OS X) package repositories and (b) PyPI Python package
repository. Your life will be a lot easier if you use one of the options in
(a), but if they is unavailable for some reason (e.g., you do not have root
and can't persuade your admins to install), there is a fall back method of
compiling the core dependencies yourself.

Note that there are some things, such as QGIS and profilers, which are not
strictly dependencies but can come in handy. These things are not installed by
all the methods below.

If you are on a current UNIX system and QUAC does not pass its tests after
dependency installation using the instructions below, that is a bug. Please
report it!


Debian/Ubuntu
-------------

`FIXME: This section is incomplete and out of date. Please improve it.`

Debian packages
~~~~~~~~~~~~~~~

Install these first.

* ``gdal-bin``
* ``gfortran``
* ``gnuplot``
* ``mercurial``
* ``libgeos-c1``
* ``python-anyjson``
* ``python-cmdtest``
* ``python-daemon``
* ``python-dateutil``
* ``python-dev``
* ``python-gdal``
* ``python-joblib``
* ``python-matplotlib``
* ``python-meliae`` (optional, for memory profiling, see `blog post
  <http://jam-bazaar.blogspot.com/2010/08/step-by-step-meliae.html>`_)
* ``python-numpy``
* ``python-oauth2``
* ``python-pip``
* ``python-psutil``
* ``python-pyicu`` (optional)
* ``python-sphinx``
* ``python-tz``
* ``randomize-lines``
* ``runsnakerun`` (optional, for profiling)

PyPI Python packages
~~~~~~~~~~~~~~~~~~~~

Install with ``pip install foo``.

* `isodate <https://pypi.python.org/pypi/isodate>`_ parsing and formatting
  of ISO dates, times, and intervals. Version 0.4.9 is required to avoid a
  bug. (A ``.deb`` (``python-isodate``) is available in ``wheezy`` and
  ``quetzal``, but it is too old.)

* `Django <https://www.djangoproject.com/>`_ contains a `GEOS wrapper
  <https://docs.djangoproject.com/en/dev/ref/contrib/gis/geos/>`_ which we
  use.

* `scikit-learn <http://scikit-learn.org/stable/index.html>`_ (v0.13) is a
  machine learning library.

* ``pyproj`` is an interface to the PROJ.4 library.

Other Python packages
~~~~~~~~~~~~~~~~~~~~~

* A `custom version <https://bitbucket.org/reidpr/tweetstream-reidpr>`_ of
  ``tweetstream`` Twitter library (hacked by Reid)

SciPy
~~~~~

QUAC needs SciPy version 0.11 or better.

Both Debian and Ubuntu only have 0.10, even in the bleeding-edge development
releases (as of 2/20/2013). You can install it with ``pip``. It's worth
looking at the `installation documentation for Linux
<http://www.scipy.org/Installing_SciPy/Linux>`_. Try:

#. Remove existing ``python-scipy`` package.
#. Install ATLAS: ``libatlas-base-dev libatlas3-base``
#. Remove old LAPACK: ``liblapack3``

Note that this does not get you a (supposedly significantly faster, but
probably not terribly important for us) optimized ATLAS. You can do that by
building it from source; directions are in ``README.Debian``.

One-file Python modules
~~~~~~~~~~~~~~~~~~~~~~~

Download the modules (they are single ``.py`` files) and place them somewhere
in your Python path (e.g., ``/usr/local/lib/python2.7/dist-packages``).

- `TinySegmenter <http://lilyx.net/tinysegmenter-in-python/>`_ is a compact
  tokenization library for Japanese.

QGIS
~~~~

`QGIS <http://www.qgis.org/>`_ is an open source GIS system. While Ubuntu
comes with QGIS, it is a little crusty. However, the QGIS project provides
package repositories with new versions; see the `download page
<http://hub.qgis.org/projects/quantum-gis/wiki/Download>`_. You probably want
the "release" one.

You only need QGIS if you want to use it to visualize stuff. It's not required
for processing.

Note: As of 1/2/2013, the ``qgis-plugin-grass`` package is not installable on
Debian Wheezy because it depends on ``grass641``, which is not available any
more (``grass642`` is). The workaround is to build the ``.deb`` from source as
explained in this bug report: http://hub.qgis.org/issues/6438


OS X
----

`FIXME: section is pretty much useless`

* SpatialLite

  - brew install libspatialite

* pysqlite

  - Must install pysqlite from source (pip won't work): http://code.google.com/p/pysqlite/
  - Modify setup.cfg by commenting out the line
    define=SQLITE_OMIT_LOAD_EXTENSION
  - python setup.py build_static (<---Note the static part!)
  - sudo python setup.py install
  - See http://stackoverflow.com/a/1546162
  - EDIT db_glu.py with path to libspatialite  (e.g., if you installed from brew, /usr/local/lib/libspatialite.dylib )


Self-compile
------------

This method should only be used if one of the others does not work.
Essentially, it re-implements the most basic functionality of a package
manager, and it does so rather poorly and without regard to what you already
have installed.

It does not require root, and it will take a little while to run, since it has
to download and compile a fair amount of stuff. There are separate scripts to
download and install, in case you want to QUAC on a system that doesn't have
good access to the Internet.

Prerequisites:

* Some basic dependencies such as GNU Make 3.81 and C/C++/Fortran compilers.
  Exactly what is currently unknown, but it "Works For Me™".

* The `Environment Modules <http://modules.sourceforge.net/>`_ package. You
  probably have this if your system has a ``module`` command. This isn't
  strictly needed, as you can get the same effect by editing your shell init
  files appropriately.

The below assumes that you have unpacked QUAC into ``$QUACBASE``.

First, install the dependencies:

.. code-block:: sh

   mkdir $QUACBASE/deps
   cd $QUACBASE/deps
   ../misc/manual-download  # creates $QUACBASE/deps/src
   ../misc/manual-install

Optional:

* ``manual-install`` takes an argument which is the number of processes to use
  while compiling (``make -j``).

* You can run ``manual-download`` anywhere and move the resulting ``src``
  directory into ``$QUACBASE/deps`` manually.

Second, configure your environment. Add following to your ``.bashrc``.

.. code-block:: sh

   module use --append $QUACBASE/misc
   module load quac-module

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
