Getting started
***************

These are basic directions to collect some tweets and put them in TSV files so
you can do something awesome with them. These directions aren't comprehensive;
you may need to consult other sources to fill in some gaps.

Set up Twitter
==============

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

Install Twepi
=============

#. Install the dependencies.

#. Grab the code using Mercurial (a.k.a. ``hg``)::

     hg clone ssh://path/to/repo twepi

Collect some tweets
===================

#. Create directories to hold the collected tweets (e.g., ``tweets``) and your
   configuration and logs (e.g., ``config``).

#. In ``config``, create a file ``sample.cfg``; look through the options in
   ``default.cfg`` and add to ``sample.cfg`` the ones that need to be
   customized. **Because this file will contain authentication secrets, ensure
   it has appropriate permissions.**

#. Run the collector for a while, e.g.::

     collect --verbose --config /path/to/sample.cfg

   (Type Control-C to stop.)

#. Build the TSV files::

     cd tweets
     make -f /path/to/twepi/parse.mk all clean-rawtsv
