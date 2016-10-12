.SECONDARY:  # don't remove intermediate files
.ONESHELL:   # pass recipe lines to shell together
.SHELLFLAGS := -ec

MAKEFILE := $(abspath $(MAKEFILE_LIST))
MAKE_DIR := $(dir $(MAKEFILE))
export GNUPLOT_LIB := $(MAKE_DIR)
PATH := $(MAKE_DIR):$(PATH)
OUT_DIR := $(CURDIR)

outs := $(wildcard *.out.pkl.gz)
out_dirs := $(outs:.out.pkl.gz=)
out_stats := $(outs:.out.pkl.gz=/err-stats.pkl.gz)

# Function to find the truth TSV for any input or output file.
truth = $(firstword $(subst /, ,$(1)))/truth.tsv


.PHONY: all
all: tsv plots

.PHONY: tsv
tsvs: deps.mk

.PHONY: plots
plots: plots_all_1 plots_first_1a

# The relevance plots depend on human coding and a datafile that's generally
# not present, so we don't put them in all.
#
# FIXME: relevance only implemented for horizon 0.
.PHONY: relevance
relevance: $(outs:.out.pkl.gz=/relevance/h0.relv-summary.pdf)
#$(outs:.out.pkl.gz=/relevance/h0.relv.pdf)

.PHONY: clean
clean: clean_plots
	rm -f deps.mk
	rm -f err-stats_all.pkl.gz
	rm -f *.tsv
	rm -Rf $(out_dirs)

.PHONY: clean_plots
clean_plots:
	find . -name '*.pdf' | xargs -r rm

.PHONY: plots_all_1
plots_all_1: tsvs

.PHONY: plots_first_1a
plots_first_1a: tsvs

# This makefile includes all the data dependencies for the plots, which aren't
# known until we process the output dumps.
deps.mk: $(out_stats) $(MAKEFILE)
	rm -f $@
	for i in $$(find . -name '*.pred-all.tsv'); do
	  pdf=$$(echo $$i | sed s/\.tsv/.pdf/)
	  echo plots_all_1: $$pdf >> $@
	done
	for i in $$(find . -name '*.pred-first.tsv'); do
	  pdf=$$(echo $$i | sed s/\.tsv/.pdf/)
	  echo plots_first_1a: $$pdf >> $@
	done
# only include it if we are not cleaning
ifeq (,$(findstring clean,$(MAKECMDGOALS)))
  include deps.mk
endif

# Compute all the .tsv, .dat, and other summaries, ready for plotting
#
# content-analysis-urls removed because it would require significant
# modifications, as the input data are no longer stored in the output pickles.
# They would need to be joined in from input,?.pkl.gz.
#
%/err-stats.pkl.gz: %.out.pkl.gz %.model.pkl.gz $(MAKE_DIR)/data-for-plots_dl $(MAKE_DIR)/content-analysis-urls
	mkdir -p $(<:.out.pkl.gz=)
#	content-analysis-urls $(word 2, $^)
	data-for-plots_dl $(word 1, $^)

# Plot 1: All predictions; for each D,L,H,T (2,000 plots)
%.pred-all.pdf: %.pred-all.tsv %.pred-first.tsv $(MAKE_DIR)/pred-all_n.gp $(MAKE_DIR)/base.gp
	gnuplot -c $(word 3,$^) $(call truth,$<) $(word 1,$^) $(word 2,$^) > $@

# Plot 1a: First predictions; for each D,L,H,T
%.pred-first.pdf: %.pred-first.tsv $(MAKE_DIR)/pred-first_n.gp $(MAKE_DIR)/base.gp
	gnuplot -c $(word 2,$^) $(call truth,$<) $(word 1,$^) > $@

# Relevance plots
# relevance, model
%/relevance/h0.relv.tsv %/relevance/h0.relv-summary.tsv: article-relevance.xlsx %.model.pkl.gz
	relevance-data $^
%.relv-summary.pdf: %.relv-summary.tsv $(MAKE_DIR)/relv-summary.gp $(MAKE_DIR)/base.gp
	gnuplot -c $(word 2,$^) $< > $@
