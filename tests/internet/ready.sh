#/bin/sh

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

wget --timeout=5 -O /dev/null http://en.wikipedia.org 2>&1 | fgrep --quiet '200 OK'
