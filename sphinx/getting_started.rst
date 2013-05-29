.. Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

Getting started
***************

These are basic directions to collect some tweets and put them in TSV files so
you can do something awesome with them. These directions aren't comprehensive;
you may need to consult other sources to fill in some gaps.

Install QUAC
============

#. Install the dependencies.

#. Grab the code using Git::

     git clone https://github.com/reidpr/quac.git

   *Note: This creates a read-only repository. If you plan to contribute to
   QUAC, you should fork the repo on Github and clone yours instead.*

#. Build executables and the documentation::

     cd quac
     make

#. Run the tests::

     ./test.sh

Collect some tweets
===================

*Note: You may not need to do this. If you have collaborators who are already
collecting tweets, you should in fact not do this. Just use their data.*

Set up Twitter
--------------

You need both a user account and an application, as well as four different
authentication parameters, to access the streaming API using OAuth.

#. Create an account on Twitter to use for collection. (I suggest you do not
   use your normal Twitter account, if you have one.)

#. Create a Twitter application (https://dev.twitter.com/apps; sign in as
   the user above).

#. Click *Create my access token*.

#. The four authentication parameters are on the Details tab (you may need to
   reload it after the above step).

   * consumer key
   * consumer secret
   * access token
   * access secret

Run the collector
-----------------

#. Create directories to hold the collected tweets (e.g., ``tweets``) and your
   configuration and logs (e.g., ``config``).

#. In ``config``, create a file ``sample.cfg``; look through the options in
   ``default.cfg`` and add to ``sample.cfg`` the ones that need to be
   customized. **Because this file will contain authentication secrets, ensure
   it has appropriate permissions.**

#. Run the collector for a while, e.g.::

     collect --verbose --config /path/to/sample.cfg

   (Type Control-C to stop.)

Build the TSV files
-------------------

::

   /path/to/quac/misc/parse.sh 1 /path/to/tweets

Doing it seriously
------------------

The above will get you a few tweets to play with. If you want to actually
collect tweets in a serious and reliable way (i.e., without gaps):

#. Run ``collect`` with the ``--daemon`` option, and set up ``logcheck`` to
   watch the log files and e-mail you if something goes wrong.

#. Set up a cron job to build the TSVs regularly, e.g.::

     27 3 * * *  nice bash -l -c '/path/to/quac/misc/parse.sh 4 /path/to/tweets >> /path/to/logs/parse.log'
