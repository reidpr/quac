About QUAC
==========

QUAC ("Quantitative analysis of chatter" or any related acronym you like) is a
package for acquiring and analyzing social internet content. Features:

* Reliably collect tweets from the Twitter Streaming API and convert them into
  an easy-to-parse, de-duplicated, well-ordered, and fast TSV format.

* Estimate the origin location of tweets with no geotag. (But see `issue #15
  <https://github.com/reidpr/quac/issues/15>`_.)

* Careful preservation of Unicode throughout the processing pipeline.

* Various cleanup steps to deal with tweet quirks, including very rare ones
  (we've seen certain weirdnesses in only one of our 1.3+ billion tweets).
  That is, we deal with the special cases so you don't have to.

* Parallel processing using various combinations of Make, ``joblib``, and a
  simple map-reduce framework called QUACreduce which is included. (But see
  `issue #33 <https://github.com/reidpr/quac/issues/33>`_.)

QUAC is copyright © 2012-2013 Los Alamos National Security, LLC, and others.
It is open source under the Apache license and was formerly known as Twepi
("Twitter for epidemic analysis").

Reporting bugs
--------------

Use our `list of issues <https://github.com/reidpr/quac/issues>`_. To maximize
the chances of your bug being understood and fixed, you should read `"Three
parts to every good bug report"
<http://www.joelonsoftware.com/articles/fog0000000029.html>`_ (scroll down).

If you find QUAC useful
-----------------------

Please send us a note at ``reidpr@lanl.gov`` if you use QUAC, even for small
uses, and/or star the project on GitHub. This type of feedback is very
important for continued justification of the project to our sponsors.

Note that for many uses of QUAC (especially research) you are ethically
oblicated to cite it. For guidelines on how to do this, see the *Citing*
section of the documentation.

For more information
--------------------

* Documentation is online at <http://reidpr.github.io/quac>. (Note: this may
  describe a different version of QUAC than the one you have.)

* Current documentation is rooted at ``doc/index.html``. (You'll probably need
  to build it first.)

* Most scripts have pretty help which you can print using the ``--help``
  option and/or look at in comments at the top of the script. Modules also
  usually have good docstrings.
