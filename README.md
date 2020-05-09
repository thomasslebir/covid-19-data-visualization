# Covid-19 Data Visualization

In the notebooks provided in this repo, I'll explore both worldwide and US-centric datasets of the Covid-19 virus to try to visualize its spread. I'll use plotly and ipywidgets to create interactive maps and charts, voila to publish the results in an interactive, notebook-based dashboard, and dash to produce a full-fledged dashboard that can be hosted independently.

### Worldwide Data
Worldwide data is published daily on the [ECDC website](https://www.ecdc.europa.eu/en/geographical-distribution-2019-ncov-cases). I enriched the data for visualization purposes with Wikipedia's [ISO country codes](https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes) and Statistic Times' [breakdown of countries by region/continent](http://statisticstimes.com/geography/countries-by-continents.php)

### United States Data
United States  county and state-level data is updated daily on the [New York Times' github](https://github.com/nytimes/covid-19-data) (dashboard in progress).


## Notebooks

### Walkthrough
The ```world_data_walkthrough.ipynb``` is a step-by-step explanation of how to get started with plotly, first generating static maps and then adding animations, and how to work with ipywidgets to add useful interactivity to explore the data further. I also cover two other chart formats, namely bar charts and scatter plots.

### Dashboards
The ```world_data_voila_dashboard.ipynb``` and ```usa_data_voila_dashboard.ipynb``` both use final versions of charts in the walkthrough (with a few modifications on the United States to fit data). They both leverage utilities built in the walkthrough, packaged in ```scripts```. They are meant to be published as dashboards using ```voila```.

## Dashboard

* The full dashboard in the ```dashboard``` folder is generated with dash. It features all final versions of charts along with a logic to refresh data, visualize it and download it as a csv. I've also hosted it on [heroku](https://covid19-dash-app.herokuapp.com/).


## More Information on Covid-19

* [ECDC](https://www.ecdc.europa.eu/en/covid-19-pandemic)
* [CDC](https://www.cdc.gov/coronavirus/2019-ncov/index.html)
* [Google Covid-19 Information](https://www.google.com/covid19/)
