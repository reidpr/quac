.. Copyright (c) Los Alamos National Security, LLC, and others.

Limitations
***********

* Adventures with ``joblib``:

  * ``Parallel`` has a ``verbose`` argument that is underdocumented ("[I]f non
    zero, progress messages are printed. Above 50, the output is sent to
    stdout. The frequency of the messages increases with the verbosity level.
    If it more than 10, all iterations are reported."). I even looked at the
    code and can't figure it out. Anyway, some experimentation suggests 9
    seems to be a reasonable value; the frequency of messages decays over time
    at a decent rate.

  * ``sqlite3.Row`` objects interact badly with ``joblib``. The symptoms are
    very strange: functions run under 2 or more jobs that touch such an object
    simply stop, with no obvious exception or other error (though segfaults do
    appear in the system logs), and the job starts all its iterations but then
    hangs. For now, because it seems more elegant to not pass those tuples
    through ``joblib``, I haven't removed ``row_factory = sqlite3.Row`` from
    ``db_glue.py``, but it's something to consider for the future. We don't
    currently used named columns very much. (``sqlite3.Row`` `"tries to mimic
    a tuple in most of its features"
    <https://pysqlite.readthedocs.org/en/latest/sqlite3.html#sqlite3.Row>`_,
    but I guess it's not close enough.)

  * Same deal with ``PyICU``. Calling ``tokenizers.ICU.tokenize()`` hangs.
