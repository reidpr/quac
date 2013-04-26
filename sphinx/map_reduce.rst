Map-Reduce with ``makereduce``
******************************

Introduction
============

`Map-reduce <http://en.wikipedia.org/wiki/MapReduce>`_ [#]_ is a neat and easy
to use parallel programming paradigm. However, its implementations have some
issues:

- Industrial strength map-reduce frameworks (e.g., `Hadoop
  <http://en.wikipedia.org/wiki/Apache_Hadoop>`_, `Disco
  <http://discoproject.org/>`_) are difficult to install and use.

- Frameworks assume that nodes have no performant shared parallel filesystem
  like `Panasas <http://www.panasas.com/products/panfs>`_. Therefore, they
  implement a non-POSIX distributed filesystem using node-local storage (e.g.,
  Hadoop's HDFS).

  While this condition is simpler from a hardware perspective, if you don't
  have access to node-local disks for whatever reason (e.g., they don't
  exist), you're in a pretty inconvenient situation. Typically, clusters like
  this *do* have a nice parallel filesystem, but support for using it directly
  is poor or nonexistent. You can of course run a distributed filesystem on
  top of the parallel filesystem, but this is an unnecessary level of
  indirection and throws away the convenience of the parallel filesystem.

- Map-reduce jobs cannot be run incrementally; if new input data are added,
  the entire job must be re-run.

``makereduce`` is a simple wrapper included with QUAC that solves these
problems. It works on both a single node as well as in a SLURM allocation.


Example
=======

The basic paradigm is that the ``makereduce`` command creates a makefile which
you then run with ``make`` (either directly or wrapped).

This example implements a toy version of the classic "word count" example
using standard UNIX tools. ``makereduce`` also has a Python API which we do
not cover here.

Create sample input
-------------------

::

   $ echo -e 'foo bar baz\nfoo foo' > /tmp/foo1.txt
   $ echo -e 'bar' > /tmp/foo2.txt
   $ cat /tmp/foo*.txt
   foo bar baz
   foo foo
   bar


Define the *map* operator
-------------------------

This converts standard input into a sequence of key/value pairs, one per line.
The key can be any string and is separated from the value (which is opaque to
``makereduce`` but must not contain newline characters) by a single space.

We will use ``tr`` for this::

  $ cat /tmp/foo*.txt | tr '[:blank:]' '\n'
  foo
  bar
  baz
  foo
  foo
  bar

(Note that in the standard map-reduce word count examples, the mapper emits
the value 1 for each word. ``makereduce`` is perfectly happy with null values,
and counting the length of a set is the same as summing a set of 1's of the
same size, so we do the former.)

Define the *reduce* operator
----------------------------

This converts a sequence of key/value pairs from
the mapper, presented on standard input, into arbitrary output (typically
one output item per set of identical keys). All input pairs with the same
key are adjacent in the input, but there are otherwise no input ordering
guarantees.

We will use ``uniq`` to print each input word with the number of times it
occurred::

  $ echo -e 'b\nb\na\nc\nc\nc' | uniq -c
  2 b
  1 a
  3 c

Test the operators together
---------------------------

::

  $ cat /tmp/foo*.txt | tr '[:blank:]' '\n' | sort -sk1 | uniq -c
  2 bar
  1 baz
  3 foo

Congratulations, you've just run map-reduce in serial mode, with one mapper
and one reducer! The next step is to run lots of mappers and reducers in
parallel, which is one thing ``makereduce`` helps with.

Prepare the job
---------------

The ``makereduce`` command is used to prepare a makefile as well as a SLURM
job file::

  $ makereduce -m 'tr "[:blank:]" "\n"' \
               -r 'uniq -c > out/$RID' \
               -p 2 \
               /tmp/mrjob /tmp/foo*.txt

What's going on here?

* ``-m`` defines the map operator. This can be any shell pipeline; watch
  quoting carefully!

* ``-r`` defines the reduce operator. The environment variable ``$RID`` is
  the reducer ID; this is important for keeping output from different
  reducers separate.

* ``-p`` defines the number of partitions. There is one reducer per
  partition, so this limits the available parallelism for the reduce step
  (as well as downstream map-reduce jobs unless you take other measures).
  The limiting factor to keep in mind is that if you have :math:`n` input
  files and :math:`p` partitions, you will need :math:`n \times p`
  temporary files, which can grow quickly.

* ``/tmp/mrjob`` is a directory in which to build the job.

* ``/tmp/foo*.txt`` are the input files. There should be lots of these, as
  only one mapper is run per input file. They can live anywhere but must
  have unique filenames even if they are in multiple directories.

Run the job with make
---------------------

This approach is simpler but is limited to the parallelism available in a
single machine. If you need more, you can use a SLURM cluster (see the next
step). For example::

  $ cd /tmp/mrjob
  $ ls -R
  .:
  Makefile  slurm_job  tmp

  ./out:

  ./tmp:

``makereduce`` has created two files and two directories:

* ``Makefile`` is what you expect; it defines the dependency graph among
  the temporary and job management files.

  **Note:** Output files created by your reduce operator are *not* included
  in the dependency graph. Therefore, Make has no idea if they are complete
  or not, so it's your responsibility to make sure they're not corrupted on
  re-runs (which may include new data). It's best practice to simply
  overwrite these each time the reducer is run.

* ``slurm_job`` is a SLURM batch file to run the Make job on multiple
  nodes.

* ``tmp`` is a directory containing various files used to contain
  intermediate results and manage job progress. ``make clean`` deletes
  everything in this directory.

* ``out`` is a convenience directory for your use. You don't have to put your
  output here, but you ought to have a good reason not to. ``make
  reallyclean`` deletes everything here as well as in ``tmp``.

You are now ready to run the job::

  $ make -j2
  [...FIXME...]
  $ ls -R
  .:
  Makefile  out  slurm_job  tmp

  ./out:
  0  1

  ./tmp:
  0.reduced  foo1.txt.0  foo1.txt.mapped  foo2.txt.1
  1.reduced  foo1.txt.1  foo2.txt.0       foo2.txt.mapped

Note that the subdirectories are now populated.

Your output is available with::

  $ cat out/*
  2 bar
  1 baz
  3 foo

Note that the output order has changed. In general, you must sort yourself
if you care about this order.

Run the job with SLURM
----------------------

::

  $ sbatch -N2 slurm_job -j4

Note that the number of nodes requested from SLURM and ``-j``, which is the
total number of tasks ``make`` will run simultaneously, must be coordinated
for good performance. The above might be appropriate for a cluster with two
cores per node. Memory could be a limitation also, along with myriad others.

Adding more input data
----------------------

One of the neat things that ``makereduce`` can do is add additional data
and then only re-run the parts of the job that are affected. For example::

  $ echo 'qux' > /tmp/foo3.txt
  $ cd /tmp/mrjob
  $ makereduce --update . /tmp/foo*.txt
  $ make -j2
  [...FIXME...]
  $ cat out/*
  2 bar
  1 baz
  3 foo
  1 qux

Note that only ``foo3.txt`` was mapped, because we already had mapper results
for ``foo1.txt`` and ``foo2.txt``.

What's next?
------------

For further help, say ``makereduce --help`` or see ``makr/grep.py`` for a
Python example.


Drawbacks
=========

``makereduce`` is pretty simple and has a number of limitations. If these are
a problem, perhaps you are better off with something else. Some of these could
be fixed, and others are more fundamental.

* Lower fault tolerance. If one of your nodes goes down, the job will stop.
  However, it will probably do so in a consistent state, and restarting will
  continue more or less where you left off.

* Line-oriented I/O. You are responsible for serializing your data to
  something without newlines, which is kind of annoying and wastes spacetime.

* Scaling is not as good. If you need to run 10,000 mappers in parallel,
  ``makereduce`` is probably not for you.

* As mentioned earlier, input filenames must be unique even if they came from
  different directories.

* No automatic chunking of input; ``makereduce`` cannot map a single file in
  parallel.


FIXME
=====

- sort tmpdir
- parallel sorts


.. Footnotes
   =========

.. [#] I know that it's usually spelled MapReduce, but I think InterCapping is
       stupid.
