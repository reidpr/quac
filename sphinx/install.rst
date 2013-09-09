.. Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

Installing QUAC
***************

QUAC can be installed on most UNIX-based systems.

Summary
=======

#. Install the dependencies below.

#. Download the code using Git::

     git clone https://github.com/reidpr/quac.git

#. Build executables and the documentation::

     cd quac
     make

#. Run the tests (this is actually pretty important, as it tells you whether
   you've installed all the dependencies correctly)::

     ./test.sh

   Some tests require additional data or resources; if they are not available,
   then the tests are skipped.

   (While some parts of QUAC will work if some tests fail, we recommend
   installing everything necessary to make them pass, as this will make your
   life much easier going forward.)

.. note:: If you plan to :doc:`contribute to QUAC <contributing>`, you
          should fork the repository on Github and clone that fork instead.

Installing dependencies on Debian/Ubuntu
========================================

`FIXME: This section is incomplete and out of date. Please improve it.`

`FIXME: Turn these lists into a chart with .deb, pip, and source distribution
columns.`

You need Git to install QUAC and run the tests. The wrapper `hub
<https://github.com/defunkt/hub>`_ is also recommended if you are going to
hack on QUAC at all.

Debian packages
---------------

Install these guys first.

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
--------------------

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
---------------------

* A `custom version <https://bitbucket.org/reidpr/tweetstream-reidpr>`_ of
  ``tweetstream`` Twitter library (hacked by Reid)

SciPy
-----

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
-----------------------

Download the modules (they are single ``.py`` files) and place them somewhere
in your Python path (e.g., ``/usr/local/lib/python2.7/dist-packages``).

- `TinySegmenter <http://lilyx.net/tinysegmenter-in-python/>`_ is a compact
  tokenization library for Japanese.

QGIS
----

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


Installation on OS X
====================

`FIXME: these are out of date`

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


Installation using self-compile
===============================

`FIXME: Convert into script (pair: download and install). In this case,
probably don't need Stow.`

This assumes that:

* You do not have root access, and you have an environment variable
  ``$MYPREFIX`` which is the root of your install directory.

* Your system has some basic dependencies such as GNU Make 3.81, ``gcc``, and
  a Fortran compiler.

Basic recipe for compiling C programs and libraries
---------------------------------------------------

.. code-block:: sh

   wget http://foo.com/foo-1.0.tar.gz
   tar xjf foo-1.0.tar.gz
   pushd foo-1.0
   ./configure --enable-python --prefix=$MYPREFIX
   make
   make test    # optional
   make install DESTDIR=$MYPREFIX/stow/foo-1.0
   cd $MYPREFIX/stow/foo-1.0
   mv .$MYPREFIX/* .
   rm -Rv home  # assumes home directories are in /home
   cd ..
   stow -Sv foo-1.0
   popd

Bootstrap ``stow``
------------------

It is highly recommended that you install everything with GNU Stow, as this
lets you easily upgrade or remove packages you compiled. Here is a basic
recipe to compile Stow and then stow it with itself:

.. code-block:: sh

   wget http://ftp.gnu.org/gnu/stow/stow-2.2.0.tar.bz2
   tar xjf stow-2.2.0.tar.bz2
   pushd stow-2.2.0
   ./configure --prefix=$MYPREFIX
   make
   make install DESTDIR=$MYPREFIX/stow/stow-2.2.0
   cd $MYPREFIX/stow/stow-2.2.0
   mv .$MYPREFIX/* .
   rm -Rv home     # assumes home directories are in /home
   cd ..
   PERL5LIB=stow-2.2.0/share/perl5 stow-2.2.0/bin/stow -Sv stow-2.2.0
   stow --version  # test it
   which stow      # using correct stow?
   popd

Install Python
--------------

Python is not too hard to compile using the recipe above. Use:

.. code-block:: sh

   wget http://www.python.org/ftp/python/2.7.5/Python-2.7.5.tar.bz2
   unset PYTHONHOME
   ./configure --enable-shared --enable-unicode=ucs4 --prefix=$MYPREFIX
   make OPT=-O3
   export PYTHONHOME=$MYPREFIX
   python-config --prefix  # should be just $MYPREFIX, without stow directory

.. warning:: Python does some `sneaky following of symlinks
             <http://www.velocityreviews.com/forums/t331589-is-there-any-way-to-make-python-play-well-with-stow.html>`_
             to figure out what it should report in things like
             ``python-config --prefix``. By setting ``PYTHONHOME`` to
             ``$MYPREFIX/lib/python2.7`` in your ``.bashrc``, you override
             this, but note that you must *unset* ``PYTHONHOME`` during Python
             builds.

Bootstrap ``pip``
-----------------

See:

* http://www.pip-installer.org/en/latest/installing.html
* http://cournape.wordpress.com/2008/07/05/using-stow-with-setuptools/

Notes:

* Many packages include an identical ``site.py``, which ``stow`` will flag as
  a conflict. It seems to not really matter which one is used. I installed the
  one from ``distribute``.

* You can install from a pre-downloaded ``.tar.gz`` by specifying a file name
  instead of a package name.

Steps:

#. Install `setuptools <https://pypi.python.org/pypi/setuptools>`_:

.. code-block:: sh

   wget https://pypi.python.org/packages/source/s/setuptools/setuptools-1.1.4.tar.gz
   tar xzf setuptools-1.1.4.tar.gz
   pushd setuptools-1.1.4
   python setup.py install --single-version-externally-managed --record=$MYPREFIX/stow/setuptools-1.1.4/install.log --prefix $MYPREFIX/stow/setuptools-1.1.4
   cd $MYPREFIX/stow
   stow -Sv --ignore='install\.log' setuptools-1.1.4
   popd

#. Install `pip <http://pypi.python.org/pypi/pip>`_ in the same way.


..  LocalWords:  MYPREFIX Rv setuptools Sv
