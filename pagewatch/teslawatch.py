#!/usr/bin/env python3

"""An example module to be used with pagewatch.py.
   Modules must provide a summarize(driver) function,
   where driver is a selenium driver already initialized.

   summarize(driver) should load one or more URLs, parse
   using selenium functions, then do something with the result.
   This may include printing output, generating an RSS file,
   emailing someone, etc.
   pagewatch is agnostic on what modules do with the summary they produce.
"""


# https://stackoverflow.com/a/76766125
from selenium.webdriver.common.by import By


# Zip code to be added separately
url = "https://www.tesla.com/inventory/new/m3?PAINT=BLUE&INTERIOR=PREMIUM_WHITE&arrangeby=relevance&zip=%s&range=0"


def summarize(driver):
    """Load page(s) in the selenium driver provided, and summarize.
    """
    # get_cars_for_zip("87547")
    # Also Vegas 89117, CO Springs 80905
    # print("\n")

    get_cars_for_zip(driver, "80905")


def get_cars_for_zip(driver, zipcode):
    driver.get(url % zipcode)

    # fullhtml = webdriver.page_source

    cards = driver.find_elements(By.XPATH,
                                 "//article[@class='result card']")
    # Wait for dynamic content to load
    # cards = WebDriverWait(driver, 20) \
    #     .until(EC.visibility_of_element_located((
    #         By.XPATH,
    #         "//article[@class='result' or @class=' card']"
    #     )))

    # print("Cards:", cards)

    for card in cards:
        print()

        basic_info = card.find_element(By.CSS_SELECTOR,
                                       "div.result-basic-info") \
                         .find_element(By.CSS_SELECTOR, "div") \
                         .get_attribute('innerHTML')
        print("Basic info:", basic_info)

        featurelist = card.find_element(By.CSS_SELECTOR,
                                        "ul.result-regular-features")
        features = [ f.get_attribute('innerHTML')
                     for f in featurelist.find_elements(By.CSS_SELECTOR,
                                                        "li") ]
        print("Features:", features)

        price = card.find_element(By.CSS_SELECTOR,
                                  'span.result-purchase-price') \
                    .get_attribute('innerHTML')
        print("Price:", price)

