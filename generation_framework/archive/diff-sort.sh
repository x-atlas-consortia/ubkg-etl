#!/bin/bash

echo "< `wc -l $1`"
echo "> `wc -l $2`"
echo
diff <(sort $1) <(sort $2)
