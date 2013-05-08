#!/bin/bash

# It used to be that you could test a Python module which called
# testable.register() simply by running it as a script. However, the Powers
# that Be have decreed that running scripts within packages is a big fail
# (IMO, this is shortsighted, as the complexity of this script demonstrates).
# Supposedly, there's a package called runpy which does the right magic, but I
# couldn't get it to work properly.
#
# See:
#
#   http://www.python.org/dev/peps/pep-0328/
#   http://www.python.org/dev/peps/pep-0366/
#   http://bugs.python.org/issue1510172
#
# Anyway, the usage of this script is as follows:
#
#   * If you pass the filename of a module, it will be tested.
#
#   * Otherwise, this script will find all candidate modules and test them.
#
#   * If you pass -i as the first argument, then the function
#     test_interactive() will be called instead of the non-interactive test
#     harness. This is good for drawing pictures and whatnot that need human
#     interpretation to determine correctness.
#
#   * The script does not test modules that have import problems:
#
#     * If -l (lenient mode) is specified, any modules that have imports which
#       fail are skipped.
#
#     * Otherwise, only imports explicitly marked with
#       "testable.SKIP_IF_NOT_FOUND" (in a comment) are skipped.
#
#     * There is no skipping for interactive tests.
#
# BUGS:
#
#   * Fails on filenames with spaces or other funny characters.
#
#   * Does not say which modules couldn't be imported.

set -e
#set -x

import_skip='testable.SKIP_IF_NOT_FOUND'

while getopts "il" opt; do
    case $opt in
        i)
            echo '+ interactive mode'
            interactive=1
            ;;
        l)
            echo '+ lenient mode'
            import_skip='^(import|from [^.])'
            ;;
        \?)
            exit 1
            ;;
    esac
done
shift $((OPTIND-1))

modules=$*
if [ "$modules" == "" ]; then
    modules=`find . -name '*.py' -exec grep -l 'testable.register' {} \;`
fi

# Remove all .pyc files: otherwise, importing modules that were removed or
# renamed will still work!
find . -name '*.pyc' -exec rm {} \;

# On MacOS, sed's -r option is -E
sedopt='-r'
if [ `uname` == "Darwin" ]; then
    sedopt='-E'
fi

for mraw in $modules; do
    m=`echo $mraw |  sed $sedopt 's/^(\.\/)?(.*)\.py$/\2/g' | sed $sedopt 's/\//./g'`
    echo -n "+ $m... "
    if [ $interactive ]; then
        echo
        python -c "import $m ; $m.test_interactive()"
    else
        # Python will give an ImportError message in case of import skips
        # FIXME: This doesn't test "from . import foo" correctly.
        if ( egrep "$import_skip" $mraw | python $testimports 2> >(tail -n1) ); then
            echo
            python -m $m
        fi
    fi
done
