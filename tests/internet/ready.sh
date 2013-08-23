#/bin/sh

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

wget -O /dev/null http://google.com 2>&1 | fgrep --quiet '200 OK'
