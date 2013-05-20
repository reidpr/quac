# Set up environment for tests.

# test scripts in this checkout, not in $PATH
export PATH=$(cd $(dirname $0)/../bin && pwd):$PATH

# stop test if any command fails
set -e

# echo key commands
x () {
    echo "\$ $@"
    eval "$@"
}

# echo key pipelines (executed in a subshell)
y () {
    echo "$ ($1)"
    sh -c "$1"
}
