#!/bin/bash

# Desired app size
appwidth=165
appheight=65

# How strongly to prefer top/bottom edges vs. left/right?
# Chance of choosing left/right edge is 1/$sidechance.
sidechance=20

# Find the monitor height
dimensions=$( xdpyinfo | grep dimensions: | head -1 | awk '{ print $2; }' )
if [[ ! $monheight = -* ]]; then monheight="+$monheight"; fi

# This will be the second dimension, after we choose top/bottom vs left/right.
if [[ $(( RANDOM % 2 )) != 0 ]]; then
    whichedge='+0'
else
    whichedge='-0'
fi

# Choose top/bottom vs. left/right, preferring top/bottom
if [[ $(( RANDOM % $sidechance )) != 0 ]]; then
    # top/bottom
    monwidth=$( echo $dimensions | sed 's/x.*//' )
    # Reduce monwidth by the width of the app, so it won't be positioned
    # off the right side of the screen.
    monwidth=$(( $monwidth - $appwidth ))
    # random number between -$monwidth and $monwidth
    geom=$(( ( ((RANDOM % $monwidth) * 2) - $monwidth )  + 1 ))
    if [[ ! $geom = -* ]]; then geom="+$geom"; fi
    geom="$geom$whichedge"
else
    monheight=$( echo $dimensions | sed 's/.*x//' )
    # Reduce monheight by the height of the app, so it won't be positioned
    # off the bottom of the screen.
    monheight=$(( $monheight - $appheight ))
    # random number between -$monheight and $monheight
    geom=$(( ( ((RANDOM % $monheight) * 2) - $monheight )  + 1 ))
    if [[ ! $geom = -* ]]; then geom="+$geom"; fi
    geom="$whichedge$geom"
fi
geom="${appwidth}x${appheight}${geom}"
echo "$geom"
