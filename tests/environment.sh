# Set up environment for tests.

# test scripts in this checkout, not in $PATH
export PATH=$(cd $(dirname $0)/../bin && pwd):$PATH

# stop test if any command fails
set -e

# echo key pipelines
x () {
    echo "\$ $@"
    eval "$@"
}
