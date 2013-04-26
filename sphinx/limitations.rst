Bugs and limitations
********************

* This bug list is here in the ``README`` instead of a real bug tracker.

* Paths in the config files must be relative to the location of the config
  file specified on the command line (specifically, absolute paths don't
  work).

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

* ``Geo_GMM`` objects can't be printed because of a ``RuntimeError`` arising
  from (IMO) a design error. I filed a `bug report
  <https://github.com/scikit-learn/scikit-learn/issues/1463>`_.

* There are several places where a ``verbose`` argument could be eliminated by
  interrogating the logger instead (i.e., are we at ``DEBUG`` log level).

* Write a "contributing" section for these docs. Ideas:

  * where is the master repository

    * there is none - it's distributed
    * reid's branch is the de facto master
    * he pushes to ``FIXME`` regularly
    * do not push to ``FIXME``

  * updating your working directory

    * hg pull
    * hg update

  * edit in a branch, not on ``master``
  * coding style
  * say ``test.sh`` a lot

* Parsing related:

  * ``summarize-days`` should output nulls for days where we didn't collect
    any data.

* Console logging claims it's going to ``stdout`` when it fact it's
  ``stderr``. Update docs and comments.
