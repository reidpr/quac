'''Disco has a scheme to detect which modules your stuff uses, put them in a
   zip file, and copy it to workers. In theory, this enables you to install
   absolutely nothing app-specific on worker nodes. Unfortunately, it works
   poorly (e.g., it misses modules) and has some very weird quirks (e.g.,
   packages are not supported). However, if you have a filesystem shared by
   all the Disco nodes (e.g., via NFS), you can put your stuff in $PYTHONPATH
   and let workers find it that way. Unfortunately, Disco mangles $PYTHONPATH.

   This module works around that. To use, copy $PYTHONPATH to $PYTHONPATH_COPY
   in your .bashrc, restart the Disco master, then place the following two
   lines at the top of your Python scripts before any Disco stuff:

     import mr_path
     mr_path.fix_pythonpath()

   Notes:

     1. You will need to be able import *this module* before you can fix the
        path; to do so, you'll want to set required_modules (mr.base.Job does
        this automatically).

     2. This module still doesn't fix the problem that Disco programs (e.g.,
        modules with subclasses of disco.*) cannot be packaged. There is a
        failed attempt at that in r3be9. Perhaps another wrapper is possible.

   There is a bug for (perhaps part of) this problem:
   <https://github.com/discoproject/disco/issues/328>'''

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

import os
import sys


path_fixed = False

def fix_pythonpath():
   global path_fixed
   if (not path_fixed):
      for i in os.environ['PYTHONPATH_COPY'].split(':'):
         sys.path.insert(0, i)
      path_fixed = True
