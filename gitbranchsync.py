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
        return 0, 0

    # The trick is to find the last SHA that's in both of ref and upstream.
    # Then figure out if either one has anything more recent.
    for i, entry in enumerate(reversed(ref.log())):
        for j, upstream_entry in enumerate(reversed(upstream.log())):
            if entry.newhexsha == upstream_entry.newhexsha:
                return i, j

    # If we get here, there's no common element between the two.
    print("Warning: no common commit between %s and %s" % (ref.name,
                                                           upstream.name))
    return 0, 0

def check_push_status(repo, silent=False):
    '''Does this repo have changes that haven't been pushed upstream?
       Print any info, but also return the number of changes that differ.
       If silent is set, don't print anything, just calculate and return.
    '''
    modfiles = 0
    # git status --porcelain -uno
    porcelain = repo.git.status(porcelain=True).splitlines()
    for l in porcelain:
        if not l.startswith("?? "):
            if not silent:
                if not modfiles:
                    print("Need to commit locally modified files:")
                print l
            modfiles += 1
    if not silent:
        print("")

    differences = 0
    for ref in repo.heads:
        localdiffs, remotediffs = comprefs(ref)
        upstream = ref.tracking_branch()
        if not upstream:
            # Can't push if there's no upstream!
            continue
        if localdiffs or remotediffs:
            if not differences:
                if not silent:
                    print("Need to push:")
                needspush = True
        elif not silent:
            print("Up to date with %s" % upstream.name)

        if localdiffs > 0 and not silent:
            print("  %s is ahead of %s by %d commits" % (ref.name,
                                                         upstream.name,
                                                         localdiffs))
        if remotediffs > 0 and not silent:
            print("  %s is ahead of %s by %d commits" % (upstream.name,
                                                         ref.name, remotediffs))

    # Perhaps temporarily, compare with the output of what I used before,
    # git for-each-ref --format="%(refname:short) %(push:track)" refs/heads | fgrep '[ahead'
    foreachref = repo.git.execute(['git', 'for-each-ref',
                                   '--format="%(refname:short) %(push:track)"',
                                   'refs/heads']).splitlines()
    # git.execute weirdly adds " at the beginning and end of each line.
    foundref = False
    for line in foreachref:
        if '[ahead' in line:
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1]
            if not foundref:
                if not silent:
                    print("for-each-ref says:")
                foundref = True
            if not silent:
                print("  " + line)
    if foundref and not silent:
        print("")

    return modfiles + localdiffs + remotediffs

def list_branches(repo, add_tracking=False):
    '''List branches with their tracking info. If add_tracking is True,
       try to make the local and remote branches mirror each other.
    '''

    remotebranches = {}
    if not repo.remotes:
        print("No remotes for repo %s" % repo.working_dir)
        return

    for branch in repo.remotes[0].refs:
        simplename = branch.name.split('/')[-1]
        if simplename == "HEAD":
            continue
        remotebranches[simplename] = branch

    # Formatting: what's the longest name?
    maxlen = 0

    # Dictionary-ize the local branches too,
    # and make sets showing which local branches track something,
    # and which remote branches are tracked.
    localbranches = {}
    localtracks = set()
    remotetracks = set()
    for branch in repo.heads:
        localbranches[branch.name] = branch
        maxlen = max(maxlen, len(branch.name))
        if branch.tracking_branch():
            localtracks.add(branch.name)
            remotetracks.add(branch.tracking_branch().name.split('/')[-1])

    localbranchnames = set(localbranches.keys())
    remotebranchnames = set(remotebranches.keys())

    # The four lists we care about
    tracking_branches = []       # local tracks remote
    not_tracking_branches = []   # local doesn't track remote of same name
    local_only = []              # local, no remote of same name
    remote_only = []             # remote, no local of same name

    for branch in localbranches:
        lb = localbranches[branch]
        if lb.tracking_branch():
            tracking_branches.append(lb.name)
        elif lb.name in remotebranches:
            not_tracking_branches.append(lb.name)
        else:
            local_only.append(lb.name)

    for name in remotebranchnames - localbranchnames:
        remote_only.append(name)

    # Now we've collected all the info we need. Time to print it out.
    maxlen = min(maxlen, 35)
    fmt = "  %%%ds  %%s" % maxlen

    if tracking_branches:
        print("\nLocal branches tracking remotes:")
        for name in tracking_branches:
            print(fmt % (name,
                         " -> %s" % localbranches[name].tracking_branch().name))

    if not_tracking_branches:
        print("\nLocal branches that aren't tracking their remotes:")
        for name in not_tracking_branches:
            print(fmt % (name, " vs  %s" % remotebranches[name].name))

            if add_tracking:
                # The local branch already exists, just needs to
                # be set to track the remote of the same name.
                print("Setting local %s to track %s"
                      % (name, remotebranches[name].name))
                localbranches[name].set_tracking_branch(remotebranches[name])

    if remote_only:
        print("\nRemote-only branches, not mirrored here:")
        for name in remote_only:
            print(fmt % remotebranches[name].name)

            if add_tracking:
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
                print("Created branch %s to track %s" % (name,
                                                         remotebranches[name]))

    if local_only:
        print("\nLocal-only branches, not tracking a remote")
        for name in local_only:
            print(fmt % (name, ""))

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Check git branches vs. upstream.',
        epilog='''Won't make changes to the repo unless -t is specified.
With no arguments, -lc is the default.

Examples:
Show status of a repo: %(prog)s -fc
Update a repo so remote branches are tracked: %(prog)s -ft
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
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
    parser.add_argument('-s', "--silent", dest="silent", default=False,
                        action="store_true",
                        help='Suppress output of -c (for use in scripts)')
    parser.add_argument('repo', nargs='?', default='.',
                        help='The git repo: defaults to the current directory')

    args = parser.parse_args()

    # By default (no arguments specified), do -cl, i.e. check and list.
    if not args.list and not args.check and not args.track:
        args.list = True
        args.check = True

    repo = Repo(args.repo)

    retval = 0

    # Fetch, if specified, always needs to happen first.
    if args.fetch:
        fetch_from_upstream(repo)

    # If we're adding tracking info, do that first so check and list
    # will reflect what we changed.
    if args.track:
        list_branches(repo, True)

    if args.check:
        retval = check_push_status(repo, args.silent)

    if args.list:
        list_branches(repo, False)

    return retval

if __name__ == '__main__':
    sys.exit(main())
