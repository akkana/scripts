#!/bin/zsh

####################################################################
# Rsync local files up to a web server
# Usage: towebhost dir
#
# Set up pre-defined web hosts, paths and users, and their corresponding
# local paths as follows:
#     webhosts=( user@mywebserver1.com:public_html mywebserver2.com:web )
#     weblocalpaths=( $HOME/mywebdir   /public/myotherwebdir )
# The first webhost corresponds to the first weblocalpath, etc.
# Define them in ~/.config/webhosts/webhosts.sh or
# ~/.config/zsh/webhosts.sh

if [[ -r ~/.config/webhosts/webhosts.sh ]]; then
    echo Reading from .config/webhosts
    . ~/.config/webhosts/webhosts.sh
elif [[ -r ~/.config/zsh/webhosts.sh ]]; then
    echo Reading from .config/zsh
    . ~/.config/zsh/webhosts.sh
fi

if (( ! ${+webhosts} || ! ${+weblocalpaths} )); then
    echo 'Please define $webhosts and $weblocalpaths either in'
    echo '~/.config/webhosts/webhosts.sh or ~/.config/zsh/webhosts.sh'
    exit 1
fi

# There's some rudimentary code to do fromwebhost, but don't trust it:
# I almost never have occasion to need that, so I never test that path.
fromwebhost=0

# --protect-args protects against the remote host changing filenames
# to include characters like & or ;, which could result in command execution
# when the remote machine uses bash to evaluate the commandline,
# but more likely just copies files incorrectly.
# E.g. rsync file\ 1 remotehost:folder\ 2
# copies file\ 1 to remotehost:folder, missing the space.
flags='--protect-args '

# Evaluate arguments: -n and/or -f
for i in "$@"
do
    case $i in
        -n)
            flags='-n'
            shift
            ;;
        -f)
            fromwebhost=1
            shift
            ;;
        --default)
            break
            ;;
    esac
done

if [[ $# == 0 ]]; then
    print "Usage: towebhost file_or_dir"
    return
fi


excludes="--exclude .git --exclude cache --exclude __pycache__ --exclude '*.pyc' --exclude 'webhits*'"

for dst in "$@"; do
    echo $dst

    # Get the full path of the argument:
    localpath=$dst:A

    # Sanity check our two webhosts variables:
    if [[ $#weblocalpaths != $#webhosts ]]
    then
        echo "Error: webhosts and weblocalpaths don't match"
        return
    fi
    webhost='none'
    for i in {1..$#webhosts}; do
        if [[ $localpath == $weblocalpaths[$i]* ]]; then
            webhost=$webhosts[$i]
            localbase=$weblocalpaths[$i]
            break
        fi
    done

    if [[ $webhost == 'none' ]]; then
        echo "$localpath\n  doesn't match any known local path in"
        for p in $weblocalpaths; do
            echo "    $p"
        done
        return
    fi

    # Make sure directories have a terminal slash,
    # whether or not the user provided one.
    if [ -d $localpath ]; then
        # Remove terminal slash.
        ## requires extendedglob, so make sure it's set locally.
        setopt localoptions extendedglob
        localpath=${localpath%%/##}/
    fi

    remotepath=${localpath#$localbase}

    if [[ $fromwebhost == 1 ]]; then
        echo "Copying from $webhost$remotepath to local $localpath"
        echo
        cmd="rsync -av $flags --delete $excludes $webhost$remotepath $localpath"

    else
        echo "Copying $localpath to $webhost$remotepath"
        echo
        cmd="rsync -av $flags --delete $excludes $localpath $webhost$remotepath"
    fi

    echo $cmd
    eval $cmd
done
