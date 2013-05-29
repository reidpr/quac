'''This module lets you do two things:

     1. Write doctest tests for your module and put them out of the way at the
        end, with no weird syntax to remember.

     2. Automatically run the tests when the module is executed.

   The way this is done is by calling register(), which invokes some very
   sneaky magic to insert the proper variables into the calling (i.e., your)
   module's namespace and then run the doctests. For example, you might put
   the following at the end of your module `foo.py` (leading comment
   characters are included to avoid making it into a real live doctest):

     # testable.register("""
     #   >>> 'hello world'
     #   'hello world'
     # """)

   Then, you can run `python foo.py` to run the tests (no output means all
   tests passed), or pass -v to see a more detailed report.

   These classes also provide a way for scripts to accept a --unittest flag.
   There are two ways to invoke the tests:

   1. (Preferred.) If the script wraps everything in a main() function, then
      the standard script idiom should be extended to:

        if (__name__ == '__main__' and not testable.do_script_tests()):
           main()

   2. (Deprecated.) If the script runs code outside main, it must parse
      --unittest itself and raise Unittests_Only_Exception (u.parse_args()
      does this), then catch the exception and skip its normal processing.

   The basic complication is that in order to put tests at the bottom of the
   script, you have to execute all the way down to the bottom of the script,
   so you can't do something analagous to argparse._HelpAction (do your thing
   and then exit immediately).'''

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.


import argparse
import doctest
import inspect
import sys


# Set to true if do_script_tests() was called and the answer was, don't run
# the tests.
run_tests = True


class Unittests_Only_Exception(Exception):
   pass

class Raise_Unittest_Exception(argparse.Action):
   def __call__(self, parser, namespace, values, option_string=None):
      raise Unittests_Only_Exception


def register(teststr):
   calling_frame = inspect.stack()[1][0]
   calling_module = sys.modules[calling_frame.f_locals['__name__']]
   calling_frame.f_locals['__test__'] = {'tests': teststr}
   calling_frame.f_locals['test_interactive'] = test_interactive_null
   if (calling_module.__name__ in ('__main__', '<run_path>')):
      if (run_tests):
         test(calling_module)

manualonly_register = register
'''Same as register(), but normally not invoked when test.sh is automatically
   collecting modules to test.'''

def test(module):
   options = doctest.ELLIPSIS | doctest.REPORT_ONLY_FIRST_FAILURE
   doctest.testmod(module, optionflags=options)

def test_interactive_null():
   '''Dummy test_interative() that does nothing. Placed in calling module's
      namespace; if you want actual interactive tests, just put in a def and
      this will be overridden (note that this def must be *after* the
      testable.register() call. The point is so you can run interactive tests
      on any testable'd module without error, even if there are none.'''
   pass

def do_script_tests():
   '''Return true if a script should run unit tests instead of its standard
      operation.'''
   global run_tests
   run_tests = ('--unittest' in sys.argv)
   return run_tests


# Yes, testable.py is itself instrumented in this way, though the test is
# pretty stupid.
register('''
  >>> 'testable.py is awesome'
  'testable.py is awesome'
''')
