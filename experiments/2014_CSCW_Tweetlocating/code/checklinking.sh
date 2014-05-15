#!/bin/sh

find $MYPREFIX/lib -name '*.so' -exec sh -c "echo {} && ldd {} | grep 'not found'" \;
