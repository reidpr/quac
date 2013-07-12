# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

'''Functions and classes to facilitate scripts that set up, run, and clean up
   after QUACreduce jobs.'''

# Scripts can use and/or extend this help epilogue to explain the various
# caveats & hints for QUACreduce jobs.
help_epilogue = '''
Notes:

  * If JOBDIR already exists, any of its contents that get in the way of the
    job will be clobbered, but everything else will be left alone. Note that
    this can cause confusion in some cases; for example, if a run with
    --partitions 4 is followed by a run with --partitions 2 in the same
    directory, the output files from the two runs will be mixed (since the
    second one produces fewer).

  * If --reduce includes the string "%RID", it is replaced with the reducer
    ID; this is important for coordinating output files if --partitions > 1.

  * --python is mutually exclusive with --map and --reduce (which must both be
    specified if one is).

  * --pyargs is a dictionary of parameters to pass to the Python job.
    Key/value pairs are colon-separated, and pairs are space-separated. Values
    are converted to ints or floats if possible (in that order); otherwise,
    they are left as strings. E.g.: "--pyargs 'foo:bar baz:1 qux:1.0'".

  * --sortdir probably should not, if possible, be on the shared filesystem;
    the point is to leverage node-local storage for sorting during the
    partitioning phase. However, this storage must be available on the same
    path for each node.

  * Input files need not exist at quacreduce time; this gives you greater
    flexibility in when to build the job.

  * Beware shell quoting with --map and --reduce!
'''

import os
import subprocess as sp

import time_
import u
l = u.l

# This command returns false if the first command in the previous pipe failed.
PIPEFAIL = 'if [ $${PIPESTATUS[0]} -ne 0 ]; then false; fi'



### Job phases ###

def clean(args):
   sp.check_call('cd %s && make clean' % (args.jobdir), shell=True)

def parse_args(ap):
   # parse args
   args = u.parse_args(ap)
   # check arguments
   if (len(set(os.path.basename(i) for i in args.inputs)) != len(args.inputs)):
      ap.error('input file basenames must be unique')
   if (args.python and (args.map or args.reduce)):
      ap.error('--python cannot be specified with --map and/or --reduce')
   if (args.map and not args.reduce or args.reduce and not args.map):
      ap.error('--map and --reduce must both be specified if one is')
   # absolutize input files
   args.inputs = [os.path.abspath(i) for i in args.inputs]
   # set sortdir if unset
   if (args.sortdir is None):
      args.sortdir = 'tmp'
   # done
   return args

def run(args, job_ct):
   sp.check_call('cd %s && make -j%d' % (args.jobdir, job_ct), shell=True)

def setup(args):
   if (not (args.python or args.map or args.reduce)):
      u.abort('--python or --map and --reduce must be specified')

   directories_setup(args)
   if (args.python):
      pythonify(args)
   makefile_dump(args)
   slurm_dump(args)


### Classes ###

class ArgumentParser(u.ArgumentParser):

   def parse_args(self, args):
      gr = self.add_argument_group('operators')
      gr.add_argument('--map',
                      metavar='CMD',
                      help='shell pipeline for map function')
      gr.add_argument('--reduce',
                      metavar='CMD',
                      help='shell pipeline for reduce function')
      gr.add_argument('--python',
                      metavar='CLASS',
                      help='Python class containing map-reduce implementation')
      gr.add_argument('--pyargs',
                      metavar='DICT',
                      help='Dictionary of parameters for Python job')
      gr = self.add_argument_group('job logistics')
      gr.add_argument('inputs',
                      metavar='FILE',
                      nargs='+',
                      help='input files (must have unique names)')
      gr.add_argument('--jobdir',
                      metavar='DIR',
                      default='.',
                      help='job directory (default .)')
      gr.add_argument('--partitions',
                      type=int,
                      metavar='N',
                      default=1,
                      help='number of partitions to use (default 1)')
      gr.add_argument('--sortdir',
                      metavar='DIR',
                      help='directory for sort temp files (default JOBDIR)')
      gr.add_argument('--sortmem',
                      metavar='N',
                      default='64M',
                      help='sort memory to use (sort -S; default 64M)')
      gr.add_argument('--update',
                      action='store_true',
                      help='add more input (not implemented; see issue #36)')
      return super(ArgumentParser, self).parse_args(args)


### Support functions ###

def directories_setup(args):
   u.mkdir_f(args.jobdir)
   u.mkdir_f('%s/out' % (args.jobdir))
   u.mkdir_f('%s/tmp' % (args.jobdir))

def makefile_dump(args):
   fp = open('%s/Makefile' % (args.jobdir), 'w')
   fp.write('''\
# This is a QUACreduce job, generated %s.

SHELL=/bin/bash\n
'''
            % (time_.nowstr_human()))
   # everything
   fp.write('all: %s\n' % (' '.join('tmp/%d.reduced' % (i)
                                    for i in xrange(args.partitions))))
   # cleanup
   fp.write('''
.PHONY: clean reallyclean
clean:
	rm -Rf tmp/*
reallyclean: clean
	rm -Rf out/*
''')
   # mappers
   for filename in args.inputs:
      fp.write('''
%(mapdone)s: %(input)s
	%(map_cmd)s < %(input)s | hashsplit %(nparts)d tmp/%(ibase)s && %(pipefail)s
	touch %(mapdone)s
''' % { 'ibase': os.path.basename(filename),
        'input': filename,
        'map_cmd': args.map,
        'mapdone': 'tmp/%s.mapped' % (os.path.basename(filename)),
        'nparts': args.partitions,
        'pipefail': PIPEFAIL })
   # reducers
   for rid in xrange(args.partitions):
      input_bases = [os.path.basename(i) for i in args.inputs]
      cmd = args.reduce.replace('%(RID)', str(rid))
      fp.write('''
%(reducedone)s: %(mapdones)s
	LC_ALL=C sort -s -k1,1 -t'	' -S %(buf)s -T %(sortdir)s %(mapouts)s | %(cmd)s && %(pipefail)s
	touch %(reducedone)s
''' % { 'buf': args.sortmem,
        'cmd': cmd,
        'mapdones': ' '.join('tmp/%s.mapped' % (i) for i in input_bases),
        'mapouts': ' '.join('tmp/%s.%d' % (i, rid) for i in input_bases),
        'pipefail': PIPEFAIL,
        'rid': rid,
        'reducedone': 'tmp/%d.reduced' % (rid),
        'sortdir': args.sortdir })
   fp.close()

def pythonify(args):
   'Adjust args.map and args.reduce to call the appropriate Python methods.'
   assert (args.python)
   module = args.python.rpartition('.')[0]
   class_ = args.python
   params = repr(u.str_to_dict(args.pyargs))
   base = "python -c \"import %(module)s; j = %(class_)s(%(params)s); " % locals()
   args.map = base + "j.map_stdinout()\""
   args.reduce = base + "j.reduce_stdinout(%(RID))\""

def slurm_dump(args):
   pass  # unimplemented, see issue #33
