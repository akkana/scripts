#!/usr/bin/env python

# Manage git branches between local and remote,
# since git is so incredibly inept at that.

# Uses python-git package on Debian.

# Choices for git in python on Debian seem to be: python-git, python-pygit2,
# and python-dulwich. Dulwich doesn't have any docs on examining things
# like branches; it's all about creating and committing files.
# python-git seems like the best, and seems to correspond to
# the (rather incomplete) docs at
# http://gitpython.readthedocs.io/en/stable/tutorial.html
# http://gitpython.readthedocs.io/en/stable/reference.html

import sys
import os

from git import Repo

def list_branches(repopath, add_tracking=False):
    '''List branches with their tracking info. If add_tracking is True,
       try to make the local and remote branches mirror each other.
    '''
    repo = Repo(repopath)

    if not repo.remotes:
        print "No remotes!"
        return

    # Fetch from the remote, then build up a dictionary of remote branch names.
    remote = repo.remotes[0]
    print("Fetching from %s..." % remote.name)
    remote.fetch()

    remotebranches = {}
    for branch in repo.remotes[0].refs:
        simplename = branch.name.split('/')[-1]
        if simplename == "HEAD":
            continue
        remotebranches[simplename] = branch

    # Dictionary-ize the local branches too,
    # and make sets showing which local branches track something,
    # and which remote branches are tracked.
    localbranches = {}
    localtracks = set()
    remotetracks = set()
    for branch in repo.heads:
        localbranches[branch.name] = branch
        if branch.tracking_branch():
            localtracks.add(branch.name)
            remotetracks.add(branch.tracking_branch().name.split('/')[-1])

    localbranchnames = set(localbranches.keys())
    remotebranchnames = set(remotebranches.keys())
    print "Local branches:", localbranchnames
    print "Remote branches:", remotebranchnames

    print("")
    for branch in localbranches:
        lb = localbranches[branch]
        if lb.tracking_branch():
            print("%s -> %s" % (lb.name, lb.tracking_branch().name))
        else:
            print(lb.name)
    print("")

    # Print local branches that don't track any remote branch.
    # Don't do anything about this, though.
    for name in localbranchnames - remotebranchnames:
        if not localbranches[name].tracking_branch():
            print("%s doesn't have a corresponding remote branch" % name)

    # What remote branches aren't tracked at all?
    for name in remotebranchnames - remotetracks:
        print("%s isn't tracked by a local branch"
              % remotebranches[name].name)
        if name in localbranches:
            if localbranches[name].tracking_branch():
                print("Local %s is tracking %s instead of %s"
                      % (name, localbranches[name].tracking_branch().name,
                      remotebranches[name].name))
                # If it's tracking something else, we shouldn't change that.
            else:
                if add_tracking:
                    # The local branch already exists, just needs to
                    # be set to track the remote of the same name.
                    print("Setting local %s to track %s"
                          % (name, remotebranches[name].name))
                    localbranches[name].set_tracking_branch(remotebranches[name])
                else:
                    print("Local %s isn't tracking remote %s"
                          % (name, remotebranches[name].name))

        elif add_tracking:
            # We have no local branch matching the remote branch.
            # Need to create a new branch by that name:
            # equivalent of git checkout -t <remote>/name
            # or git branch --track branch-name origin/branch-name
            # Can't use repo.create_head(name) because it doesn't allow
            # for arguments like reference.
            new_branch = git.Head.create(repo, name,
                                         reference=remotebranches[name])
            localbranches[name] = new_branch
            new_branch.set_tracking_branch(remotebranches[name])
            print("Created new branch %s to track %s" % (name,
                                                         remotebranches[name]))

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "-a":
        list_branches(".", True)
    else:
        list_branches(".", False)

def Usage():
    print("Usage: %s [-a]" % os.path.basename(sys.argv[0]))
    print("  -a: Add tracking to branches that don't have it")

if __name__ == '__main__':
    main()
