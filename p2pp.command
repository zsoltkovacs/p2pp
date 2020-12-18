#!/bin/sh
DIRECTORY=`dirname $0`
fg
if [ $# -eq -0 ]
then
     $DIRECTORY/P2PP.py  >>p2pp.tmp
else
     $DIRECTORY/P2PP.py -i "$1" >>p2pp.tmp
fi

open -a TextEdit p2pp.tmp

