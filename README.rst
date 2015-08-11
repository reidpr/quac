About QUAC
==========

QUAC ("Quantitative analysis of chatter" or any related acronym you like) is a
package for acquiring and analyzing social internet content. Features:

* Reliable data collection and conversion of raw data into into easy-to-parse,
  de-duplicated, and well-ordered formats. We support:

  * Tweets from the `Twitter Streaming API
    <https://dev.twitter.com/docs/streaming-apis>`_.

  * Wikipedia hourly aggregate `pageview logs
    <http://dumps.wikimedia.org/other/pagecounts-raw/>`_.

  * Wikipedia edit history and related `XML dumps
    <http://meta.wikimedia.org/wiki/Data_dumps>`_.

* Estimate the origin location of tweets with no geotag. (But see `issue #15
  <https://github.com/reidpr/quac/issues/15>`_.)

* Careful preservation of Unicode throughout the processing pipeline.

* Various cleanup steps to deal with tweet quirks, including very rare ones
  (we've seen certain weirdnesses in only one of our 1.3+ billion tweets).
  That is, we deal with the special cases so you don't have to.

* Parallel processing using various combinations of Make, ``joblib``, and a
  simple map-reduce framework called QUACreduce which is included.

QUAC is copyright © 2012-2015 Los Alamos National Security, LLC, and others.
It is open source under the Apache license and was formerly known as Twepi
("Twitter for epidemic analysis").

Reporting bugs
--------------

Use our `list of issues <https://github.com/reidpr/quac/issues>`_. To maximize
the chances of your bug being understood and fixed, take a look at `"Three
parts to every good bug report"
<http://www.joelonsoftware.com/articles/fog0000000029.html>`_ (scroll down).

**That said, note that unlike many open source projects, we make a point of
being friendly to bug reporters, even newbies.** Therefore, please don't
hesitate to report a bug, even if you're inexperienced with QUAC or feel
unsure. In almost all cases you will tell us something useful, even if the
issue turns out not to be a bug per se, and we will support your efforts in
this regard.

If you find QUAC useful
-----------------------

Please send us a note at ``reidpr@lanl.gov`` if you use QUAC, even for small
uses, and/or star the project on GitHub. This type of feedback is very
important for continued justification of the project to our sponsors.

Note that for many uses of QUAC (especially research) you are ethically
obligated to cite it. For guidelines on how to do this, see the *Citing*
section of the documentation.

Science!
--------

We use QUAC for scientific research. To promote reproducibility, which is one
of the core values of science, we try to open-source the code that runs our
related experiments as well as QUAC itself. This code, and further information
about it, can be found in the directory ``experiments``.

For more information
--------------------

* Documentation is online at <http://reidpr.github.io/quac>. (Note: this may
  describe a different version of QUAC than the one you have.)

* Current documentation is rooted at ``doc/index.html``. (You'll probably need
  to build it first.)

* Most scripts have pretty help which you can print using the ``--help``
  option and/or look at in comments at the top of the script. Modules also
  usually have good docstrings.
