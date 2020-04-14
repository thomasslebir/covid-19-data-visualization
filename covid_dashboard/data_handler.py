import math
import requests

import numpy as np
import pandas as pd


class CovidDataHandler:
    def __init__(self, world_data_url=None, iso_country_url=None, regions_continents_url=None, as_at_date=None):
        # URLs
        if world_data_url is None:
            self.world_data_url = r"https://www.ecdc.europa.eu/sites/default/files/documents/COVID-19-geographic" \
                                  r"-disbtribution-worldwide-"
        else:
            self.world_data_url = world_data_url

        if iso_country_url is None:
            self.iso_country_url = (
                r"https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes"
            )
        else:
            self.iso_country_url = iso_country_url

        if regions_continents_url is None:
            self.regions_continents_url = (
                r"http://statisticstimes.com/geography/countries-by-continents.php"
            )
        else:
            self.regions_continents_url = regions_continents_url

        # Others
        if as_at_date is None:
            self.as_at_date = pd.Timestamp.today()
        else:
            self.as_at_date = pd.Timestamp(as_at_date)

        # Data holders
        self.covid_country_raw_data = None
        self.covid_country_data_date = None
        self.covid_country_data = None
        self.covid_usa_data = None
        self.covid_usa_data_date = None
        self.iso_country_codes = None
        self.iso_country_codes_dropped = None
        self.regions_continents_data = None

    def generate_country_level_dataset(self, as_at_date=None, max_consecutive_dates=5, walk_back=True):
        # Retrieve all data for country-level dataset
        self.covid_country_raw_data = self.get_latest_ecdc_data(as_at_date=as_at_date,
                                                                max_consecutive_dates=max_consecutive_dates,
                                                                walk_back=walk_back)
        self.iso_country_codes = self.get_iso_country_codes_data()
        self.regions_continents_data = self.get_regions_continents_data()

        # Check that all data is available
        data_sets = [self.covid_country_raw_data, self.iso_country_codes, self.regions_continents_data]
        integrity_check = [ds for ds in data_sets if ds is None]
        if len(integrity_check):
            print("Unable to generate country-level dataset as the following are None: {}.".format(integrity_check))
            return

        self.covid_country_data = self.create_country_level_dataset(self.covid_country_raw_data, self.iso_country_codes,
                                                                    self.regions_continents_data)

    def get_latest_ecdc_data(self, url=None, as_at_date=None, max_consecutive_dates=5, walk_back=True):
        """
        Returns a DataFrame of the latest Covid-19 numbers by country as posted daily on the ECDC website.
    
        Args:
            url (str): Download link for daily .xls file. If file_link is None, the function defaults to the last
            known location as a convenience.
            as_at_date (Union[str, datetime.date, pd.Timestamp]): Starting date for file download tries. If file_date
            is None, the function defaults to today.
            max_consecutive_dates (int): Number of days to walk back or forward if the current date's file is not
            available.
            walk_back (bool): Way to increment dates for file matching in time. If walk_back is True, the function
            will decrement dates until max_consecutive_dates is reached or a valid link is found. Otherwise, the
            function will increment dates.
            
        Returns:
            pd.DataFrame
        """
        # Default arguments
        if url is None:
            url = self.world_data_url

        if as_at_date is None:
            as_at_date = self.as_at_date
        else:
            as_at_date = pd.Timestamp(as_at_date)

        # Request file
        try:
            file_url = "{}{:%Y-%m-%d}.xlsx".format(url, as_at_date)
            resp = requests.get(file_url)
        except:
            print("Invalid URL.")
            return

        # Loop back/forward in dates while GET fails
        while resp.status_code != 200 and max_consecutive_dates > 1:
            print("File retrieval failed for {:%Y-%m-%d}.".format(as_at_date))
            if walk_back:
                as_at_date -= pd.Timedelta("1d")
            else:
                as_at_date += pd.Timedelta("1d")
            max_consecutive_dates -= 1
            file_url = "{}{:%Y-%m-%d}.xlsx".format(url, as_at_date)
            resp = requests.get(file_url)

        if resp.status_code != 200:
            print("File retrieval failed for {:%Y-%m-%d}.".format(as_at_date))
            print("Maximum number of consecutive dates reached. Please check if URL is correct or expand date window "
                  "using max_consecutive_dates argument.")
            return

        self.covid_country_data_date = as_at_date

        df = pd.read_excel(resp.content)
        df.columns = ["date_rep", "day", "month", "year", "cases", "deaths", "country", "alpha_2_code", "alpha_3_code",
                      "population_2018"]

        return df

    def get_iso_country_codes_data(self, url=None, table_index=0, matching_length=True):
        """
        Returns a DataFrame of country codes from Wikipedia.
    
        Args:
            url (str): Link to the Wikipedia page of ISO country codes.
            table_index (int): Index of the table within the HTML elements.
            matching_length (bool): If True, only keeps ISO codes that respect string length requirements for both
            columns.
            
        Returns:
            pd.DataFrame
        """
        # Default arguments
        if url is None:
            url = self.iso_country_url

        # Read HTML tables
        tables = pd.read_html(url)

        # Load & format
        df = tables[table_index]
        df.columns = df.columns.droplevel()
        df.columns = [c.split("[")[0].strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
        df["alpha_2_code"].iloc[0] = "AF"

        # Filter out countries where alpha_3_codes are too long
        if matching_length:
            df_dropped = df[df["alpha_3_code"].str.len() > 3].copy()
            df = df[df["alpha_3_code"].str.len() == 3].copy()
            self.iso_country_codes_dropped = df_dropped

        return df

    def get_regions_continents_data(self, url=None, table_index=2):
        """
        Returns a DataFrame of region and continent classification for each country.
    
        Args:
            url (str): Link to the webpage.
            table_index (int): Index of the table within the HTML elements.
            
        Returns:
            pd.DataFrame
        """
        # Default argument
        if url is None:
            url = self.regions_continents_url

        # Read HTML tables
        tables = pd.read_html(url)

        # Load & format
        df = tables[table_index]
        df.drop(columns=["No"], inplace=True)
        df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]

        return df

    @staticmethod
    def create_country_level_dataset(df_ecdc=None, df_iso=None, df_regions=None):
        """
        Returns a clean dataset composed by assembling ECDC data and Wikipedia ISO country data.
        Ensures all countries are included and span all dates for compatibility with Plotly.
        Adds additional metrics per country: cumulative cases, cumulative deaths, mortality rate,
        % of population infected, % of population deaths.
        
        Args:
            df_ecdc (pd.DataFrame): DataFrame from raw data published daily by the ECDC.
            df_iso (pd.DataFrame): DataFrame of table of country codes from Wikipedia.
            df_regions (pd.DataFrame): DataFrame of regional and continental classification for each country.
            
        Returns:
            pd.DataFrame
        """
        # Safety check
        if any(x is None for x in [df_ecdc, df_iso, df_regions]):
            print("One or more DataFrame is missing (of type None), please check.")
            return

        # Format
        df = df_ecdc.copy()
        df.drop(columns=["day", "month", "year"], inplace=True)
        df["date_rep"] = df["date_rep"].astype(str)
        df["cum_cases"] = None
        df["cum_deaths"] = None
        df.dropna(subset=["alpha_3_code"], inplace=True)

        # List all dates and missing countries
        all_dates = (pd.date_range(df["date_rep"].min(), df["date_rep"].max()).astype(str).tolist())
        missing_countries = list(set(df_iso["alpha_3_code"]).difference(set(df_ecdc["alpha_3_code"])))
        frames = []

        # Fill in dates for countries already included in df_ecdc
        for alpha_3_code in df["alpha_3_code"].unique():
            try:
                df_country = df[df["alpha_3_code"] == alpha_3_code].copy()
                # Additional dates
                dates_to_add = list(
                    set(all_dates).difference(set(df_country["date_rep"]))
                )
                df_to_add = pd.DataFrame({"date_rep": dates_to_add})
                for col in ["cases", "deaths"]:
                    df_to_add[col] = 0
                for col in ["country", "alpha_2_code", "alpha_3_code", "population_2018"]:
                    df_to_add[col] = df_country[col].iloc[0]
                # Concatenate both
                df_temp = pd.concat([df_country, df_to_add], ignore_index=True)
                df_temp.sort_values(by="date_rep", inplace=True)
                # Add cumulative counts
                df_temp["cum_cases"] = df_temp["cases"].cumsum()
                df_temp["cum_deaths"] = df_temp["deaths"].cumsum()
                frames.append(df_temp)
            except:
                print("Issue encountered while adding dates to country code {}.".format(alpha_3_code))

        # Fill in missing countries
        for alpha_3_code in missing_countries:
            df_missing = pd.DataFrame({"date_rep": all_dates})
            for col in ["cases", "deaths", "cum_cases", "cum_deaths"]:
                df_missing[col] = 0
            for col in ["alpha_2_code", "alpha_3_code"]:
                df_missing[col] = df_iso.loc[df_iso["alpha_3_code"] == alpha_3_code, col].iloc[0]
            df_missing["country"] = df_iso.loc[df_iso["alpha_3_code"] == alpha_3_code, "country_name"].iloc[0]
            df_missing["population_2018"] = np.NaN

        # Create full DataFrame
        df = pd.concat(frames, ignore_index=True)
        df.sort_values(by=["country", "date_rep"], inplace=True)

        # Add indicators
        df["mortality_rate"] = (df["cum_deaths"] / df["cum_cases"]).fillna(0)
        df["fraction_infected"] = df["cum_cases"] / df["population_2018"]
        df["fraction_deaths"] = df["cum_deaths"] / df["population_2018"]
        df["infections_growth_rate"] = df["cum_cases"].pct_change()
        df["deaths_growth_rate"] = df["cum_deaths"].pct_change()
        for col in ["infections_growth_rate", "deaths_growth_rate"]:
            cd_nan = (df["date_rep"] == df["date_rep"].min()) | (df[col] == math.inf)
            df.loc[cd_nan, col] = np.NaN

        # Merge regions/continents
        df = df.merge(df_regions[["iso_alpha3_code", "region_1", "region_2", "continent"]], how="left",
                      left_on="alpha_3_code", right_on="iso_alpha3_code").drop(columns=["iso_alpha3_code"])
        country_exceptions = {"Kosovo": "Europe", "Taiwan": "Asia", "Bonaire": "South America"}
        for ce in country_exceptions:
            df.loc[df["country"] == ce, "continent"] = country_exceptions[ce]
        df["country"] = df["country"].str.replace("_", " ")

        return df
