# Copyright (c) Los Alamos National Security, LLC, and others.

umask 007

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
# FIXME: These sed expressions have been untested on a Mac. They used to use
# the non-extended syntax, which is kind of horrible and kept confusing me.
# Interestingly, the -E flag is undocumented on Ubuntu but sees to work. We
# may need some other portability solution.
cleanup () {
    sed -E -e 's/[0-9]{1,2}:[0-9]{2}:[0-9]{2}/[TIME]/g' \
           -e 's/[0-9.]+( ?[a-zA-Z]+\/(s|second)([ )]|$))/[RATE]\1/g' \
           -e "s|$QUACBASE|[QUACBASE]|g"
}

# Echo key commands (in parent shell), no cleanup.
x () {
    echo "\$ $@"
    eval "$@" 2>&1
}

# Echo key pipelines (in a subshell), piping through cleanup
y () {
    echo "$ ($1)" | cleanup
    bash -c "$1" 2>&1 | cleanup
}

# Echo key commands (in parent shell), with cleanup; return value inaccessible.
z () {
    echo "\$ $@" | cleanup
    eval "$@" 2>&1 | cleanup
}

# Echo key commands (in parent shell), with cleanup and sort; no return value.
zs () {
    echo "\$ $@ | sort" | cleanup
    eval "$@" 2>&1 | cleanup | LC_ALL=C sort
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
