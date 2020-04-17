import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio


class CovidChartGenerator:
    def __init__(self, df=None, plotly_template=None, plotly_renderer=None, dash=False):
        self.df = df
        self.metrics = {"cases": "new cases", "deaths": "new deaths", "cum_cases": "cumulative cases",
                        "cum_deaths": "cumulative deaths", "mortality_rate": "mortality rate",
                        "fraction_infected": r"% of pop. infected", "fraction_deaths": r"% of pop. dead",
                        "infections_growth_rate": "infections growth rate", "deaths_growth_rate": "deaths growth rate"}
        self.scopes = ["world", "europe", "asia", "africa", "north america", "south america"]
        self.templates = ["ggplot2", "seaborn", "simple_white", "plotly", "plotly_white", "plotly_dark", "presentation",
                          "xgridoff", "ygridoff", "gridon", "none"]
        self.renderers = ["plotly_mimetype", "jupyterlab", "nteract", "vscode", "notebook", "notebook_connected",
                          "kaggle", "azure", "colab", "cocalc", "databricks", "json", "png", "jpeg", "jpg", "svg",
                          "pdf", "browser", "firefox", "chrome", "chromium", "iframe", "iframe_connected",
                          "sphinx_gallery"]

        if plotly_template is None or plotly_template.lower() not in self.templates:
            self.template = "plotly_dark"
        else:
            self.template = plotly_template.lower()

        if plotly_renderer is None or plotly_renderer.lower() not in self.renderers:
            pio.renderers.default = "iframe"
        else:
            pio.renderers.default = plotly_renderer.lower()

        self.dash = dash

    def _scale_upper_limit(self, x):
        sign = np.sign(x)
        x = abs(x)
        if x == 0:
            return 0
        elif x >= 1:
            power = int(math.log10(x))
            scale = math.pow(10, power)
            lower = math.floor(x / scale) * scale
            for step in [1.25, 1.5, 1.75, 2]:
                if x < lower * step:
                    return lower * step * sign
        else:
            factor = 1
            while x < 1:
                factor *= 10
                x *= 10
            return self._scale_upper_limit(x * sign) / factor

    def _scale_lower_limit(self, x):
        sign = np.sign(x)
        x = abs(x)
        if x == 0:
            return 0
        elif x >= 1:
            power = int(math.log10(x))
            scale = math.pow(10, power)
            lower = math.floor(x / scale) * scale
            for step in [1.75, 1.5, 1.25, 1]:
                if x >= lower * step:
                    return lower * step * sign
        else:
            factor = 1
            while x < 1:
                factor *= 10
                x *= 10
            return self._scale_lower_limit(x * sign) / factor

    def _generate_scale(self, values):
        if all(x < 0 for x in values):
            return self._scale_upper_limit(min(values)), self._scale_lower_limit(max(values))
        else:
            return self._scale_lower_limit(min(values)), self._scale_upper_limit(max(values))

    def generate_animated_map(self, df=None, scope="world", metric="cum_cases", chart_type="choropleth", fit_dates=True,
                              plotly_template=None):
        """
        Generates an animated map from ECDC Covid-19 country-level data.
        
        Args:
            df (pd.DataFrame): data to be visualized.
            scope (str): geographical scope of the map. Can be one of 'world', 'europe', 'asia', 'africa',
            'north america', 'south america'. Defaults to 'world'.
            metric (str): metric to plot. Can be one of 'cases', 'deaths', 'cum_cases', 'cum_deaths', 'mortality_rate',
            'fraction_infected', 'fraction_deaths', 'infections_growth_rate', 'deaths_growth_rate'. Defaults to
            'cum_cases'.
            chart_type (str): type of map. Can be one of 'choropleth' or 'scatter_geo'.
            fit_dates (bool): drop dates before data starts being non-zero for selected criteria.
            plotly_template (str): Plotly layout template to apply to generated figure. All accepted values accessible
            via self.templates.
            
        Returns:
            None
        """
        # Args check
        if scope.lower() not in self.scopes:
            print("Selected scope not supported ({}). \nPlease select from: {}.".format(scope, ", ".join(self.scopes)))
            return

        if metric.lower() not in self.metrics.keys():
            print("Selected metric not supported ({}). \nPlease select from: {}.".format(metric, ", ".join(
                self.metrics.keys())))
            return

        if df is None:
            df = self.df.copy()

        # DataFrame filtering
        if scope.lower() != "world":
            df = df[df["continent"] == scope.title()].copy()

        if fit_dates:
            min_date = df.loc[df[metric] > 0, "date_rep"].min()
            df = df[df["date_rep"] >= min_date].copy()

        # Generate figure
        if chart_type == "choropleth":
            fig = px.choropleth(df, locations="alpha_3_code", color=metric, hover_name="country",
                                hover_data=["date_rep", metric], range_color=[0, df[metric].max()],
                                color_continuous_scale=px.colors.sequential.Reds, scope=scope,
                                animation_frame="date_rep")
            fig.update_layout(
                coloraxis_colorbar=dict(title=self.metrics[metric].capitalize(), yanchor="middle", y=0.5, ticks="outside"))
        elif chart_type == "scatter_geo":
            fig = px.scatter_geo(df, locations="alpha_3_code", hover_name="country", size=metric, size_max=60,
                                 color_discrete_sequence=[px.colors.sequential.Reds[-2]], scope=scope,
                                 animation_frame="date_rep")
        else:
            print("Selected chart type not supported ({}). \nPlease select from: choropleth, scatter_geo.".format(
                chart_type))
            return

        # Format figure
        fig.update_geos(showcountries=True, countrycolor="white", coastlinecolor="white", landcolor="grey")
        fig.update_layout(margin=dict(r=0, t=50, l=0, b=0),
                          title_text="<b>Covid-19 {} by country</b>".format(self.metrics[metric]), title_y=.99,
                          title_yanchor="top", title_x=0.5, title_xanchor="center")
        if plotly_template is None or plotly_template.lower() not in self.templates:
            fig.layout.template = self.template
        else:
            fig.layout.template = plotly_template

        if self.dash:
            return fig
        else:
            pio.show(fig)

    def generate_animated_bar_chart(self, df=None, scope="world", x="cum_cases", y="default", x_cutoff=None, top_n=None,
                                    fit_dates=True, plotly_template=None):
        """
        Generates an animated bar chart from ECDC Covid-19 country-level data.
    
        Args:
            df (pd.DataFrame): ECDC data to be visualized.
            scope (str): geographical scope of the data. Can be one of 'world', 'europe', 'asia', 'africa',
            'north america', 'south america'. Defaults to 'world'.
            x (str): metric to plot. Can be one of 'cases', 'deaths', 'cum_cases', 'cum_deaths', 'mortality_rate', '
            fraction_infected', 'fraction_deaths', 'infections_growth_rate', 'deaths_growth_rate'. Defaults to
            'cum_cases'.
            y (str): unit to group data. If scope is 'world', defaults to 'continent', otherwise defaults to 'country'.
            x_cutoff (int): will not represent y groups that fall strictly below x_cutoff value. If x is cumulative,
            cutoff value applies to the last value by date. If not, cutoff value applies to the maximum within the date
            range.
            top_n (int): only display top N y groups. Operates like x_cutoff.
            fit_dates (bool): drop dates before data starts being non-zero for selected criteria.
            plotly_template (str): Plotly layout template to apply to generated figure. All accepted values accessible
            via self.templates.
            
        Returns:
            None
        """
        # Args check
        if scope.lower() not in self.scopes:
            print("Selected scope not supported ({}). \nPlease select from: {}.".format(scope, ", ".join(self.scopes)))
            return

        if x.lower() not in self.metrics:
            print("Selected x not supported ({}). \nPlease select from: {}.".format(x, ", ".join(self.metrics.keys())))
            return

        if y.lower() not in list(self.metrics.keys()) + ["default"]:
            print("Selected y not supported ({}). \nPlease select from: {}.".format(y, ", ".join(
                list(self.metrics.keys()) + ["default"])))
            return

        if df is None:
            df = self.df.copy()

        # DataFrame filtering
        if scope.lower() != "world":
            df = df[df["continent"] == scope.title()].copy()

        if y == "default":
            if scope.lower() == "world":
                y = "continent"
            else:
                y = "country"

        # Metric cutoff/top n aggregates
        if "cum" in x:
            df_check = (df.loc[df["date_rep"] == df["date_rep"].max(), [y, x]].groupby(y).sum())
        else:
            df_check = df[[y, x]].groupby(y).agg(max)

        if x_cutoff is not None:
            y_to_remove = df_check.loc[df_check[x] < x_cutoff].index
            df = df[~df[y].isin(y_to_remove)].copy()

        if top_n is not None:
            if len(df_check.index) > top_n:
                y_to_keep = df_check.nlargest(top_n, x).index
                df = df[df[y].isin(y_to_keep)].copy()

        # Fit dates
        if fit_dates:
            min_date = df.loc[df[x] > 0, "date_rep"].min()
            df = df[df["date_rep"] >= min_date].copy()

        # Format
        max_val = df_check.max()[x]
        graph_scale = [0, self._scale_upper_limit(max_val)]

        # Generate figure
        fig = px.bar(df, x=x, y=y, color=y, orientation="h", hover_name=y, hover_data=["date_rep", "country", y, x],
                     animation_frame="date_rep", range_x=graph_scale, labels=dict(x="", y=""),
                     color_discrete_sequence=px.colors.cyclical.Twilight)
        fig.update_layout(title_text="<b>Covid-19 {} by {}</b>".format(self.metrics[x], y), title_y=0.99,
                          title_yanchor="top", title_x=0.5, title_xanchor="center")
        if plotly_template is None or plotly_template.lower() not in self.templates:
            fig.layout.template = self.template
        else:
            fig.layout.template = plotly_template

        if self.dash:
            return fig
        else:
            pio.show(fig)

    def generate_animated_scatter_plot(self, df=None, x="cum_cases", y="mortality_rate", size="population_2018",
                                       facet_col=None, facet_row=None, plotly_template=None):
        """
        Generates an animated scatter plot from ECDC Covid-19 country-level data.
    
        Args:
            df (pd.DataFrame): ECDC data to be visualized.
            x (str): metric to plot along the x axis. Can be one of 'cases', 'deaths', 'cum_cases', 'cum_deaths',
            'mortality_rate', 'fraction_infected', 'fraction_deaths', 'infections_growth_rate', 'deaths_growth_rate'.
            Defaults to 'cum_cases'.
            y (str): metric to plot along the y axis. Values as per x. Defaults to 'mortality_rate'.
            size (str): metric used to size dots in the plot. Values as per x. Defaults to 'population_2018'.
            facet_col (str): field use to separate into subplots. Set to None for one chart. Defaults to None.
            facet_row (str): same as facet_col but in row form. Defaults to None.
            plotly_template (str): Plotly layout template to apply to generated figure. All accepted values accessible
            via self.templates.

        Returns:
            None
        """
        # Args check
        if x.lower() not in self.metrics:
            print("Selected x not supported ({}). \nPlease select from: {}.".format(x, ", ".join(self.metrics.keys())))
            return

        if y.lower() not in self.metrics:
            print("Selected y not supported ({}). \nPlease select from: {}.".format(y, ", ".join(self.metrics.keys())))
            return

        if size.lower() not in list(self.metrics.keys()) + ["population_2018"]:
            print("Selected size metric not supported ({}). \nPlease select from: {}.".format(size, ", ".join(
                list(self.metrics.keys()) + ["population_2018"])))
            return

        if df is None:
            df = self.df.copy()

        # Filter out nulls in size columns
        if df[size].isnull().sum() > 0:
            df = df[df[size].notnull()].copy()

        # Generate scales
        x_upper, y_upper = (self._scale_upper_limit(df[x].max()), self._scale_upper_limit(df[y].max()))
        x_scale = [0 - 0.1 * x_upper, x_upper]
        y_scale = [0 - 0.1 * y_upper, y_upper]

        # Generate figure
        fig = px.scatter(df, x=x, y=y, range_x=x_scale, range_y=y_scale, size=size, facet_col=facet_col,
                         facet_row=facet_row, hover_name="country", hover_data=["continent", x, y], size_max=60,
                         animation_frame="date_rep", animation_group="alpha_3_code",
                         labels=dict(x=self.metrics[x].capitalize(), y=self.metrics[y].capitalize()), color="continent",
                         color_discrete_sequence=px.colors.cyclical.Twilight)
        fig.update_layout(title_text="<b>Covid-19 {} vs {} by continent & country".format(self.metrics[x],
                                                                                          self.metrics[y]),
                          title_y=0.99, title_yanchor="top", title_x=0.5, title_xanchor="center")
        if plotly_template is None or plotly_template.lower() not in self.templates:
            fig.layout.template = self.template
        else:
            fig.layout.template = plotly_template

        if self.dash:
            return fig
        else:
            pio.show(fig)
