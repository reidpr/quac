# Source this in your test scripts to parse command line arguments correctly.

CORE_CT_DEFAULT=1
START_DEFAULT=2012-01-25
END_DEFAULT=2013-01-24

sedopt='-r'
if [ `uname` == "Darwin" ]; then
    sedopt='-E'
fi
# default job dir is named after script and timestamp
JOBDIR=$TWEPI_JOBBASE/`basename $0 | sed $sedopt s/\.[a-z]+\.sh$//`_`date +'%Y%m%d-%H%M'`

CORE_CT=$CORE_CT_DEFAULT
GEODB=$TWEPI_GEODB
START=$START_DEFAULT
END=$END_DEFAULT

while getopts ':c:g:j:' opt; do
    case $opt in
        c)
            CORE_CT=$OPTARG
            ;;
        g)
            GEODB=$OPTARG
            ;;
        j)
            if [[ "$OPTARG" = /* || "$OPTARG" = "." || "$OPTARG" = ~* ]]; then
                # absolute path, dot, or tilde - leave it alone
                JOBDIR=$OPTARG
            else
                # relative; prefix the default
                JOBDIR=$TWEPI_JOBBASE/$OPTARG
            fi
            ;;
        s)
            START=$OPTARG
            ;;
        e)
            END=$OPTARG
            ;;
        h|\?|:)
            # -h, invalid option, or missing argument... print help
            cat <<EOF
These files are shell scripts that run or set up experiments. They take the
following arguments:

  -c N          number of cores per process (default $CORE_CT_DEFAULT)
  -g FILE       path to geodb (default $TWEPI_GEODB)
  -j DIR        job directory (under $TWEPI_JOBBASE if relative)
  -s TIMESTAMP  start time (default $START_DEFAULT)
  -e TIMESTAMP  end time (default $END_DEFAULT)
  -h            show this help text

Conventions:

  * scripts named .jex use jexplode to create a job, while scripts named
    .imm execute the experiment immediately.

  * comment at the top of the script says a little about the experiment.

  * put options one per line in the order specified by model-test --help.

Note: model-test and jexplode must be in your \$PATH.
EOF
            >&2
            exit 1
            ;;
    esac
done


# set these here for convenience
set -e
set -x
