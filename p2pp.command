#!/bin/sh
DIRECTORY=`dirname $0`

if [ $# -eq -0 ]
then
     python $DIRECTORY/P2PP.py
else
     python $DIRECTORY/P2PP.py -i "$1"
fi