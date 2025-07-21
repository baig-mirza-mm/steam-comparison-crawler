from currency_and_conversion import conversion_rates


class SteamApp:
    applications = {}

    # a maximum of how many apps we care about searching for
    application_limit = 100

    def __init__(self, ID, name):
        # this is a hard-coded failsafe in case something outside of this class wants to append extraneous elements to the applications dict
        if len(SteamApp.applications) > SteamApp.application_limit:
            return

        self.ID = ID
        self.name = name

        self.price = {}

        SteamApp.applications[self.ID] = self

    def convert_region_from_to(self, region_from, region_to):
        if self.price[region_from] == "NA":
            return "NA"

        # dividing by the rate converts it to USD and multiplying it converts it back
        return (
            float(self.price[region_from])
            / conversion_rates[region_from.name]
            * conversion_rates[region_to.name]
        )
