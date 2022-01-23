#!/bin/zsh
#
# Separate the jpeg and video from a Google MotionPhoto file
# from a Pixel phone. Works in Android 12 as of January 2022.
# No guarantees about earlier or later, apparently Google
# changes this format frequently.

# Adapted from:
# https://mjanja.ch/2021/10/stripping-embedded-mp4s-out-of-android-12-motion-photos/

for infile in $*; do
    outjpg=$(echo $infile | sed 's/.MP.jpg/.jpg/')
    if [[ $outjpg == $infile ]]; then
        echo "ERROR: No .MP.jpg in $infile, skipping"
        continue
    fi
    outmovie=$(echo $infile | sed 's/.MP.jpg/.mp4/')
    if [[ $outjpg == $infile ]]; then
        echo "Problem getting mp4 filename: $infile"
        continue
    fi

    # Don't crash when there are no files matching the glob
    [ -f "$infile" ] || continue

    # Check MP4 header, newer versions first
    unset ofs
    for header in 'ftypisom' 'ftypmp4' 'ftypmp42'; do
        ofs=$(grep -F --byte-offset --only-matching --text "$header" "$infile")

        if [[ $ofs ]]; then
            # echo "$infile: offset $ofs"

            # Extract just the jpeg part:
            cp "$infile" "$outjpg"
            # cp "$infile" "$outmovie"
            ofs=${ofs%:*}
            ofs=$((ofs-4))
            # truncate -s $((ofs-4)) "$outjpg"
            truncate -s $ofs "$outjpg"

            # extract the movie part.
            # Neither of these work
            # cut -b ${ofs}- "$infile" >"$outmovie"
            # tail -c +${ofs} "$infile" >"$outmovie"
            # But this does:
            dd if="$infile" skip=1 bs=$ofs of="$outmovie" >/dev/null 2>&1

            echo "JPEG: $outjpg, MOVIE: $outmovie"

            # Go to next image
            break
        else
            echo "Couldn't calculate offset"
        fi
    done
done
