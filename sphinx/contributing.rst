.. Copyright (c) Los Alamos National Security, LLC, and others.

How to contribute
*****************

.. note:: This section is definitely a work in progress.


Basic workflow
==============

These are the rough steps we follow to get things done. Use your judgement
too!

Branching model
---------------

We try to keep the branching model simple. Right now, ours is fairly similar
to Scott Chacon's `"GitHub Flow"
<http://scottchacon.com/2011/08/31/github-flow.html>`_: ``master`` is stable;
do (non-trivial, i.e. multi-commit) work on topic branches; use pull requests
to ask for merging. One thing we do take from Driessen's `Git-Flow
<http://nvie.com/posts/a-successful-git-branching-model/>`_ model is an
avoidance of fast-forward merges in most cases.

We do tag versions. At this point, this is a planning tool rather than any
statement about stability.

Doing actual work
-----------------

#. Select an issue to work on and assign it to yourself. If there isn't one,
   create one. You might want to discuss your plans before diving in. Make
   sure no one else is working on it already.

   Sometimes your plans involve multiple issues. In this case, pick one to be
   the "leader" (you'll use this below).

#. Create (and switch to) a branch to do your work on::

     git checkout -b foo-branch

   Name the branch after the issue, including issue number, if that will be
   helpful.

#. Work, work, work. Commit lots. Use test-driven development. If a commit
   will close an issue, use the GitHub commit-message syntax to do so.

#. (Optional.) If your history is particularly insane, clean it up with ``git
   rebase``.

#. Merge ``master`` into your branch. Repair any conflicts that arise. (This
   is so the later merge in the opposite direction will be clean.)

#. Run the tests. If they don't pass, keep working until they do.

#. Push your branch to GitHub. If you're a core contributor (i.e., you have
   write access to ``reidpr/quac``), put your branch there. Otherwise, put it
   in your QUAC fork on GitHub.

#. Create a pull request. (Do this any time you want feedback --- you don't
   have to be ready to merge. However, in this case say clearly in the pull
   request comments that you don't want a merge yet.)

   Core contributors should transform the lead issue into a pull request with
   :samp:`hub pull-request -i {ISSUENUM}`.

   Others should comment on the lead issue with a pointer to the pull request;
   the pull request should in turn have a pointer to the issue.

#. Assign the issue to the ``master`` master (if you can) and add a comment
   requesting the pull.

#. Once your work is merged and pushed, remove your local branch.

Merging to ``master``
---------------------

#. Verify that you have a pull request, not just a branch.

#. Go to the pull request & read about what's going on.

#. ``git checkout master``

#. Merge the relevant branch::

     git merge --no-ff --no-commit remote/foo-branch

   (Note that you don't need to create a local branch; you can merge a remote
   branch directly.)

#. If there were any conflicts, abort the merge and complain.

#. Run the tests. If any failed, abort the merge and complain.

#. Commit, push.

#. Verify that the relevant issues were closed on GitHub.

#. Remove the branch::

     git push origin --delete {branch}

Cutting a release
-----------------

#. Make sure no issues remain for the GitHub milestone.
#. Edit release notes and commit.
#. Run the tests (they should pass).
#. ``make doc-web``
#. Tag the appropriate commit, e.g.: :samp:`git tag -a v0.{foo}`
#. ``git push``, ``git push --tags``
#. Close the relevant milestone.


Code style
==========

At a high level, follow the style of surrounding code. We more or less follow
PEP 8 style, except:

* 3 spaces per indent.
* Put parentheses around the conditions in ``if``, ``for``, etc.

Note that Reid is very picky about code style, so don't feel singled out if he
complains (or even updates this section based on your patch!). He tries to be
nice about it.

Docstrings
----------

Example (note extra indent)::

   def whois(number):
      '''Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer ac
         semper eros. Curabitur ullamcorper tortor et nibh lobortis, ut
         ultrices sapien aliquet.

         >>> whois(8675309)
         jenny'''


Documentation
=============

Building the docs
-----------------

To build HTML::

   $ make doc

Eventually we may build a few other formats too (e.g., PDF via LaTeX).

Sometimes, Sphinx gets confused about removed files. In this case, before
building, try::

   $ (cd sphinx && make clean)

Conventions
-----------

```FIXME``` (i.e., interpreted text containing the word "FIXME", all caps)

::

   Chapter title (once per file)
   *****************************

   Heading 1
   =========

   Heading 2
   ---------

   Heading 3 (use sparingly)
   ~~~~~~~~~~~~~~~~~~~~~~~~~

Publishing to the web
---------------------

If you have write access to the master repository, you can update the web
documentation.

Prerequisites
~~~~~~~~~~~~~

Normally, HTML documentation is copied to ``doc/``, which is a regular old
directory that is ignored by Git. To publish to the web, that directory needs
to contain a Git checkout of the ``gh-pages`` branch (*not* a submodule). To
set that up:

::

   $ rm -Rf doc
   $ git clone git@github.com:reidpr/quac.git doc
   $ cd doc
   $ git checkout gh-pages


Publishing
~~~~~~~~~~

Just say ``make doc-web``. Note that it can sometimes take a few minutes for
the new version to be published.

