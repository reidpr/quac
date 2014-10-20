# A klugy but functional makefile to build the various stuff.
#
# Copyright (c) Los Alamos National Security, LLC, and others.

all: bin/hashsplit doc

bin/hashsplit: misc/hashsplit.c
	gcc -std=c99 -Wall -O3 -o $@ $<

.PHONY: doc
doc:
	cd sphinx && $(MAKE)

.PHONY: doc-web
doc-web:
	cd sphinx && $(MAKE) web
