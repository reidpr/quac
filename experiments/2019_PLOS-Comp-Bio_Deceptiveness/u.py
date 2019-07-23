from collections import abc
import io
import os
import pathlib
import re

import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns


## Paths & other logistical constants

datapath = pathlib.Path("./data")
datapath_tl = pathlib.Path("./data")
figpath = pathlib.Path(".")


## Experiment configuration (things that could be factors but aren't)

# Random seed. Add 1-based worker number for parallel workers.
random_seed = 8675309

# If the fraction of zeros in a Google Health Trends time series exceeds this,
# remove the feature from analysis.
ght_zero_threshold = 2/3

# Split the weeks into the five seasons. Weeks are Sunday to Saturday
# inclusive and referred to by the starting Sunday. Seasons start on the first
# Sunday in July.
seasons = [ ("2011-Jul-03", "2012-Jun-24"),
            ("2012-Jul-01", "2013-Jun-30"),
            ("2013-Jul-07", "2014-Jun-29"),
            ("2014-Jul-06", "2015-Jun-28"),
            ("2015-Jul-05", "2016-Jun-26") ]
start = seasons[0][0]
end = seasons[4][1]
train_start = start
train_end = seasons[2][1]
test_start = seasons[3][0]
test_end = end

## Configure plots

# \the\textwidth reveals a PLOS text width of 379.4175 points (5.25 inches).
pspoint_inches = 1/72
texpoint_inches = 1/72.27
text_width = 379.4175 * texpoint_inches

# Setting figure size in Matplotlib is tricky; the obvious method of setting
# figsize is not correct if one uses bbox_inches="tight" (or savefig.bbox),
# which we do. As far as I can tell, the sizing algorithm works like this:
#
#   1. Allocate a canvas of size figsize.
#   2. Draw the plot.
#   3. Crop to include only areas drawn on.
#
# The problem is that now the figure is smaller than figsize. One can of
# course scale it when placing it into a document, but then all the other
# things supposedly specified with real units (e.g. text size, tick
# dimensions) no longer uses those units.
#
# Our workaround is to estimate a scale factor and apply that to everything.
#
# The scale can be estimated by iterating values until the output is the right
# size with pdfinfo. (One would think that the ratio between figure size at
# scale=1 and desired figure size would work, but it doesn't. For example, I
# tried a scale of 378/334, but the resulting figure was ~360 points wide.)
# Any estimate will be a little inaccurate, because it depends on what
# specifically is drawn for the labels etc., but hopefully close enough.
fig_scale = 1.198
fig_width = text_width * fig_scale

sns.set_context("notebook")
sns.set(rc={
   "font.size":        10 / fig_scale,
   "axes.labelsize":   10 / fig_scale,
   "axes.labelweight": "bold",
   "legend.fontsize":  10 / fig_scale,
   "axes.titlesize":   10 / fig_scale,
   "axes.titleweight": "bold",
   "xtick.labelsize":  10 / fig_scale,
   "ytick.labelsize":  10 / fig_scale})
sns.set_style("ticks")

mpl.rcParams.update({
   "axes.linewidth":      0.8 / fig_scale,       # frame width (points)
   "axes.labelpad":       4.0 / fig_scale,
   "figure.dpi":          120,       # reasonable size in Jupyter Notebooks
   "font.family":         "DejaVu Sans",
   "font.weight":         "normal",
   "figure.figsize":      (fig_width, 0.3 * fig_width),
   "lines.markersize":    5.0 / fig_scale,
   "pdf.compression":     0,
   "savefig.bbox":        "tight",   # remove whitespace around plot
   "savefig.format":      "pdf",     # default
   "savefig.pad_inches":  1.0 * pspoint_inches / fig_scale,
   "xtick.direction":     "in",
   "xtick.major.pad":     5.0 / fig_scale,
   "xtick.major.size":    7.0 / fig_scale,
   "xtick.major.width":   0.8 / fig_scale,
   "xtick.minor.pad":     5.0 / fig_scale,
   "xtick.minor.size":    3.5 / fig_scale,
   "xtick.minor.width":   0.8 / fig_scale,
   "ytick.direction":     "in",
   "ytick.major.pad":     5.0 / fig_scale,
   "ytick.major.size":    7.0 / fig_scale,
   "ytick.major.width":   0.8 / fig_scale,
   "ytick.minor.pad":     5.0 / fig_scale,
   "ytick.minor.size":    3.5 / fig_scale,
   "ytick.minor.width":   0.8 / fig_scale})

sns.set_palette("deep")
colors = sns.color_palette()


## Set up reproducible output

# The right way to do this is to set the environment variable, but that's not
# supported in Matplotlib 2.0.2 (maybe [1] soon [2]?). For now, monkey-patch
# plt.savefig to rewrite the creation date.
#
# [1]: https://github.com/matplotlib/matplotlib/pull/6597
# [2]: https://github.com/matplotlib/matplotlib/blob/master/doc/users/whats_new/reproducible_ps_pdf.rst

os.environ["SOURCE_DATE_EPOCH"] = "0"


def dict_nested_values(d):
   # https://stackoverflow.com/a/10756615
   for (k, v) in d.items():
      if (isinstance(v, abc.Mapping)):
         yield from dict_nested_values(v)
      else:
         yield v
