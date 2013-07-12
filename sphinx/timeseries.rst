.. Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

Time series analysis
********************

QUAC can do some neat things with time series; see the scripts:

* ``ngrams-build``
* ``ngrams-search``
* ``ngrams-correlate``

Input file format
=================

``ngrams-correlate`` requires one or more time series as input. These are
stored in Excel spreadsheets (yes, a proprietary format, but readily
accessible). Only the ``.xls`` format (Excel 95 or 2000/XP/2003) is supported.
[1]_

While the examples are framed in terms of disease outbreaks, any time series
will work.

The format of data within the spreadsheet is not rigorously specified, but
below are some notes. Look at ``misc/halloween.xls`` for an example. Note that
the source code should not be considered a definitive specification.

* Filenames are significant, as they are used to report results. No spaces,
  tabs, or special characters should be included, to simplify interpretation
  of output.

* The first and second row of the sheet gives column headings. The order and
  value of these cells are important; that is, you must use *both* the
  specified names as well as the specified column numbers.

* Columns A (*date*) and B (the value column, named anything that doesn't
  clash) contain the time series of interest.

  * The *date* column is a monotonically increasing list of dates. They do not
    have to be any regular interval.

    * If the sequence has gaps, the value for a given date

  * The value column is floating-point value corresponding to the given date.

    * Leave a cell blank to indicate no data for that date.

    * If the date sequence has gaps, each date preceding a gap is assumed to
      begin an interval extending to (but not including) the next date in the
      list. The value for a given date is assumed to be the *total* value for
      all dates in the interval, and all dates in the interval are assumed to
      contribute equally. For example, if you specify (2012-10-28, 3) and
      (2012-10-30, 42), the sequence as interpreted is ((10-28, 1), (10-29,
      1), (10-30, 1), (10-30, 42)).

      Note that the last date in the sequence will not be extended into an
      interval. For example, if your dates are week starts, you'll need to add
      a dummy week to finish the sequence.

* Columns D, E, and F are events. If an end date is omitted, it is assumed to
  be the same as the start date. These columns are currently ignored.

* Columns H (*property*) and I (*pvalue*) are a set of key/value property
  pairs. Properties other than the following are ignored.

  * *incubation days*

* Other columns, charts, and sheets beyond Sheet 1 are ignored.

* If the data represent a multi-wave disease outbreak, each time series file
  should include only one wave.

----

.. [1] You may get lucky and have ``.xlsx`` work, but don't count on it.
