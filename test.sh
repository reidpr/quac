#!/bin/bash
# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.

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
#   * Otherwise, this script will find all candidate modules under lib/, all
#     scripts under bin/ and test them. Modules can declare that they should
#     not be included in these automatic tests but remain testable manually;
#     if you pass -a, then these are included anyway.
#
#   * If you pass -i as the first argument, then the function
#     test_interactive() will be called instead of the non-interactive test
#     harness. This is good for drawing pictures and whatnot that need human
#     interpretation to determine correctness.
#
#   * If a script has import problems, a complaint about that will be printed
#     instead of running the tests (which obviously can't be done).
#
#   * This script will also run all the cmdtests under tests/. (To run an
#     individual cmdtest test, "cd tests" and then "cmdtest -t foo .".)
#
# BUGS:
#
#   * Fails on filenames with spaces or other funny characters.

set -e
#set -x

BASEDIR=$(cd $(dirname $0); pwd)

while getopts "ai" opt; do
    case $opt in
        a)
            echo '* test everything (override manual-only)'
            test_all=1
            ;;
        i)
            echo '* interactive mode'
            interactive=1
            ;;
        \?)
            exit 1
            ;;
    esac
done
shift $((OPTIND-1))

to_test=$*

# Choose the right sed option for extended regexes, in a lame way.
case $(uname) in
    Linux)
        sed='sed -r'
        ;;
    Darwin)
        sed='sed -E'
        ;;
    *)
        echo "don't know how to sed on your platform" >&2
        exit 1
        ;;
esac


## Functions ##

# Test whether the imports in script or module $1 can work. This is done by
# extracting all the imports into a test .py file in the same directory as $1,
# and then running that file. Only the first import failure is reported.
import_test () {
    local traw=$(dirname $1)/IMPORTTEST.py
    # strip indents and doctest stuff on import lines
    egrep '^[ >]*(import|from)' $1 | $sed 's/^[ >]*//' > $traw
    python -m $(file_to_module $traw) 2> >(tail -n1)
    local retval=$?
    if [ $retval -eq 0 ]; then
        # success; need newline (on failure, Python error message has one)
        echo
    fi
    rm $traw
    return $retval
}

# Transform filename to Python module name: strip leading ./, if any, and
# trailing .py, and change slashes to dots.
file_to_module () {
    echo $1 | $sed 's/^(\.\/)?(.*)\.py$/\2/g' | $sed 's/\//./g'
}

        # # Python will give an ImportError message in case of import skips
        # # FIXME: This doesn't test "from . import foo" correctly.
        # if ( egrep "$import_skip" $mraw | python $testimports 2> >(tail -n1) ); then
        #     echo
        #     python -m $m
        # fi


## Test scripts ##

cd $BASEDIR/bin

# Can't specify scripts to test.sh (use --unittest), so do nothing if anything
# is specified.
if [ "$to_test" == "" ]; then
    echo '*** testing scripts'
    for script in $(find -L . -type f); do
        # is it really a Python script? hacky test...
        if ( head -n1 $script | fgrep -q python ); then

            echo -n "+ $script ... "

            if ( ! fgrep -q quacpath $script ); then
                echo 'Does not import quacpath'
                continue
            fi

            if ( import_test $script ); then
                if ( fgrep -q -- --unittest $script ); then
                    $script --unittest
                fi
            fi
        fi
    done
fi


## Test modules ##

cd $BASEDIR/lib
echo '*** testing modules'

if [ "$to_test" == "" ]; then
    if [ $test_all ]; then
        grepstr='testable\.(manualonly_)?register'
    else
        grepstr='testable\.register'
    fi
    modules=$(find . -name '*.py' -exec egrep -l $grepstr {} \;)
else
    modules=$to_test
fi

# Remove all .pyc files: otherwise, importing modules that were removed or
# renamed will still work!
find . -name '*.pyc' -exec rm {} \;

for mraw in $modules; do
    # Strip leading lib/, if present (so you can use tab completion with
    # test.sh at top level).
    mraw=$(echo $mraw | $sed 's/lib\///' )
    m=$(file_to_module $mraw)
    echo -n "+ $m ... "
    if [ $interactive ]; then
        echo
        python -c "import $m ; $m.test_interactive()"
    else
        if ( import_test $mraw ); then
            python -m $m
        fi
    fi
done


## Test cmdtests ##

# Can't specify cmdtests to test.sh, so do nothing if anything is specified.
if [ "$to_test" == "" ]; then
    for subdir in $BASEDIR/tests/*; do
        if [ -d $subdir ]; then
            echo -n '***' tests/`basename $subdir`': '
            if (cd $subdir && ./ready.sh); then
                echo testing
                (cd $subdir && cmdtest . || true)
            else
                echo skipped
            fi
        fi
    done
fi
