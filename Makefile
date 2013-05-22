# A klugy but functional makefile to build the various stuff.

all: bin/hashsplit doc

bin/hashsplit: misc/hashsplit.c
	gcc -std=c99 -Wall -O3 -o $@ $<

.PHONY: doc
doc:
	cd sphinx && $(MAKE)
