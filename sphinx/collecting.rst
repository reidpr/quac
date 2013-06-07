.. Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

Collecting data
***************

These are basic directions to collect and preprocess data so you can do
something awesome with them. These directions aren't comprehensive; you may
need to consult other sources to fill in some gaps.

.. note:: You may not need to do this. If you have collaborators who are
   already collecting data, you should probably in fact *not* do this. Just
   use their data.


Wikipedia
=========

Use the scripts ``wp-get-dumps`` and ``wp-get-access-logs``. No authentication
is needed, but you may wish to communicate with Wikimedia and/or mirror admins
if you are planning a large download.

These scripts use ``rsync``, so setting the environment variable
``RSYNC_PROXY`` may be needed depending on your firewall.


Twitter
=======

These instructions will help you collect and archive tweets as they appear in
the Streaming API. QUAC currently cannot acquire past tweets.

Set up authentication
---------------------

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
   customized.

   .. warning:: Because this file will contain authentication secrets, ensure
      that it has appropriate permissions.

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
