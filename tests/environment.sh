# Copyright (c) Los Alamos National Security, LLC, and others.

# Set up environment for tests.

# base QUAC directory
export QUACBASE=$(cd $(dirname $0)/$(dirname $BASH_SOURCE)/.. && pwd)

# test scripts in this checkout, not in $PATH
export PATH=$QUACBASE/bin:$PATH

# Same for Python modules; the oddness is so we don't have a trailing colon if
# $PYTHONPATH is unset.
export PYTHONPATH=$QUACBASE/lib${PYTHONPATH:+:}$PYTHONPATH

# Use the test arguments
export QUACARGS="--notimes --config=$QUACBASE/tests/test.cfg"

# Make a private directory for tests to work in. If tests need to share state,
# they can set it up manually.
mkdir $DATADIR/$TESTNAME
export DATADIR=$DATADIR/$TESTNAME

# Use a known locale so that things sort consistently. I think this may also
# affect Unicode stuff?
export LC_ALL=en_US.UTF-8

# stop test if any command fails
set -e

# Strip out things that vary in output:
#
# - timestamps (e.g., 1:23:45)
# - rates (e.g., 100 elephants/s)
#
# The regular expressions look like line noise because I'm trying to be
# portable.
cleanup () {
    sed -e 's/[0-9]\{1,2\}:[0-9][0-9]:[0-9][0-9]/[TIME]/g' \
        -e 's/[0-9.]\{1,\} \([a-zA-Z]\{1,\}\/s\)/[RATE] \1/g' \
        -e "s|$QUACBASE|[QUACBASE]|g"
}

# echo key commands
x () {
    echo "\$ $@" | cleanup
    eval "$@" 2>&1 | cleanup
}

# echo key pipelines (executed in a subshell)
y () {
    echo "$ ($1)" | cleanup
    bash -c "$1" 2>&1 | cleanup
}

# Decide how to call netstat. The problem is that Red Hat and everyone else
# chose incompatible options for not truncating hostnames.
if (netstat --help 2>&1 | fgrep -q -- --wide); then
    WIDE=--wide
else
    WIDE=--notrim
fi

# Print info about current SSH state (4 lines). See commit c5009e for the most
# recent -o ControlPersist=5m version (it was actually in
# localssh/distmake.script then).
sshinfo () {
    # FIXME: This ps command does not work on Mac. I suspect a portable
    # alternative is possible, but I haven't figured it out yet.
    echo -n 'ssh clients:      '
    ps -C ssh -o command | fgrep -v 'sleep 86400' | egrep -c -- '-S .+sshsock\..* '$1 || true
    echo -n 'ssh masters:      '
    ps -C ssh -o command | egrep -c -- '-S .+sshsock\..* '$1' sleep 86400' || true
    echo -n 'control sockets:  '
    ls /tmp | fgrep -c 'sshsock.'$1 || true
    echo -n 'TCP connections:  '
    netstat $WIDE | egrep -c '(localhost|'$HOSTNAME'):.+'$1'.*:ssh +ESTABLISHED' || true
}

sshinfol () {
    sshinfo $HOSTNAME
}
