#!/bin/sh

# Adapted from mosh https://unix.stackexchange.com/a/389119
# The colorizing doesn't work for me, but I've left it in
# in case it turns out to work in some cases.
# For a simpler solution, zipgrep can search epubs.

PAT=${1:?"Usage: grep-epub PAT *.epub files to grep"}
shift
: ${1:?"Need epub files to grep"}

if [ $# -ge 1 ]; then
  extra="--with-filename"
else
  extra=
fi

for i in $* ;do
  output=$(
    unzip -p $i "*.htm*" "*.xml" "*.opf" |  # unzip only html and content files to stdin
    perl -lpe 's![<][^>]{1,200}?[>]!!g;' | # get rid of small html <b>tags
    grep -Piaso  ".{0,30}$PAT.{0,30}" |    # keep some context around matches
    grep -Pi --color "$PAT"                # color the matches.
  )
  if [ x"$output" != x ]; then
    echo "======" $i
    echo $output
    echo
  fi
done
