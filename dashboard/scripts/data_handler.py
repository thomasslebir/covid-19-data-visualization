import logging
import math
import os
import re

import requests
import numpy as np
import pandas as pd

DEFAULT_URLS = {"world_data":               "https://www.ecdc.europa.eu/sites/default/files/documents/"
                                            "COVID-19-geographic-disbtribution-worldwide-",
                "iso_country":              "https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes",
                "regions_continents":       "http://statisticstimes.com/geography/countries-by-continents.php",
                "usa_state_data":           "https://raw.githubusercontent.com/nytimes/covid-19-data/master/"
                                            "us-states.csv",
                "usa_county_data":          "https://raw.githubusercontent.com/nytimes/covid-19-data/master/"
                                            "us-counties.csv",
                "usa_state_codes":          "https://www.nrcs.usda.gov/wps/portal/nrcs/detail/?cid=nrcs143_013696",
                "usa_county_geojson":       "https://raw.githubusercontent.com/plotly/datasets/master/"
                                            "geojson-counties-fips.json",
                "usa_state_population":     "https://www2.census.gov/programs-surveys/popest/tables/2010-2019/"
                                            "state/totals/nst-est2019-01.xlsx",
                "usa_county_population":    "https://www2.census.gov/programs-surveys/popest/tables/2010-2019/"
                                            "counties/totals/co-est2019-annres.xlsx"}

LOGGER = logging.getLogger(__name__)


