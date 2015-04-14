.. Copyright (c) Los Alamos National Security, LLC, and others.

Preprocessing data
******************

Typically, raw data direct from collection is not too useful. QUAC implements
a preprocessing step to translate it into more pleasant formats as well as do
some preliminary analysis. This section describes the steps to do that.

.. contents::
   :depth: 2
   :local:

.. note::

   All times and dates are in UTC except as otherwise noted.

Twitter
=======

Overview
--------

QUAC's Twitter pipeline has three basic steps:

#. Collect tweets using the streaming API. (``collect`` script.)

#. Convert the tweets from the raw JSON, de-duplicate and clean them up, and
   produce nicely organized and ordered TSV files. (``parse.mk`` makefile.)

#. Geo-locate tweets that do not contain a geotag. (``geo.mk`` makefile.) (But
   see issue `#15 <https://github.com/reidpr/quac/issues/15>`_.)


File organization
-----------------

A fully populated data directory looks something like this:

* :samp:`raw/` --- Raw JSON tweets fresh from the Streaming API.

  * :samp:`2012-04/` --- Tweets from ``collect``. Each month gets its own
    directory.

    * :samp:`20120401_003115{.json.gz}` --- Sequence of JSON tweet objects.
      *Note:* As of roughly April 14, 2014, most tweets contain spurious
      newlines due to the erroneous way that QUAC handles
      ``Transfer-Encoding: chunked`` HTTP data. Our parsing strategy works
      around this problem. We plan to fix this in Issue #8.

    * :samp:`20120401_003115{.stats}` --- Text file containing a few statistics
      about the above.

    * :samp:`20120401_003115{.2012-03-31.raw.tsv}` --- Direct TSV translation
      of tweets from March 31 contained in the JSON file above (i.e., still
      contains duplicates and is in arbitrary order).

    * :samp:`20120401_003115{.2013-04-01.raw.tsv}` --- A given JSON file can
      have tweets from multiple days, so it may produce more than one
      ``.raw.tsv`` file.

    * :samp:`20120401_003115{.d}` -- Makefile listing dependencies related to
      the above JSON and ``.raw.tsv`` files.

    * ... (lots more of the above)

  * :samp:`legacy/` --- Subdirectories don't have to be named after dates.
    (Perhaps you have some existing Twitter data that were not collected with
    QUAC.)

  * ... (more subdirs)

* :samp:`pre/`

  * :samp:`2012-03-31{.all.tsv}` --- Processed tweets from March 31 from all
    raw JSON files. No duplicates and in ascending order by tweet ID.

  * :samp:`2012-03-31{.geo.tsv}` --- Subset of the above that contain a
    geotag.

  * ... (two ``.tsv`` per day in the data)

  * :samp:`metadata` --- Python pickle file summarizing metadata for the above
    files.

* :samp:`geo/` --- `FIXME`

In addition to the above, you will find ``.log`` files scattered about. These
are simply log files produced during processing.


File formats
------------

Raw JSON tweets
~~~~~~~~~~~~~~~

Each raw tweet file (``.json.gz``) is a gzipped sequence of JSON-encoded
tweets in the `format documented by Twitter
<https://dev.twitter.com/docs/platform-objects>`_, separated by newlines
(i.e., a file cannot be parsed as a single JSON object). Non-tweet objects do
appear; these are also JSON encoded. Newlines do not appear within encoded
tweets, so they can safely be used as a separator. Files are named with a
timestamp of when collection started for that file (time zone is *local*, a
historical artifact which will not be fixed -- be careful!) and placed in a
1-level hierarchy by year and month. The collection process caps the number of
tweets in each raw file to a "reasonable" number that changes occasionally.

Along with each ``.json.gz`` is a ``.stats`` file. This contains a few
statistics about the raw file's data, though its key purpose is simply to mark
that the collector closed the tweet file in an orderly way. Bare ``.json.gz``
files may be still in progress, broken, etc. and should be read with caution.
Tweets are Unicode and indeed contain high characters, so care must be taken
in handling character encodings.

`collect` saves the raw bytes of each tweet it receives from the Twitter
Streaming API, without any parsing or encoding/decoding. There are a few
quirks of this stream. (I am pretty sure, but not 100% sure, that these are
all real, and not quirks of Python -- they're consistent between `curl`,
Firefox, and my Python code.) These quirks do not appear to affect the
parsability of the JSON.

