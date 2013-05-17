Writing documentation
*********************

Conventions
===========

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
=====================

If you have write access to Reid's repository, you can update the web
documentation.

Prerequisites
-------------

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
----------

Just say ``(cd sphinx && make web)``. Note that it can sometimes take a few
minutes for the new version to be published.
