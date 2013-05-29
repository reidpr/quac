.. Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

FAQ
***

#. A caution about tweet IDs

   Tweet IDs are 64-bit integers. This exceeds the capacity of double-precision
   floating point numbers, which can cause a variety of problems. For example,
   loading TSV files without declaring the column as text can silently truncate
   digits, and JSON parsing in some languages can fail silently.

#. My python script barfs with ``UnicodeDecodeError`` when printing tweets!

   The output encoding must be UTF-8; sometimes, your terminal is capable, but
   Python fails to detect this (e.g., Mac OS X 10.4). In this case, you can
   set the ``LANG`` environment variable to ``en_US.UTF-8``, or (as a last
   resort) ``PYTHONIOENCODING`` to ``utf8``. If your terminal is incapable,
   you're just out of luck. Get a Mac?

#. Unicode works OK in the terminal, but Python barfs when redirecting stdout.

   I could not figure out how to make this work without changing the source
   code. Snippet::

      import codecs
      utf8_stdout = codecs.getwriter("utf8")(sys.stdout)

   Now ``utf8_stdout`` is a file-like object that can print UTF8 to stdout.

#. The collector fails to start with ``--daemon`` and there's no error
   message.

   During the daemonization procedure, there's an interval between when
   ``stdout`` and ``stderr`` are closed and the logging starts up. If
   something goes wrong during this period, the failure is silent (I'm not
   sure where the exception is being eaten -- the ``python-daemon`` library,
   or something else).

   To diagnose, pass the ``--daemon-debug`` switch, which prevents stdout and
   stderr from being closed. It also aborts the program after logging is set
   up, because running a daemon with ``stdout`` and ``stderr`` open can cause
   weird problems.

#. How do I quickly see a tweet as it's "supposed" to look?

   You can look at any tweet in your browser with the following URL::

      https://twitter.com/#!/FOO/status/174159225168203778

   ``FOO`` is ostensibly the username of the user who created the tweet, but
   it doesn't seem to matter what you put there. Obviously, replace the ID
   with the one you're actually interested in.

   This seems to work sometimes and not work sometimes. I haven't figured out
   the pattern.