* While the encoding of the output is ostensibly UTF-8, it appears that high
  characters are escaped with the "\uXXXX" notation. For example:

  .. code-block:: text

     "text":"\u2606\u2606\u2606\u2606\u2606#Cruzeiro"

* Some text has excessive escaping. For example, forward slashes do not need
  to be escaped, but they are anyway:

  .. code-block:: text

     "source":"\u003Ca href=\"http:\/\/blackberry.com\/twitter"

TSV files
~~~~~~~~~

The raw tweet files are not so convenient to work with: JSON parsing is slow,
and tweets can be duplicated and out of order (including between files, which
makes parallelization difficult). Therefore, we pre-process the JSON into a
TSV format which addresses these issues. The final product is a pair of TSV
files for each day:

* :samp:`YYYY-DD-MM.{all}.tsv` --- For each day, we build one
  tab-separated-values (TSV) file containing tweets created on that day, in
  ascending ID order. There is no header line, no quoting, and no
  within-record newlines or tabs (these are stripped before storing the
  tweets). There is some other cleaup that goes on as well; consult the source
  code for this. The encoding is UTF-8. The files contain the following
  possibly-empty fields, in this order (note that field names generally
  correspond to those in the JSON; refer to the Twitter docs):

  #. *id*: Tweet ID from Twitter (64-bit integer)
  #. *created_at*: When the tweet was created, in `ISO 8601 format
     <http://en.wikipedia.org/wiki/ISO_8601>`_.
  #. *text*: The actual "message"; free text
  #. *user_screen_name*: free text with some restrictions
  #. *user_description*: free text
  #. *user_lang*: `ISO 639-1 <http://en.wikipedia.org/wiki/ISO_639-1>`_
     language code set by user. Note that this is a fairly unreliable means of
     determining the language of ``text``. `FIXME: take advantage of new
     lang tweet attribute when it comes out.`
  #. *user_location*: free text
  #. *user_time_zone*: self-selected from a few dozen options
  #. *location_lon*: longitude of geotag (WGS84)
  #. *location_lat*: latitude of geotag
  #. *location_src*: code indicating source of geotag; one of:

     * ``co``: ``coordinates`` attribute (GeoJSON)
     * ``ge``: ``geo`` attribute (an older form of official geotag) `FIXME`
     * ``lo``: coordinates appearing in user ``location`` field `FIXME`
     * ... `FIXME`

* :samp:`YYYY-DD-MM.{geo}.tsv` --- The subset of the above which have a
  geotag.

There are also intermediate TSV files (``.raw.tsv``) which are in the above
format but have not yet had de-duplication and re-ordering. Downstream
applications should ignore them.

Preprocessing metadata file
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This file is a pickled Python dictionary containing metadata about the
directory of preprocessed TSV files. It currently contains one item:

#. ``days`` is a ``dict`` listing metadata for the daily TSV files above. Keys
   are ``datetime.date`` instances, and values are dictionaries with the
   following fields:

   * *count*: Number of tweets
   * *count_geotag*: Number of geotagged tweets
   * *min_id*: Minimum tweet ID in the file
   * *max_id*: Maximum tweet ID in the file

*Note: The metadata file used to contain information about the raw tweet files
as well. This proved to be not so useful, and so it hasn't been reimplemented
in the new make-based processing scheme.*

Geo-located tweets
~~~~~~~~~~~~~~~~~~

`FIXME`

* TSV, one per day
* Tweet ID, pickled Geo_GMM instance
* GMM even if geotagged

Alternatives that were considered and rejected
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We tried the following and ultimately rejected them (for now). A key
requirement (as of 2/21/2013) is that we'd like convenient parallel access and
not to mess with setting up servers.

* Postgres: We tried using Postgres, which is a very nice open source RDBMS
  that has great spatial support (PostGIS), but it was just too slow. Also, it
  requires setting up a server and doesn't lend itself to a distributed
  approach.

* DBM-style databases (e.g., BerkeleyDB): We need key/tuple storage, not just
  key/value (unless we want to do our own pickling of Python objects into
  values, which seems lame).

* SQLite/SpatiaLite: Again, rather slow, and overkill since we need key/tuple
  storage. Doesn't support streaming or parallel access very well.