class CovidDataHandler:
    def __init__(self, world_data_url=None, iso_country_url=None, regions_continents_url=None,
                 usa_state_data_url=None, usa_county_data_url=None, usa_state_codes_url=None,
                 usa_county_geojson_url=None, usa_state_population_url=None, usa_county_population_url=None,
                 as_at_date=None):
        LOGGER.info("Instantiating data handler")
        # URLs
        if world_data_url is None:
            self.world_data_url = DEFAULT_URLS["world_data"]
        else:
            self.world_data_url = world_data_url

        if iso_country_url is None:
            self.iso_country_url = DEFAULT_URLS["iso_country"]
        else:
            self.iso_country_url = iso_country_url

        if regions_continents_url is None:
            self.regions_continents_url = DEFAULT_URLS["regions_continents"]
        else:
            self.regions_continents_url = regions_continents_url

        if usa_state_data_url is None:
            self.usa_state_data_url = DEFAULT_URLS["usa_state_data"]
        else:
            self.usa_state_data_url = usa_state_data_url

        if usa_county_data_url is None:
            self.usa_county_data_url = DEFAULT_URLS["usa_county_data"]
        else:
            self.usa_county_data_url = usa_county_data_url

        if usa_state_codes_url is None:
            self.usa_state_codes_url = DEFAULT_URLS["usa_state_codes"]
        else:
            self.usa_state_codes_url = usa_state_codes_url

        if usa_county_geojson_url is None:
            self.usa_county_geojson_url = DEFAULT_URLS["usa_county_geojson"]
        else:
            self.usa_county_geojson_url = usa_county_geojson_url

        if usa_state_population_url is None:
            self.usa_state_population_url = DEFAULT_URLS["usa_state_population"]
        else:
            self.usa_state_population_url = usa_state_population_url

        if usa_county_population_url is None:
            self.usa_county_population_url = DEFAULT_URLS["usa_county_population"]
        else:
            self.usa_county_population_url = usa_county_population_url

        # Others
        if as_at_date is None:
            self.as_at_date = pd.Timestamp.today()
        else:
            self.as_at_date = pd.Timestamp(as_at_date)

        # Data holders
        self.covid_country_raw_data = None
        self.covid_country_data_date = None
        self.covid_country_data = None
        self.covid_usa_state_data = None
        self.covid_usa_county_data = None
        self.covid_usa_data_date = None
        self.iso_country_codes = None
        self.iso_country_codes_dropped = None
        self.regions_continents_data = None

    def generate_all_datasets(self, as_at_date=None, max_consecutive_dates=5, walk_back=True):
        LOGGER.info("Starting generation of all data")
        self.generate_country_level_dataset(as_at_date=as_at_date, max_consecutive_dates=max_consecutive_dates,
                                            walk_back=walk_back)
        self.generate_usa_datasets()
        LOGGER.info("All data generated")

    def generate_country_level_dataset(self, as_at_date=None, max_consecutive_dates=5, walk_back=True):
        LOGGER.info("Starting generation of country-level data")
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
            LOGGER.warning("Unable to generate country-level dataset as the following are None: {}.".format(integrity_check))
            return

        self.covid_country_data = self.create_country_level_dataset(self.covid_country_raw_data, self.iso_country_codes,
                                                                    self.regions_continents_data)

    def generate_usa_datasets(self):
        LOGGER.info("Starting generation of USA state and county-level data")
        self.covid_usa_state_data = self.generate_usa_state_data()
        self.covid_usa_county_data = self.generate_usa_county_data()

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
        LOGGER.info("Generating ECDC datsaset")
        # Check if file exists
        file_name = "{:%Y%m%d}_ecdc_data.csv".format(self.as_at_date)
        file_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        file_path = os.path.join(file_folder, file_name)
        if os.path.isfile(file_path):
            LOGGER.info("Reading from file")
            df = pd.read_csv(file_path)
            LOGGER.info("ECDC data ready")
            return df

        LOGGER.info("Day file not found, generating from scratch")
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
            LOGGER.warning("Invalid URL.")
            return

        # Loop back/forward in dates while GET fails
        while resp.status_code != 200 and max_consecutive_dates > 1:
            LOGGER.warning("File retrieval failed for {:%Y-%m-%d}.".format(as_at_date))
            if walk_back:
                as_at_date -= pd.Timedelta("1d")
            else:
                as_at_date += pd.Timedelta("1d")
            max_consecutive_dates -= 1
            file_url = "{}{:%Y-%m-%d}.xlsx".format(url, as_at_date)
            resp = requests.get(file_url)

        if resp.status_code != 200:
            LOGGER.warning("File retrieval failed for {:%Y-%m-%d}.".format(as_at_date))
            LOGGER.warning("Maximum number of consecutive dates reached. Please check if URL is correct or expand "
                           "date window using max_consecutive_dates argument.")
            return

        self.covid_country_data_date = as_at_date

        df = pd.read_excel(resp.content)
        df.columns = ["date_rep", "day", "month", "year", "cases", "deaths", "country", "alpha_2_code", "alpha_3_code",
                      "population_2018", "ecdc_continent"]
        df["date_rep"] = pd.to_datetime(df["date_rep"], dayfirst=True).astype(str)

        # Export file to csv and delete previous files
        LOGGER.info("Exporting ECDC data")
        self._export_and_clean(df, file_folder, file_name)
        LOGGER.info("ECDC data ready")

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
        LOGGER.info("Generating ISO country codes")
        # Check if file exists
        file_name = "{:%Y%m%d}_iso_country_codes.csv".format(self.as_at_date)
        file_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        file_path = os.path.join(file_folder, file_name)
        if os.path.isfile(file_path):
            LOGGER.info("Reading from file")
            df = pd.read_csv(file_path)
            LOGGER.info("ISO country codes ready")
            return df

        LOGGER.info("Day file not found, generating from scratch")
        # Default arguments
        if url is None:
            url = self.iso_country_url

        # Read HTML tables
        LOGGER.info("Reading data")
        tables = pd.read_html(url)

        # Load & format
        LOGGER.info("Formatting data")
        df = tables[table_index]
        df.columns = df.columns.droplevel()
        df.columns = [c.split("[")[0].strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
        df["alpha_2_code"].iloc[0] = "AF"

        # Filter out countries where alpha_3_codes are too long
        if matching_length:
            LOGGER.info("Dropping invalid entries")
            df_dropped = df[df["alpha_3_code"].str.len() > 3].copy()
            df = df[df["alpha_3_code"].str.len() == 3].copy()
            self.iso_country_codes_dropped = df_dropped

        # Export & clean
        LOGGER.info("Exporting ISO country codes")
        self._export_and_clean(df, file_folder, file_name)
        LOGGER.info("ISO country codes ready")

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
        LOGGER.info("Generating regions & continents data")
        # Check if file exists
        file_name = "{:%Y%m%d}_regions_continents.csv".format(self.as_at_date)
        file_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        file_path = os.path.join(file_folder, file_name)
        if os.path.isfile(file_path):
            LOGGER.info("Reading from file")
            df = pd.read_csv(file_path)
            LOGGER.info("Regions & continents data ready")
            return df

        LOGGER.info("Day file not found, generating from scratch")
        # Default argument
        if url is None:
            url = self.regions_continents_url

        # Read HTML tables
        LOGGER.info("Reading data")
        tables = pd.read_html(url)

        # Load & format
        LOGGER.info("Formatting data")
        df = tables[table_index]
        df.drop(columns=["No"], inplace=True)
        df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]

        # Export & clean
        LOGGER.info("Exporting regions & continents data")
        self._export_and_clean(df, file_folder, file_name)
        LOGGER.info("Regions & continents data ready")

        return df

    def create_country_level_dataset(self, df_ecdc=None, df_iso=None, df_regions=None):
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
        LOGGER.info("Generating Covid-19 country-level dataset")
        # Safety check
        if any(x is None for x in [df_ecdc, df_iso, df_regions]):
            LOGGER.warning("One or more DataFrame is missing (of type None), please check.")
            return

        # Check if file exits
        file_name = "{:%Y%m%d}_country_level_dataset.csv".format(self.as_at_date)
        file_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        file_path = os.path.join(file_folder, file_name)
        if os.path.isfile(file_path):
            LOGGER.info("Reading from file")
            df = pd.read_csv(file_path)
            LOGGER.info("Country-level dataset ready")
            return df

        LOGGER.info("Day file not found, generating from scratch")
        # Format
        LOGGER.info("Formatting data")
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
        LOGGER.info("Filling missing dates")
        for alpha_3_code in df["alpha_3_code"].unique():
            try:
                df_country = df[df["alpha_3_code"] == alpha_3_code].copy()
                # Additional dates
                dates_to_add = list(set(all_dates).difference(set(df_country["date_rep"])))
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
        LOGGER.info("Filling missing countries")
        for alpha_3_code in missing_countries:
            df_missing = pd.DataFrame({"date_rep": all_dates})
            for col in ["cases", "deaths", "cum_cases", "cum_deaths"]:
                df_missing[col] = 0
            for col in ["alpha_2_code", "alpha_3_code"]:
                df_missing[col] = df_iso.loc[df_iso["alpha_3_code"] == alpha_3_code, col].iloc[0]
            df_missing["country"] = df_iso.loc[df_iso["alpha_3_code"] == alpha_3_code, "country_name"].iloc[0]
            df_missing["population_2018"] = np.NaN

        # Create full DataFrame
        LOGGER.info("Concatenating tidy dataframes")
        df = pd.concat(frames, ignore_index=True)
        df.sort_values(by=["country", "date_rep"], inplace=True)

        # Add indicators
        LOGGER.info("Calculating indicators")
        df["mortality_rate"] = (df["cum_deaths"] / df["cum_cases"]).fillna(0)
        df["fraction_infected"] = df["cum_cases"] / df["population_2018"]
        df["fraction_deaths"] = df["cum_deaths"] / df["population_2018"]
        df["infections_growth_rate"] = df["cum_cases"].pct_change()
        df["deaths_growth_rate"] = df["cum_deaths"].pct_change()
        for col in ["infections_growth_rate", "deaths_growth_rate"]:
            cd_nan = (df["date_rep"] == df["date_rep"].min()) | (df[col] == math.inf)
            df.loc[cd_nan, col] = np.NaN

        # Merge regions/continents
        LOGGER.info("Merging continent/regional data")
        df = df.merge(df_regions[["iso_alpha3_code", "region_1", "region_2", "continent"]], how="left",
                      left_on="alpha_3_code", right_on="iso_alpha3_code").drop(columns=["iso_alpha3_code"])
        country_exceptions = {"Kosovo": "Europe", "Taiwan": "Asia", "Bonaire": "South America"}
        for ce in country_exceptions:
            df.loc[df["country"] == ce, "continent"] = country_exceptions[ce]
        df["country"] = df["country"].str.replace("_", " ")

        # Export & clean
        LOGGER.info("Exporting country-level dataset")
        self._export_and_clean(df, file_folder, file_name)
        LOGGER.info("Country-level dataset ready")

        return df

    def generate_usa_state_data(self, data_url=None, state_code_url=None, state_code_table_index=None):
        """
        Returns a tidy DataFrame of United States state-level Covid-19 data based on daily files from the New York
        Times' GitHub and state codes from the NRCS website.

        Args:
            data_url (str): URL to New York Times' GitHub of United States state-level Covid-19 data.
            state_code_url (str): URL to NRCS' page of United States state codes.
            state_code_table_index (int): Index of the table within the NRCS' webpage's HTML elements.

        Returns:
            pd.DataFrame
        """
        LOGGER.info("Generating USA state-level data")
        # Check if file exits
        file_name = "{:%Y%m%d}_usa_state_level_dataset.csv".format(self.as_at_date)
        file_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        file_path = os.path.join(file_folder, file_name)
        if os.path.isfile(file_path):
            LOGGER.info("Reading from file")
            df = pd.read_csv(file_path)
            LOGGER.info("USA state-level dataset ready")
            return df

        LOGGER.info("Day file not found, generating from scratch")
        # Defaults
        if data_url is None:
            data_url = self.usa_state_data_url

        if state_code_url is None:
            state_code_url = self.usa_state_codes_url

        if state_code_table_index is None:
            state_code_table_index = 0

        # Read NYT data & pad FIPS
        LOGGER.info("Reading data")
        df = pd.read_csv(data_url)
        df["fips"] = df["fips"].astype(int).astype(str).str.zfill(2)
        df.rename(columns={"cases": "cum_cases", "deaths": "cum_deaths"}, inplace=True)

        # Make tidy
        LOGGER.info("Adding missing dates")
        all_dates = pd.date_range(df["date"].min(), df["date"].max()).astype(str).tolist()
        frames = []
        for state in df["state"].unique():
            df_state = df[df["state"] == state].copy()
            dates_to_add = list(set(all_dates).difference(set(df_state["date"])))
            df_to_add = pd.DataFrame({"date": dates_to_add})
            df_to_add["state"] = state
            df_to_add["fips"] = df_state["fips"].iloc[0]
            # Aggregate
            df_state_new = pd.concat([df_state, df_to_add])
            df_state_new.sort_values(by="date", inplace=True)
            for col in ["cases", "deaths"]:
                df_state_new[f"cum_{col}"].fillna(method="ffill", inplace=True)
                df_state_new[f"cum_{col}"].fillna(0, inplace=True)
                df_state_new[col] = df_state_new[f"cum_{col}"].diff().fillna(0)
            frames.append(df_state_new)

        # State alpha codes
        LOGGER.info("Adding state alpha codes")
        df_state_codes = pd.read_html(state_code_url)[state_code_table_index][:-1].copy()
        df_state_codes.columns = [c.strip().lower().replace(" ", "_") for c in df_state_codes.columns]
        df_state_codes.rename(columns={"postal_code": "alpha_code"}, inplace=True)
        df_state_codes["fips"] = df_state_codes["fips"].astype(int).astype(str).str.zfill(2)

        # Add missing states
        LOGGER.info("Adding missing states")
        missing_fips = set(df_state_codes["fips"]).difference(set(df["fips"]))
        if len(missing_fips):
            for fips in missing_fips:
                df_state = pd.DataFrame({"date": all_dates})
                df_state["state"] = df_state_codes[df_state_codes["fips"] == fips]["name"].iloc[0]
                df_state["fips"] = fips
                for col in ["cum_cases", "cum_deaths", "cases", "deaths"]:
                    df_state[col] = 0
                frames.append(df_state)

        LOGGER.info("Concatenating tidy dataframes")
        df = pd.concat(frames, ignore_index=True)
        df.sort_values(by=["state", "date"], inplace=True)

        # Merge
        LOGGER.info("Merging data")
        df = df.merge(df_state_codes[["fips", "alpha_code"]], how="left", left_on="fips", right_on="fips")

        # Export & clean
        LOGGER.info("Exporting USA state-level data")
        self._export_and_clean(df, file_folder, file_name)
        LOGGER.info("USA state-level dataset ready")

        return df

    def generate_usa_county_data(self, url=None):
        """
        Returns a tidy DataFrame of United States county-level Covid-19 data based on daily files from the New York
        Times' GitHub.

        Args:
            url (str): URL to New York Times' GitHub of United States county-level Covid-19 data.

        Returns:
            pd.DataFrame
        """
        LOGGER.info("Generating USA county-level dataset")
        # Check if file exits
        file_name = "{:%Y%m%d}_usa_county_level_dataset.csv".format(self.as_at_date)
        file_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        file_path = os.path.join(file_folder, file_name)
        if os.path.isfile(file_path):
            LOGGER.info("Reading from file")
            df = pd.read_csv(file_path)
            LOGGER.info("USA county-level dataset ready")
            return df

        LOGGER.info("Day file not found, generating from scratch")
        # Defaults
        if url is None:
            url = self.usa_county_data_url

        # Read data, fill in missing FIPS and remove cases from unknown counties
        LOGGER.info("Reading data")
        df = pd.read_csv(url)
        df.loc[df["county"] == "New York City", "fips"] = 36061  # NYC mapped to Manhattan
        df.loc[df["county"] == "Kansas City", "fips"] = 20085    # FIPS for most of Kansas City
        df = df[df["county"] != "Unknown"].copy()
        df["fips"] = df["fips"].astype(int).astype(str).str.zfill(5)
        df.rename(columns={"cases": "cum_cases", "deaths": "cum_deaths"}, inplace=True)

        # Make tidy
        LOGGER.info("Adding missing dates")
        all_dates = pd.date_range(df["date"].min(), df["date"].max()).astype(str).tolist()
        frames = []
        for fips in df["fips"].unique():
            df_county = df[df["fips"] == fips].copy()
            dates_to_add = list(set(all_dates).difference(set(df_county["date"])))
            df_to_add = pd.DataFrame({"date": dates_to_add})
            df_to_add["county"] = df_county["county"].iloc[0]
            df_to_add["state"] = df_county["state"].iloc[0]
            df_to_add["fips"] = fips
            # Aggregate
            df_county_new = pd.concat([df_county, df_to_add])
            df_county_new.sort_values(by="date", inplace=True)
            for col in ["cases", "deaths"]:
                df_county_new[f"cum_{col}"].fillna(method="ffill", inplace=True)
                df_county_new[f"cum_{col}"].fillna(0, inplace=True)
                df_county_new[col] = df_county_new[f"cum_{col}"].diff().fillna(0)
            frames.append(df_county_new)

        LOGGER.info("Concatenating tidy dataframes")
        df = pd.concat(frames, ignore_index=True)
        df.sort_values(by=["county", "date"], inplace=True)

        # Export & clean
        LOGGER.info("Exporting USA county-level data")
        self._export_and_clean(df, file_folder, file_name)
        LOGGER.info("USA county-level data ready")

        return df

    @staticmethod
    def _export_and_clean(df, file_folder, file_name):
        # Create folder/s if doesn't exist
        if not os.path.exists(file_folder):
            os.makedirs(file_folder)
        # Export file
        df.to_csv(os.path.join(file_folder, file_name), index=False)
        # Clean up old files
        old_files = [os.path.join(file_folder, f) for f in os.listdir(file_folder) if file_name.split("_", 1)[-1] in f
                     and f != file_name]
        for old_file in old_files:
            os.remove(old_file)
