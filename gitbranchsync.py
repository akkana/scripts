#!/usr/bin/env python

# Manage git branches between local and remote,
# since git is so incredibly inept at that.
# Also figure out whether a repo needs to be pushed upstream.

# Uses python-git package on Debian.

# Choices for git in python on Debian seem to be: python-git, python-pygit2,
# and python-dulwich. Dulwich doesn't have any docs on examining things
# like branches; it's all about creating and committing files.
# python-git seems like the best, and seems to correspond to
# the (rather incomplete) docs at
# http://gitpython.readthedocs.io/en/stable/tutorial.html
# http://gitpython.readthedocs.io/en/stable/reference.html
#
# Also interesting: https://github.com/bill-auger/git-branch-status/

import sys
import os

from git import Repo

def fetch_from_upstream(repo):
    if not repo.remotes:
        print "No remotes!"
        return

    # Fetch from the remote, then build up a dictionary of remote branch names.
    remote = repo.remotes[0]
    print("Fetching from %s..." % remote.name)
    remote.fetch()

def comprefs(ref):
    '''Find the most recent place where this branch and its upstream
       matched. Return (commits_since_in_local, commits_since_in_upstream).
    '''
    upstream = ref.tracking_branch()
    if not upstream:
        # print("No upstream for " + ref.name)
        return None, None

    # The trick is to find the last SHA that's in both of ref and upstream.
    # Then figure out if either one has anything more recent.
    for i, entry in enumerate(reversed(ref.log())):
        for j, upstream_entry in enumerate(reversed(upstream.log())):
            if entry.newhexsha == upstream_entry.newhexsha:
                return i, j

    # If we get here, there's no common element between the two.
    return None, None

def check_push_status(repo):
    '''Does this repo have changes that haven't been pushed upstream?
    '''
    # git status --porcelain -uno
    print("Locally modified files:")
    porcelain = repo.git.status(porcelain=True).splitlines()
    for l in porcelain:
        if not l.startswith("?? "):
            print l
    print("")

    # git for-each-ref --format="%(refname:short) %(push:track)" refs/heads | fgrep '[ahead'
    foreachref = repo.git.execute(['git', 'for-each-ref',
                                   '--format="%(refname:short) %(push:track)"',
                                   'refs/heads']).splitlines()
    # git.execute weirdly adds " at the beginning and end of each line.
    print("for-each-ref says:")
    for l in foreachref:
        if l.startswith('"') and l.endswith('"'):
            l = l[1:-1]
        print("  " + l)
    print("")

    print("Need to push?")
    for ref in repo.heads:
        l, r = comprefs(ref)
        if l > 0:
            print("  %s: local is ahead by %d commits" % (ref.name, l))
        if r > 0:
            print("  %s: remote is ahead by %d commits" % (ref.name, r))

def list_branches(repo, add_tracking=False):
    '''List branches with their tracking info. If add_tracking is True,
       try to make the local and remote branches mirror each other.
    '''

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

    print("Local branch tracking info:")
    for branch in localbranches:
        lb = localbranches[branch]
        if lb.tracking_branch():
            print("  %s -> %s" % (lb.name, lb.tracking_branch().name))
        else:
            print("  " + lb.name)
    print("")

    print("Branches without tracking:")
    # Print local branches that don't track any remote branch.
    # Don't do anything about this, though.
    for name in localbranchnames - remotebranchnames:
        if not localbranches[name].tracking_branch():
            print("  %s doesn't have a corresponding remote branch" % name)

    # What remote branches aren't tracked at all?
    for name in remotebranchnames - remotetracks:
        print("  %s isn't tracked by a local branch"
              % remotebranches[name].name)
        if name in localbranches:
            if localbranches[name].tracking_branch():
                print("  Local %s is tracking %s instead of %s"
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
                    print("  Local %s isn't tracking remote %s"
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

def Usage():
    print("Usage: %s [-a]" % os.path.basename(sys.argv[0]))
    print("  -a: Add tracking to branches that don't have it")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Check git branches vs. upstream. By default, -lc.')
    parser.add_argument('-l', "--list", dest="list", default=False,
                        action="store_true",
                        help='List branches and their statuses')
    parser.add_argument('-c', "--check", dest="check", default=False,
                        action="store_true",
                        help='Check whether a repo is behind upstream and needs pushing')
    parser.add_argument('-f', "--fetch", dest="fetch", default=False,
                        action="store_true",
                        help='Fetch from upstream before doing anything else')
    parser.add_argument('-t', "--track", dest="track", default=False,
                        action="store_true",
                        help='Sync tracking of local and remote branches')
    parser.add_argument('repo', nargs='?', default='.',
                        help='The git repo: defaults to the current directory')

    args = parser.parse_args()

    repo = Repo(args.repo)

    if args.fetch:
        fetch_from_upstream(repo)

    if args.track:
        list_branches(repo, True)
    elif args.list:
        list_branches(repo, False)
    elif args.check:
        check_push_status(repo)
    else:
        check_push_status(repo)
        print("")
        list_branches(repo, False)

if __name__ == '__main__':
    main()