* ZODB: This is a Python-native object database (from the Zope project). I
  implemented it as far as actually storing data, but the documentation is
  poor (e.g., the ZODB Book recommends a technique for subtransactions that
  doesn't work any more), the interface is a bit awkward, it produces several
  files per database, and the databases are rather large (a subset of 8 fields
  is nearly as large as the gzipped raw tweet files).

* NoSQL: There are lots of very hip NoSQL databases (e.g. CouchDB, MongoDB,
  etc.). However, none seem to offer both an embedded option (i.e., no server
  process) and key/tuple (document- or column-oriented?) rather than simply
  key/value.


Wikimedia pageview logs
=======================

Overview
--------

The pipeline for Wikimedia data (Wikipedia and related projects) is simpler.
We acquire them using the ``wp-get-access-logs`` script and then preprocess
them into HDF5 time series files using the ``wp-preprocess.mk`` makefile.

File organization
-----------------

A fully populated data directory looks (in part) something like this:

* :samp:`raw/` --- Raw text files direct from WMF. Note that some of these
  files contain breakage.

  * :samp:`2012/`

    * :samp:`2012-04/` --- Article access counts ("pageviews") of intervals
      ending in April 2012. Each month gets its own subdirectory.

      * :samp:`pagecounts-20120428-130001.gz` --- Number of times each URL was
        served during 12:00:00 through 12:59:59 on April 28.

      * ... (one file for each hour starting March 31, 23:00:00 through April
        30, 22:00:00)

* :samp:`timeseries/` --- Time series files as described below.

.. note::

   We do not download or use the :samp:`projectcounts` files, which contain
   the total number of URLs served from each project (e.g., Norwegian
   Wiktionary), because many of them are broken and must be re-generated
   anyway. (See issue `#81 <https://github.com/reidpr/quac/issues/81>`_.)

Article filtering
-----------------

Three classes of articles are excluded from the time series files:

#. Articles with anything other than lowercase A to Z in the language
   (project) code. This excludes invalid project codes as well as
   non-Wikipedia wikis (e.g., Wiktionary and Wikibooks) and mobile requests
   for Wikipedia articles (e.g., requests to :samp:`en.m.wikipedia.org`).

   I'm not very happy about the latter; the reason has to do with how the
   files are sorted. See `issue #108
   <https://github.com/reidpr/quac/issues/108>`_.

#. Articles with "funny" characters in their URLs. Specifically, only the
   following URL characters are passed through:

   * ASCII alphanumeric (A--Z upper and lower case, plus digits 0--9).
   * The rest of the "unreserved set", except for dot: :samp:`-_~`
   * Some of the reserved set: :samp:`!*();@,`
   * Percent (:samp:`%`), to allow encoded URLs through.

   For example, this excludes articles:

   * In non-main namespaces (these titles contain a colon).
   * With a slash in the title (e.g., "Input/output").
   * Accessed with non-percent-encoded high characters (code point ≥128).

   See:

   * http://en.wikipedia.org/wiki/Percent-encoding
   * http://en.wikipedia.org/wiki/Wikipedia:Naming_conventions_%28technical_restrictions%29

   This is done to make downstream processing easier and whilshoulde excluding
   a minimal set of articles.

#. Articles with less than a threshold number of requests in a given month.
   The zero vector is inferred for such months. This avoids storing
   low-traffic article time series fragments that are too rarely accessed or
   noisy to be useful in analysis.

   The threshold is configurable at :samp:`wkpd.keep_threshold`.

Note that this does not categorically exclude non-Wikipedia wikis such as
Wiktionary or Wikibooks, nor mobile requests for Wikipedia.

Pagecount file format
---------------------

The file format of the pagecount files is `documented by WMF
<http://dumps.wikimedia.org/other/pagecounts-raw/>`_. There are some quirks:

#. The timestamp in the filename is the *end* of the hour recorded in the
   file. Often, these timestamps are a few seconds past the hour; we ignore
   this.

#. Filesystem timestamps are not reliable, especially in the older parts of
   the data. That is, sometimes older files have newer timestamps, and the
   interval between consecutive files can be much less than one hour
   (sometimes less than a second, making them equal on many filesystems).

#. The files are ASCII, with high bytes in article URLs percent-encoded. We do
   not decode them because (a) it saves significant time and (b) there are
   apparently non-UTF-8 encodings in use. (I believe the URL encoding is
   selected by the browser.)

   An artifact of (b) is that article counts can be split. For example, the
   Russian article Люди_Икс
   (i.e., the X-Men comic series) can be accessed at both of the following
   URLs:

   * (UTF-8) http://ru.wikipedia.org/wiki/%D0%9B%D1%8E%D0%B4%D0%B8_%D0%98%D0%BA%D1%81
   * (Windows-1251) http://ru.wikipedia.org/wiki/%CB%FE%E4%E8_%C8%EA%F1

   Other encodings (e.g., ISO 8859-5, :code:`%BB%EE%D4%D8_%B8%DA%E1` and
   KOI8-R, :code:`%EC%C0%C4%C9_%E9%CB%D3`) do not work. Figuring out this mess
   is something I'm not very interested in. How WMF does it, I have no idea.

   We do, however, normalize spaces into underscores. I believe this may be
   incomplete (see issue #77).

#. There have been periods of modest `underreporting
   <http://dumps.wikimedia.org/other/pagecounts-ez/projectcounts//readme.txt>`_,
   with up to 20% of hits unrecorded. We assume such underreporting is random
   and do not try to correct it. Because our analysis works on fraction of
   total traffic rather than raw hit counts, the effect should be minimal.


Time series files
=================

These files store hourly time series of some event count, for example n-gram
occurences in Twitter messages or Wikpedia article hits.

We have three main goals for these files:

1. Provide a unified format for many types of things that can be counted over
   time, to feed into a unified analysis framework.

2. Facilitate parallel access to the dataset without specialized I/O
   techniques (such as MPI parallel I/O).

3. Facilitate reasonable performance for continually updated data written in
   time-major order (e.g., each hour, a new Wikipedia access log file arrives
   giving hits for all pages) as well as fast reading in item-major order
   (e.g., quickly iterate through each Wikipedia article's complete time
   series). That is, we want to accomplish a data transpose implicitly during
   the preprocessing phase.


Raw file format
---------------

Named time series are stored in SQLite3 database files. A directory contains
multiple databases *fragmented* by time (month); within each file are multiple
tables *sharded* by time series name (by hashing).

Currently, time series must be hourly, and fragments are one per month. We
have attempted to make the API extensible to remove these limitations without
excessive disruption to existing code.

Time series vectors can be any NumPy data type. If any time series fragment is
present in a fragment file, it is complete (i.e., a value is present for each
hour in the month.)

Functionality is provided for pruning (and replacing with zeroes on fetch)
fragments with small magnitude.

For example:

* :samp:`ts/` --- Time series directory (can be named arbitrarily)

  * :samp:`2007-12-01.db` --- Data for the month of December 2007.

    * :samp:`data0` --- Table containing data for time series whose name
      hashed mode :math:`n` is 0.

    * :samp:`data1` --- Table containing data for time series whose name
      hashed mode :math:`n` is 1.

    * ... (additional shards)

  * :samp:`2008-01-01.db` --- Data for the month of January 2008.

    * ... (shards)

  * ... (one file for each month in the dataset)

A data table has the following columns. All are :samp:`NOT NULL`.

* :samp:`name`: Time series name (text, primary key).

* :samp:`dtype`: NumPy data type character code (text).

* :samp:`total`: Sum of element absolute values in the time series fragment
  (double, regardless of fragment data type).

* :samp:`data`: Content of time series fragment. This is either a memory dump
  of the corresponding NumPy object (i.e., a C array), or the same memory dump
  compressed with zlib (if :samp:`total` is below a threshold).

Each database also contains a :samp:`metadata` table with various parameters.

.. note::

   Data tables do not use explicit indexes, instead relying on SQLite's
   `WITHOUT ROWID <http://www.sqlite.org/withoutrowid.html>`_ feature coupled
   with maximum-size 64kB pages. Back-of-the-envelope calculations suggest
   this is the right choice performance-wise, but it has not been tested.

Use for Wikipedia article hits
------------------------------

Time series names for Wikipedia articles are the language concatenated with a
slash and the article URL, for example :samp:`en/Fever` or
:samp:`fr/Fi%C3%A8vre`. These time series are :samp:`np.float32` to save
space. Elements with the value 0 indicate *either* a zero value or no data.

For normalization and to resolve this ambiguity, language total time series
are also stored under the language code (e.g., :samp:`en` or :samp:`fr`, no
trailing slash) as :samp:`np.float64` to avoid floating-point summation
problems. Elements of these total vectors are either the total of all time
series of that language for that hour, or :samp:`NaN` if no hits at all in
that language were recorded. Under this system, it is still ambiguous whether
a given language did not exist or recorded no traffic, but these two
situations are close enough that we believe this is not a concern.

Typical analysis will divide an article time series by the language total time
series to obtain a fraction of total traffic with :samp:`NaN` elements for
missing data.


..  LocalWords:  pagecount samp badfiles
