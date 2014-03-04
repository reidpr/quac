# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.


## Config

# How wide to make the hashed/ directory?
HASHMOD := 256

# How many files per xargs block? (2048 would yield very approximately 128 KiB
# of command line per invocation.)
XARGS_BLOCK := 1024

# Set to e.g. '--notimes' or '--verbose' for testing.
MDARGS :=


## Lists of files

# Pagecounts files -- all 50,000 of them.
pagecount_files := raw/*/*/pagecounts-*.gz


## Functions

# This function is the equivalent of xargs. It's useful when acting on
# variables whose length exceeds the maximum command line length (which can be
# surprisingly short -- 256KiB on OS X), in which case shell xargs can't help
# us. It is deep magic and if you understand it, I will give you a cookie.
# http://blog.melski.net/2012/01/03/makefile-hacks-automatically-split-long-command-lines/
#
# The chunk size must be greater than 0.
define xargs
  $(eval _args:=)
  $(foreach obj,$3,$(eval _args+=$(obj))$(if $(word $2,$(_args)),$1$(_args)$(EOL)$(eval _args:=)))
  $(if $(_args),$1$(_args))
endef
# The two blank lines are significant.
define EOL


endef


## Phony rules to organize things

.PHONY: all clean
.PRECIOUS: metadata

all: dircheck hashed metadata

clean:
	rm -Rf hashed hashed_small hashed_tiny metadata metadata.total.pkl.gz missing.tsv

dircheck:
	test -d raw -a -d raw/2012 -a -d raw/2012/2012-10

xargs-test:
	@echo chunks of size 1
	@$(call xargs, echo gopher, 1, a b)
	@echo list of length 0
	@$(call xargs, echo gopher, 2, )
	@echo list length equals chunk size
	@$(call xargs, echo gopher, 2, a b)
	@echo list divides evenly
	@$(call xargs, echo gopher, 3, a b c d e f)
	@echo list does not divide evenly
	@$(call xargs, echo gopher, 3, a b c d e)


## Actual rules to get stuff done

hashed: metadata $(pagecount_files)
	@echo wp-hashfiles on $(words $(filter %.gz, $?)) files ...
	@$(call xargs, wp-hashfiles $(HASHMOD) metadata, $(XARGS_BLOCK), $(filter %.gz, $?))
	touch -r metadata hashed

metadata: $(pagecount_files)
	@echo wp-update-metadata on $(words $?) files ...
	@$(call xargs, wp-update-metadata $(MDARGS) $@, $(XARGS_BLOCK), $?)
	wp-statistics $@ > missing.tsv
