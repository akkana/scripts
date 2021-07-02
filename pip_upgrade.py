#!/usr/bin/env python3

# Upgrade packages in a virtualenv -- but only the packages that
# are in that virtualenv, not site packages.

import os, sys
from pathlib import Path
import subprocess
import re


VENVLOC = os.environ["VIRTUAL_ENV"]
if not VENVLOC:
    print("Not in a virtualenv!")
    sys.exit(1)


def update_virtualenv():
    packagenames, versions = get_installed_packages()
    for pkg, version in zip(packagenames, versions):
        print(pkg, version)

    cmd = ["pip", "install", "-U", *packagenames]
    print("Calling:", cmd)
    subprocess.call(cmd)


def get_installed_packages():
    package_dir = find_package_dir()
    packagenames = []
    packageversions = []
    for infodir in package_dir.glob("*-*-info"):
        parts = infodir.name.split('-')
        if not parts[1].endswith("dist"):
            print("bad parts!")
            continue
        version = parts[1][:-4]
        if version.endswith('.'):
            version = version[:-1]
        if Path(package_dir, parts[0]).exists():
            packagenames.append(parts[0])
            packageversions.append(version)

    return packagenames, packageversions


def find_package_dir():
    for pydir in Path(VENVLOC, "lib").glob("python*"):
        site_packages = Path(pydir, "site-packages")
        if site_packages.exists():
            return site_packages

    return None


if __name__ == '__main__':
    update_virtualenv()

