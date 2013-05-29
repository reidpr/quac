# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.


## Config

# Say e.g. "make VERBOSE=--verbose" for verbose output.
VERBOSE :=

# Say e.g. "make LIMIT='--limit 1000'" to limit the number of items processed.
LIMIT :=

# Don't leave broken files laying around; re-build them on next invocation.
.DELETE_ON_ERROR:

# How much memory should sort use? Keep in mind maximum -j.
SORT_MEM := 512M


## File to build

# Patterns that match some types of files. (Note that for dependent files, we
# compute the lists of files rather than relying on these patterns, because by
# definition they don't exist yet.)
stats_pat := raw/*/*.stats
json_d_pat := raw/*/*.json.d
rawtsv_pat := raw/*/*.raw.tsv
alltsv_pat := pre/*.all.tsv
geotsv_pat := pre/*.geo.tsv
log_pat := pre/*.log raw/*/*.log
gnuplot_pdf_pat := pre/*.gp.pdf

# Lists of files to build.
stats := $(wildcard $(stats_pat))
json_ds := $(stats:.stats=.json.d)
metadata := pre/metadata pre/summary.tsv
graphs := pre/tweet_ct.gp.pdf pre/geotag_rate.gp.pdf pre/gaps.gp.pdf


## Phony rules to organize things

.PHONY: all clean

all: dircheck $(metadata) $(graphs)

# Heuristic test to make sure we're in the right kind of directory.
dircheck:
	test -d raw -a -d pre -a -d geo

clean: clean-rawtsv
	@echo Warning: deleting files which may take days to rebuild...
	rm -f $(gnuplot_pdf_pat)
	rm -f $(geotsv_pat)
	rm -f $(alltsv_pat)
	rm -f $(metadata)
	rm -f $(json_d_pat)
	rm -f $(log_pat)

# There is a little weirdness regarding .raw.tsv files. They are very large,
# and they're not used for downstream processing, so we would like to get rid
# of them once the build is complete. This can ostensibly done by marking them
# as "intermediate" files to cause Make to remove them when they are no longer
# needed. However, this doesn't work in all cases. My understanding is fuzzy,
# but I think it's something like this.
#
# Because they appear as a byproduct of creating .json.d, Make never actually
# builds them when you do something like "make all" with new or modified
# .stats, and in this case, Make doesn't treat them as intermediate and they
# don't get removed. You can remove them manually, though.
#
# However, if all the .json.d are up to date and you rebuild (e.g.) a
# .all.tsv, then Make *does* think they're intermediate and does remove them
# automatically.
#
# To get the above behavior, I needed to have both (a) .INTERMEDIATE to
# explicitly mark the .raw.tsv as intermediate (without this, make will not
# rebuild them if they're deleted, and sort will fail), and (b) a rule to
# build them (without this, make doesn't know how to rebuild them). I also
# include a clean-rawtsv target to facilitate manual removal; the recommended
# invocation is "make all && make clean-rawtsv" (in a parallel make, "make all
# clean-rawtsv" may start to delete .raw.tsv files before all is done).

clean-rawtsv:
	rm -f $(rawtsv_pat)

## Actual rules to get stuff done

ifneq ($(MAKECMDGOALS),clean)
   # Don't include sub-makefiles if we're just going to delete them.
   #
   # You will get a warning about each .json.d that doesn't exist. This is
   # kind of stupid, because we are about to build them. These warnings can be
   # supressed with "-include", but that also causes make to not complain and
   # proceed happily if the .json.d can't be built, which isn't what we want.
   include $(json_ds)
endif

json2rawtsv = json2rawtsv $(VERBOSE) $(LIMIT) $<

%.json.d: %.stats
# We don't actually know which .raw.tsv files will come out; that's a
# byproduct of building .json.d. So, they are not named in this rule.
	$(json2rawtsv)

# The dependencies of .raw.tsv and .all.tsv are unknown; we must compute them
# by parsing .json.gz (because who knows which tweets are included in a given
# raw file). They are recorded in .json.d, which are included here. These
# dependencies are, in summary:
#
# 1. .raw.tsv depend on the corresponding .stats.
# 2. .all.tsv depend on each .raw.tsv for the same date.

%.raw.tsv:
	$(json2rawtsv)

%.all.tsv:
	sort -o $@ -n -u -S $(SORT_MEM) -T . $(filter %.raw.tsv, $^)

%.geo.tsv: %.all.tsv
# This works by testing the last character of a line: if it's not a tab, then
# the last column (geotag source) contains something, so there's a geotag.
#
# The crap at the end of the line is because grep's exit codes can be either 0
# (matches found) or 1 (no matches found). Only code >= 2 means a real error,
# which we really do want to catch. And on older tweet files, no geotagged
# tweets is common.
	grep -Pv "\t$$" $< > $@ ; [ $$? -le 1 ]

pre/metadata:
	tsv2metadata $(VERBOSE) $@ $?

pre/summary.tsv: pre/metadata
	summarize-days $? > $@

%.gp.pdf: pre/summary.tsv
	cat $? | gnuplot-glue $@
