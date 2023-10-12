#!/usr/bin/env python3

# Watch a web page, summarizing the specific part you care about.
# Uses selenium so that JavaScript and dynamically loaded pages work.
#
# For instance, if you're trying to buy a car and the manufacturer
# has a page showing inventory for a particular zip code and set of options,
# but you're willing to travel or to accept several combinations of options,
# you can monitor several pages to see what comes up.
#
# Copyright 2023 by Akkana Peck; share and enjoy under the GPLv2 or later.


from selenium import webdriver

# If you need to wait for something to load after the basic page has
# finished loading. I haven't needed that yet, so this is untested.
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

from sys import argv, stderr, exit
from os.path import join, expanduser, exists
from os import listdir
from importlib import import_module


Verbose = False


def start_selenium_driver_firefox(headless=True, profile=None):
    """Run the Firefox driver, using the first profile with a name
       that includes "selenium". If none, selenium will default to
       creating a new profile.
    """
    from selenium.webdriver.firefox.options import Options
    options = Options()

    if headless:
        options.add_argument('--headless')

    mozdir = expanduser("~/.mozilla/firefox/")
    if profile:
        if exists(profile):
            foxprofiledir = profile
        else:
            foxprofiledir = join(mozdir, profile)
            if not exists(foxprofiledir):
                print("Can't find Firefox profile", profile, file=stderr)
                exit(1)
    else:
        # Return the first profile in ~/.mozilla/firefox/
        # that has "selenium" in its name.
        foxprofiledir = None
        for pdir in listdir(mozdir):
            if "selenium" in pdir:
                foxprofiledir =  join(mozdir, pdir)
                break

    if foxprofiledir:
        if Verbose:
            print("Using Firefox profile dir", foxprofiledir)

        # Old way, doesn't work any more:
        # driver = webdriver.Firefox(firefox_profile=foxprofiledir)
        options.set_capability("moz:firefoxOptions", {
            "args":["-profile", foxprofiledir]
        })
    return webdriver.Firefox(options=options)
    #                  , service=Service(GeckoDriverManager().install()))


def start_selenium_driver_chrome(headless=True):
    """Use chrome or chromium instead of firefox.
       Warning: not tested much.
    """
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.binary_location = '/usr/bin/chromium'
    if headless:
        opts.add_argument('--headless')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-sandbox')

    return  webdriver.Chrome(options=opts)


def parse_args():
    """Parse commandline arguments."""

    import argparse

    parser = argparse.ArgumentParser(description="Summarize web pages")

    # Boolean flag (don't use type=bool, gives a TypeError)
    parser.add_argument('-v', "--verbose", dest="verbose", default=False,
                        action="store_true",
                        help="Print verbose messages and show browser window")
    parser.add_argument('-c', "--chrome", dest="chrome", default=False,
                        action="store_true",
                        help="Use Chrome/Chromium instead of Firefox")
    parser.add_argument('-p', "--profile", dest="profile", default=None,
                        action="store",
                        help="Firefox profile to use, " \
                             "(full path or name in ~/.mozilla/firefox: " \
                             "if not specified, will look for a profile " \
                              "with 'selenium' in the name)")
    parser.add_argument('modules', nargs='+',
                        help="Python modules to import to parse web pages")
    return parser.parse_args(argv[1:])


if __name__ == '__main__':
    args = parse_args()

    Verbose = args.verbose

    if args.chrome:
        if Verbose:
            print("Starting selenium with chrome driver ...")
        driver = start_selenium_driver_chrome(headless=(not Verbose))
    else:
        if Verbose:
            print("Starting selenium with firefox driver ...")
        driver = start_selenium_driver_firefox(headless=(not Verbose),
                                               profile=args.profile)

    for modname in args.modules:
        if Verbose:
            print("Importing module", modname)
        module = import_module(modname)
        if Verbose:
            print(f"Calling {modname}.summarize()")
        module.summarize(driver)

