#!/bin/sh
DIRECTORY=`dirname $0`

if [ $# -eq -0 ]
then
     python3.7 $DIRECTORY/P2PP.py
else
     python3.7 $DIRECTORY/P2PP.py -i "$1"
fi