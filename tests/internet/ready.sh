#!/bin/bash

# Copyright (c) Los Alamos National Security, LLC, and others.

set -e
$(dirname $0)/../ready.sh

wget --timeout=5 -O /dev/null http://en.wikipedia.org 2>&1 | fgrep --quiet '200 OK'
