from enum import Enum
from datetime import date
from bs4 import BeautifulSoup
import re
import json
import urllib.request
from dotenv import load_dotenv
import os
import sys

conversion_rates = {}

# some regions are priced in USD rather than their native currencies
regions_priced_in_usd = [
    "TRY",
    "ARS",
]


class Currency(Enum):
    USD = 1  # United States
    CAD = 2  # Canada
    UAH = 3  # Ukraine
    TRY = 4  # Turkey
    ARS = 5  # Argentina
    BRL = 6  # Brazil
    AUD = 7  # Australia
    JPY = 8  # Japan
    KRW = 9  # South Korea
    CNY = 10  # China
    PLN = 11  # Poland
    MXN = 12  # Mexico
    INR = 13  # India
    SAR = 14  # Saudi Arabia
    ZAR = 15  # South Africa
    PHP = 16  # Philippines
    VND = 17  # Vietnam
    IDR = 18  # Indonesia
    KZT = 19  # Kazakhstan
    MYR = 20  # Malaysia
    CLP = 21  # Chile
    TWD = 22  # Taiwan

    @staticmethod
    def initialize_conversion_rates():
        load_dotenv()
        api_key = os.getenv("EXCHANGE_RATE_API_KEY") or sys.argv[3]

        with (
            open("conversion_rates.json", "w") as conversion_rates_file,
            urllib.request.urlopen(
                "https://v6.exchangerate-api.com/v6/{}/latest/USD".format(api_key)
            ) as conversion_rates_html,
        ):
            updated_json = {"date_updated": date.today().strftime("%d/%m/%Y")}

            currency_soup = BeautifulSoup(conversion_rates_html, features="html.parser")
            api_conversion_json = json.loads(str(currency_soup))["conversion_rates"]

            # get all the currencies in the json that are in the Currency enum
            for currency in Currency:
                updated_json[currency.name] = (
                    api_conversion_json[currency.name]
                    if currency.name not in regions_priced_in_usd
                    else api_conversion_json["USD"]
                )

            json.dump(updated_json, conversion_rates_file)
            print("Conversion rates have been updated.")

            return updated_json

    @staticmethod
    # cleans up the raw price string to only have numerical values (or periods)
    # TODO: FIX
    def parse_price(price):
        cleaned_price = re.sub(r"[^0-9.,]", "", price.strip())

        # if there are two consecutive decimals, there was a missing html price tag so skip this evaluation step
        if len(cleaned_price) >= 3 and ".." not in cleaned_price:
            # if the third from last character is a comma, treat it as a decimal separator
            if cleaned_price[-3] == ",":
                cleaned_price = cleaned_price[:-3] + "." + cleaned_price[-2:]

            # remove all periods except for any that may be used as decimal separators
            cleaned_price = cleaned_price[:-3].replace(".", "") + cleaned_price[-3:]

        try:
            return float(cleaned_price.replace(",", ""))
        except ValueError:
            return "NA"

    @staticmethod
    def update_conversion_rates():
        try:
            with open("conversion_rates.json", "r") as conversion_rates:
                rates = json.load(conversion_rates)

                # exit the function if the data has already been updated today
                if rates["date_updated"] == date.today().strftime("%d/%m/%Y"):
                    print("Conversion rates have already been updated today.")
                    return rates

                return Currency.initialize_conversion_rates()

        except (FileNotFoundError, json.JSONDecodeError):
            # overwrite the file with new data
            print(
                "There was an error when trying to read from 'conversion_rates.json'. The file will be updated."
            )
            return Currency.initialize_conversion_rates()

    def to_region_code(self):
        # the region code steam uses is the first two letters of the currency in ISO 4217
        return self.name[:2].lower()


# the following will run before main
conversion_rates = Currency.update_conversion_rates()
del conversion_rates["date_updated"]
