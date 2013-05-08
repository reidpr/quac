Dependencies
************

Installation of Twepi has been documented only on Ubunti Linux ("Precise
Pangolin"), though it also runs on Macs and a few Red Hat variants. Probably
any UNIX would be fine.

It requires Python 2.7 and some other stuff listed below. Note that depending
on what you are doing, you might not need all the dependencies. Use your
judgement.

`FIXME: This section may be incomplete. Please improve it.`

`FIXME: Turn these lists into a chart with .deb, pip, and source distribution
columns.`

Debian packages
===============

Install these guys first.

* ``gdal-bin``
* ``gfortran``
* ``gnuplot``
* ``mercurial``
* ``libgeos-c1``
* ``python-anyjson``
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
* ``python-pyicu`` (optional)
* ``python-sphinx``
* ``python-tz``
* ``randomize-lines``
* ``runsnakerun`` (optional, for profiling)

PyPI Python packages
====================

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
=====================

* A `custom version <https://bitbucket.org/reidpr/tweetstream-reidpr>`_ of
  ``tweetstream`` Twitter library (hacked by Reid)

SciPy
=====

Twepi needs SciPy version 0.11 or better.

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
=======================

Download the modules (they are single ``.py`` files) and place them somewhere
in your Python path (e.g., ``/usr/local/lib/python2.7/dist-packages``).

- `TinySegmenter <http://lilyx.net/tinysegmenter-in-python/>`_ is a compact
  tokenization library for Japanese.

QGIS
====

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

Installing on Mac OS
====================

Running QUAC on a Mac involves `brew` and `pip`. On 10.7, the following is enough to make most of the tests pass (except for ICU & Disco stuff and modulo bugs). See also bugs tagged `mac`.

Note that many of these items are automatically installed dependencies.

Brew
----

::

    $ brew list | cat
    emacs
    freexl
    gdal
    gdbm
    geos
    gfortran
    giflib
    git
    gmp
    jpeg
    libgeotiff
    libmpc
    libspatialite
    libtiff
    lzlib
    mercurial
    mpfr
    pkg-config
    proj
    python
    readline
    sqlite
    wget

pip
---

::

    $ pip list
    distribute (0.6.36)
    Django (1.5.1)
    docutils (0.10)
    git-remote-helpers (0.1.0)
    isodate (0.4.9)
    Jinja2 (2.6)
    joblib (0.7.0d)
    matplotlib (1.2.1)
    numpy (1.7.1)
    Pygments (1.6)
    pyproj (1.9.3)
    pysqlite (2.6.3)
    python-dateutil (2.1)
    pytz (2013b)
    scikit-learn (0.13.1)
    scipy (0.12.0)
    six (1.3.0)
    Sphinx (1.2b1)
    vboxapi (1.0)
    wsgiref (0.1.2)

