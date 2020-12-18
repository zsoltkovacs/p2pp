#!/bin/sh
DIRECTORY=`dirname $0`
fg
if [ $# -eq -0 ]
then
     $DIRECTORY/P2PP.py  >$DIRECTORY/p2pp.tmp
else
     $DIRECTORY/P2PP.py -i "$1" >$DIRECTORY/p2pp.tmp
fi

open -a Terminal "$DIRECTORY/viewoutput.sh"

