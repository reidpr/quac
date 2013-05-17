Configuration
*************

QUAC uses ``.ini``-style configuration files; some scripts require a
``--config`` argument pointing to the main configuration file.

Loading the configuration is a multi-step process in order to (a) keep
passwords out of the source repository and (b) support a DRY configuration
that also allows different programs in the package to have different
configurations.

Configuration files are loaded in the following order. Later files overwrite
any values that overlap with earlier files. Note that this order is *not*
general to specific!

#. ``default.cfg`` in the same directory as the script. (This file also serves
   as a complete listing of and documentation for the various config keys.)

#. The file specified with ``--config`` on the command line.

#. The file given as ``paths.next_config`` in #2. `FIXME: not yet implemented`

Note that step 3 does not recurse.
