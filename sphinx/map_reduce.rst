.. Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

Map-Reduce with QUACreduce
**************************

Introduction
============

`Map-reduce <http://en.wikipedia.org/wiki/MapReduce>`_ is a neat and easy to
use parallel programming paradigm. [1]_ QUACreduce is a simple map-reduce
framework designed for situations where a unified, fast POSIX filesystem is
available (e.g., HPC clusters with `Panasas
<http://www.panasas.com/products/panfs>`_). It has the following features:

* Easy to install and use. No daemons or persistent workers are required, nor
  any firewall changes, nor root access.

* Takes advantage of node-local storage, if available, which need not persist
  between jobs. [2]_

* Map-reduce jobs can be run incrementally; if new input data are added, only
  computations which actually depend on the new data are redone.

* Data API is compatible with Hadoop Streaming.

QUACreduce runs on top of ``make`` for incremental processing and works on
both a single node as well as in a SLURM allocation.


Summary of API
==============

The basic paradigm is that map and reduce operators produce and accept
line-oriented input, with key and value separated by a single tab character.
[3]_ All characters except tab, return, and newline are permitted in keys and
values (though this is untested). Null values are permitted; in this case the
separating tab may or may be omitted. [4]_ The last line of the stream must
end in a newline.

The ``quacreduce`` command implements this API by creating a makefile, which
you then run with ``make`` (either directly or wrapped).

QUACreduce also has a Python API which we do not cover here (see
``lib/qr/wordcount.py`` and other examples in the same directory).

Example
=======

.. NOTE: This example is tested in tests/quacreduce.script; make sure the two
   examples match.

This example implements a toy version of the classic "word count" example
using standard UNIX tools.

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

We will use ``tr`` for this::

  $ cat /tmp/foo*.txt | tr '[:blank:]' '\n'
  foo
  bar
  baz
  foo
  foo
  bar

(Note that in the standard map-reduce word count examples, the mapper emits
the value 1 for each word. QUACreduce is perfectly happy with null values,
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

  $ cat /tmp/foo*.txt | tr '[:blank:]' '\n' | sort -sk1 -t '	' | uniq -c
  2 bar
  1 baz
  3 foo

Congratulations, you've just run map-reduce in serial mode, with one mapper
and one reducer! The next step is to run lots of mappers and reducers in
parallel, which is one thing QUACreduce helps with.

Prepare the job
---------------

The ``quacreduce`` command is used to prepare a makefile as well as a SLURM
job file::

  $ quacreduce --map 'tr "[:blank:]" "\n"' \
               --reduce 'uniq -c > out/%(RID)' \
               --partitions 2 \
               /tmp/mrjob /tmp/foo*.txt

What's going on here?

* ``--map`` defines the map operator. This can be any shell pipeline; watch
  quoting carefully! The CWD is the job directory.

* ``--reduce`` defines the reduce operator. The variable ``%(RID)`` is the
  reducer ID; this is important for keeping output from different reducers
  separate. It is substituted by QUACreduce during job construction.

* ``--partitions`` defines the number of partitions. There is one reducer per
  partition, so this limits the available parallelism for the reduce step (as
  well as downstream map-reduce jobs unless you take other measures). The
  limiting factor to keep in mind is that if you have :math:`n` input files
  and :math:`p` partitions, you will need :math:`n \times p` temporary files,
  which can grow quickly.

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
  Makefile  slurm_job  out  tmp

  ./out:

  ./tmp:

QUACreduce has created two files and two directories:

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

Add more input data
-------------------

One of the neat things that QUACreduce can do is add additional data
and then only re-run the parts of the job that are affected. For example::

  $ echo 'qux' > /tmp/foo3.txt
  $ cd /tmp/mrjob
  $ quacreduce --update . /tmp/foo*.txt
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

For further help, say ``quacreduce --help``.


Distributed QUACreduce
======================

QUACreduce jobs can be distributed across multiple nodes. The basic paradigm
is that the master node runs a Make job which farms tasks out to compute nodes
(which can include the master) using SSH; this list is taken from resource
manager environment variables (e.g., ``$SLURM_NODELIST``). Each node must
therefore have access to the job directory at the same path.

.. warning:: You probably should point ``--sortdir`` to node-local storage for
             jobs of non-trivial size. Otherwise, you might attract the wrath
             of your operators for overly-aggressive use of the shared
             filesystem.


QUACreduce uses an SSH wrapper script called ``sshrot`` to distribute jobs
(say ``sshrot --help`` for more details on using the script). If ``mpirun`` is
available, that is used to distribute jobs; otherwise, it falls back to SSH.

The script has a few quirks you need to be aware of:

#. ``sshrot`` may not work as expected if your login shell is not ``bash``,
   and simply invoking your desired shell as part of the command may not work
   because shell quoting rules are really complicated.

#. ``ssh`` is invoked with ``-o BatchMode=yes``, i.e., don't try to ask the
   user for authentication information, just fail instead if they would have
   to supply anything. This means that you need something set up for
   non-interactive, passwordless login to the compute nodes (and ``localhost``
   if you want to run the tests). For example, SSH keys and a running SSH
   agent will work.

#. No special effort is made to either conserve TCP connections with SSH
   multiplexing or (conversely) avoid the ``MaxSessions`` multiplexing limit.
   These issues may limit scaling.

Example
-------

`FIXME`

::

  $ sbatch -N2 slurm_job -j4

Note that the number of nodes requested from SLURM and ``-j``, which is the
total number of tasks ``make`` will run simultaneously, must be coordinated
for good performance. The above might be appropriate for a cluster with two
cores per node. Memory could be a limitation also, along with myriad others.


Drawbacks
=========

QUACreduce is pretty simple and has a number of limitations. If these are
a problem, perhaps you are better off with something else. Some of these could
be fixed, and others are more fundamental.

* Lower fault tolerance. If one of your nodes goes down, the job will stop.
  However, it will probably do so in a consistent state, and restarting will
  continue more or less where you left off.

* Line-oriented I/O. You are responsible for serializing your data to
  something without newlines, which is kind of annoying and wastes spacetime.

* Scaling is not optimized. If you need to run 10,000 mappers in parallel,
  QUACreduce is probably not for you.

* As mentioned earlier, input filenames must be unique even if they came from
  different directories.

* No automatic chunking of input; QUACreduce cannot map a single file in
  parallel.


FIXME
=====

- parallel sorts


Footnotes
=========

.. [1] I know that it's usually spelled MapReduce, but I think InterCapping is
       stupid.

.. [2] Use of node-local storage in HPC clusters for distributed filesystems
       like HDFS tends to be infeasible because (a) it's difficult to ensure
       that a new job is assigned exactly the same set of nodes as a previous
       job and/or (b) node-local storage is explicitly wiped between jobs.

.. [3] This is the same as Hadoop Streaming; the goal is to make QUACreduce
       components with non-null values work without modification in that
       framework, though this is untested.

.. [4] Note that this contrasts with Hadoop Streaming, where a null key is
       permitted but a null value isn't.
