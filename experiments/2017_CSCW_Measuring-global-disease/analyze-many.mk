.SECONDARY:
.ONESHELL:
.SHELLFLAGS := -ec

MAKEFILE := $(abspath $(MAKEFILE_LIST))
MAKE_DIR := $(dir $(MAKEFILE))
export GNUPLOT_LIB := $(MAKE_DIR)
PATH := $(MAKE_DIR):$(PATH)
OUT_DIR := $(CURDIR)

.PHONY: all
all: done

.PHONY: subdirs_all
subdirs_all:
	for i in d?; do $(MAKE) -C $$i -f $(MAKE_DIR)/analyze.mk all; done

.PHONY: clean
clean: clean_plots
	rmdir ??+*

.PHONY: subdirs_clean
subdirs_clean:
	for i in d?; do $(MAKE) -C $$i -f $(MAKE_DIR)/analyze.mk clean; done

.PHONY: clean
clean_plots:
	for i in ??+*; do find $$i -name '*.tsv' | xargs -r rm; done

.PHONY: subdirs_clean_plots
subdirs_clean_plots:
	for i in d?; do $(MAKE) -C $$i -f $(MAKE_DIR)/analyze.mk clean_plots; done

done: subdirs_all $(MAKEFILE)
	data-for-plots_dist
	rsquared-best > rsquared-max.tsv
