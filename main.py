from bs4 import BeautifulSoup
from currency_and_conversion import Currency
import time
import urllib.request
import sys

from steamapp import SteamApp

if len(sys.argv) > 2:
    SteamApp.application_limit = int(sys.argv[2])


def throttle_request(start_time=time.time()):
    # Make sure at least 1 second has passed before requesting another page from steam
    time.sleep(max(1.5 - (time.time() - start_time), 0))


def initialize_app_with_currency(app: SteamApp, currency: Currency):
    try:
        # get the steam page for the app in that region
        with urllib.request.urlopen(
            "https://store.steampowered.com/api/appdetails?appids={}&cc={}".format(
                app.ID, currency.to_region_code()
            )
        ) as app_url:
            app_soup = BeautifulSoup(app_url, features="html.parser")
            formatted_html = app_soup.prettify()

            # first check if the app is sold in that region
            if formatted_html.find('"success":false') != -1:
                app.price[currency] = "NA"
                return

            # find the price
            price_expression = 'price_in_cents_with_discount":'

            price_idx = formatted_html.find(price_expression) + len(price_expression)
            price_end_idx = formatted_html.find("}", price_idx)

            price_in_cents = Currency.parse_price(
                formatted_html[price_idx:price_end_idx]
            )

            # convert the price from cents into whole dollars
            app.price[currency] = round(price_in_cents / 100, 2)
    except urllib.error.HTTPError:
        # sleep for 1 minute before doing any more requests
        print("Received an HTTPError. Waiting 1 minute before proceeding...")
        time.sleep(60)
        print("Resumed.")
        initialize_app_with_currency(app, currency)


def initialize_apps_with_currency(currency: Currency):
    with urllib.request.urlopen(
        # the below link has been chosen in particular to ignore preferences and to search for paid games only
        # the expression after the ampersand is to get the price in the specified region
        "https://store.steampowered.com/search/?category1=998&hidef2p=1&ndl=1&ignore_preferences=1&cc="
        + currency.to_region_code()
    ) as search_url:
        search_soup = BeautifulSoup(search_url, features="html.parser")
        formatted_html = search_soup.prettify()

        last_index = 0

        search_expression = "https://store.steampowered.com/app/"

        while last_index != -1:
            # get the indices of the games within the formatted string. All apps are displayed as "https://store.steampowered.com/app/<APP_ID>/<APP_NAME>/..."
            app_raw_string_idx = formatted_html.find(search_expression, last_index)

            if app_raw_string_idx == -1:
                break

            # add the length of the search expression to the index so that the given index is the first number of the app's ID
            app_raw_string_idx += len(search_expression)

            # get the closing slash after the app ID
            closing_slash_ID = formatted_html.find("/", app_raw_string_idx)

            # get the closing slash after the app name
            closing_slash_name_idx = formatted_html.find("/", closing_slash_ID + 1)

            # substring and split so all that's left is `[<APP_ID>, <APP_NAME>]`
            app_data_sub = formatted_html[
                app_raw_string_idx:closing_slash_name_idx
            ].split("/")

            # instantiate a new SteamApp object, keeping the app limit in mind if one has not already been created,
            # or fetch the already created one if it has been previously created
            app = None

            last_index = app_raw_string_idx

            if app_data_sub[0] in SteamApp.applications:
                app = SteamApp.applications[app_data_sub[0]]
            elif len(SteamApp.applications) < SteamApp.application_limit:
                app = SteamApp(app_data_sub[0], app_data_sub[1].replace("_", " "))
            else:
                continue

            # search for the following tag to get the game's price
            price_expression = '<div class="discount_final_price">'

            # search for the closing bracket after the above expression
            price_idx = formatted_html.find(
                price_expression, closing_slash_name_idx
            ) + len(price_expression)

            price_closing_idx = formatted_html.find("</div>", price_idx)

            # parse the price
            app_price = Currency.parse_price(
                formatted_html[price_idx:price_closing_idx]
            )

            app.price[currency] = app_price


def write_to_csv(output_currency=sys.argv[1] if len(sys.argv) > 1 else None):
    if output_currency is None:
        raise TypeError()

    if not isinstance(output_currency, Currency):
        output_currency = Currency[output_currency]

    with open("steam_pricing_data.csv", "w") as output_file:
        output_file.write(
            "Games with Regional Prices in {},".format(output_currency.name)
        )

        # first row is the title which features all the currencies, and the currency with the lowest regional price at the end
        output_file.write(
            ",".join([currency.name for currency in Currency])
            + ",Lowest Regional Price\n"
        )

        # each row after that is an app and its prices converted to the wanted region in the column
        for app in SteamApp.applications.values():
            output_file.write(app.name + ",")

            prices_in_output_currency_list = {}

            # get the app's price in the current region and convert it to the output currency
            i = 0
            for currency in Currency:
                # convert the price from the current currency to the output currency
                converted_price = app.convert_region_from_to(currency, output_currency)

                # for us to find the lowest regional price, convert "NA's" into -1 so comparisons can be made
                prices_in_output_currency_list[currency.name] = (
                    converted_price if converted_price != "NA" else float("inf")
                )

                output_file.write(str(converted_price) + ",")

                i += 1

            # write the currency with the lowest regional price
            output_file.write(
                min(
                    prices_in_output_currency_list,
                    key=prices_in_output_currency_list.get,
                )
                + "\n"
            )

    print("Wrote data to csv.")


if __name__ == "__main__":
    # obtain the prices for all apps on the steam search page
    for currency in Currency:
        start_time = time.time()
        print("Obtaining prices in currency: " + currency.name + "...")
        initialize_apps_with_currency(currency)
        print("Prices obtained.")
        throttle_request(start_time)

    last_request_time = time.time()

    # obtain the prices for all apps that are missing any regions (as some apps may show up on one region's default search page and not another region's)

    # get the number of missing regions for all apps to keep track of progress
    expected_total = len(Currency) * len(SteamApp.applications)
    actual_total = 0

    # count how many fixes were made
    fixes = 1

    for app in SteamApp.applications.values():
        actual_total += len(app.price)

    print(
        "{} / {} prices ({}%) were successfully obtained".format(
            actual_total, expected_total, round(actual_total / expected_total * 100, 2)
        )
    )

    for app in SteamApp.applications.values():
        for currency in Currency:
            if currency not in app.price:
                print(
                    "App '{}' is missing its value in currency '{}'. Fixing {}/{} ({}%) ...".format(
                        app.name,
                        currency.name,
                        fixes,
                        expected_total - actual_total,
                        round(fixes / (expected_total - actual_total) * 100, 2),
                    )
                )

                initialize_app_with_currency(app, currency)
                throttle_request(last_request_time)
                print(
                    "Fixed. App '{}' now has the following price with currency '{}': {}".format(
                        app.name, currency.name, app.price[currency]
                    )
                )

                fixes += 1

                last_request_time = time.time()

    write_to_csv()
