This file contains descriptions of any bugs in our code post-publication so that anyone attempting to replicate our results can account for these changes.

Note that we have elected *not* to fix any bugs described in this file. This is so that we have a clean copy of the source code as it was at the time the paper was published, which should allow people to reproduce our results exactly, bugs and all.

2016-03-02 - Wikipedia off-by-one-hour time-shift bug
-----------------------------------------------------

### Background

Each Wikipedia article access file represents a single hour of accesses, and the hour can be determined from the file name. For example, `pagecounts-20071209-180000.gz` represents the period of time from 5:00pm to 5:59:59pm on 2007-12-09. That is, the timestamp found in the file name (20071209-180000, in this example) marks the *end* of the interval.

Likewise, our ground truth datasets all contain timestamps that implicitly represent an interval of time. Because different countries have different reporting methods, some timestamps mark the end of an interval, while others mark the beginning. This is more thoroughly documented in the supplemental information provided alongside [our publication](http://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003892).

In order to perform our analysis, which involved correlations and building statistical models, we had to ensure that our time intervals aligned. That is, we needed to make sure that when we talked about a time interval for a given ground truth dataset, we were referring to the exact same interval of time in the Wikipedia data. To solve this problem, we decided to arbitrarily shift all timestamps, when necessary, to mark the *beginning* of the interval.

In the case of the Wikipedia data, we just had to shift every timestamp forward by 1 hour. In the above example, the timestamp we would use to represent the interval of time between 5:00pm and 5:59:59pm on 2007-12-09 would thus be 5:00pm on 2007-12-09, *not* the 6:00pm timestamp found in the file name.

### The bug

There were two phases of our analysis. The first phase, seen in `time_series.py`, was to pull usable time series out of the raw Wikipedia access files. This step involved using the MapReduce paradigm to, in parallel, read each file and build the time series we wanted. In order to simplify our life, we chose to subtract 1 hour from each timestamp (line 73) so that we didn't have to worry about doing that later on.

The problem is that our correlation and regression analysis, seen in `lag_analysis_regression.py`, also subtracted 1 hour from each timestamp (line 68). That means that during our analysis, we were effectively dealing with data that occurred 1 hour prior to when it actually occurred.

### Ramifications

This bug is ultimately totally negligible and doesn't change our results in any meaningful way for several reasons:

1. As seen in Table 1 in our paper, the finest granularity ground truth data we dealt with was daily, and these two cases failed catastrophically for reasons totally unrelated to this bug (described in the paper). We never correlated hourly data. Most data were weekly or monthly. As a result, we always aggregated the Wikipedia data, which has the effect of smoothing out this off-by-one-hour bug.
1. At the weekly level, 1 out of the 168 data points was incorrect. At the monthly level, 1 out of the ~720 data points was incorrect.
1. The magnitude of each incorrect data point is very small. In general, article accesses don't change very much from one hour to the next.
1. In practice, correlations are off by a factor of about 10<sup>-5</sup> or 10<sup>-6</sup>, which is clearly very small.
1. The effect of time zone differences, which we explicitly chose not to handle in our paper, will far outweigh the effect of this bug because time zone differences can account for up to a 24-hour difference.

Additionally, note that the supplemental data files included alongside our paper contain correct data. This bug only existed in our analysis, not in the data generation step.

### Fix

The fix for this bug is to simply alter line 68 of `lag_analysis_regression.py` so that there is no 1-hour subtraction.

### Gratitude

Thanks to Dr. Lee Raney, Matthew Cooper, Erin Cosby, Ryan Rogers, and Joseph Schafer at the University of North Alabama for helping us identify this bug.
