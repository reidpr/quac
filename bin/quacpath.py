# Scripts must import this module before any other QUAC modules so they get
# QUAC stuff from their working directory instead of a different QUAC
# directory that might be on PYTHONPATH. This is a subtle bug: most of the
# time, you either will be working in the directory that's on PYTHONPATH or
# there won't be one in PYTHONPATH at all. However, if you are in this
# situation, it might not be obvious because the other QUAC is only slightly
# different.
#
# Copyright (c) Los Alamos National Security, LLC, and others.


import os
import sys

sys.path.insert(0, os.path.dirname(__file__) + '/../lib')
