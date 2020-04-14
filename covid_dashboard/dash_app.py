import io

import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import flask

from covid_data_handler import CovidDataHandler
from covid_chart_generator import CovidChartGenerator

external_stylesheets = ['https://codepen.io/dadamson/pen/vPVxxq.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

cdh = CovidDataHandler()
cdh.generate_country_level_dataset()
ccg = CovidChartGenerator(df=cdh.covid_country_data, plotly_template="ggplot2", dash=True)

app.layout = html.Div([
    html.H1("Covid-19 ECDC data dashboard", style={"text-align": "center", "margin-bottom": "4rem"}),

    dcc.Tabs([
        dcc.Tab(label="Map", children=[
            html.Div([
                html.Div([
                    html.Label("Focus"),
                    dcc.Dropdown(
                        id="map-scope",
                        options=[{"label": scope.title(), "value": scope} for scope in ccg.scopes],
                        value="world",
                        clearable=False
                    )
                ], style={"width": "30%"}),
                html.Div([
                    html.Label("Metric"),
                    dcc.Dropdown(
                        id="map-metric",
                        options=[{"label": ccg.metrics[k].capitalize(), "value": k} for k in ccg.metrics],
                        value="cum_cases",
                        clearable=False,
                    )
                ], style={"width": "30%"}),
                html.Div([
                    html.Label("Map type"),
                    dcc.Dropdown(
                        id="map-type",
                        options=[{"label": "Heatmap", "value": "choropleth"}, {"label": "Scatter map", "value": "scatter_geo"}],
                        value="choropleth",
                        clearable=False
                    )
                ], style={"width":"30%"})
            ],
            style={"width": "30%", "margin": "auto", "margin-top": "3rem", "margin-bottom": "1rem", "display": "flex",
                   "justify-content": "space-between"}),
            html.Div([
                dcc.Graph(id="covid-map")
            ], style={"display": "flex", "align-items": "center", "justify-content": "center"})
        ]),

        dcc.Tab(label="Bar chart", children=[
            html.Div([
                html.Div([
                    html.Label("Focus"),
                    dcc.Dropdown(
                        id="bar-scope",
                        options=[{"label": scope.title(), "value": scope} for scope in ccg.scopes],
                        value="world",
                        clearable=False
                    )
                ], style={"width": "22%"}),
                html.Div([
                    html.Label("Metric"),
                    dcc.Dropdown(
                        id="bar-metric",
                        options=[{"label": ccg.metrics[k].capitalize(), "value": k} for k in ccg.metrics],
                        value="cum_cases",
                        clearable=False
                    )
                ], style={"width": "22%"}),
                html.Div([
                    html.Label("Cutoff"),
                    dcc.Input(
                        id="bar-cutoff",
                        type="number",
                        value=0
                    )
                ], style={"width": "22%"}),
                html.Div([
                    html.Label("Top N"),
                    dcc.Input(
                        id="bar-top-n",
                        type="number",
                        value=10
                    )
                ], style={"width": "22%"})
            ],
            style={"width": "40%", "margin": "auto", "margin-top": "3rem", "margin-bottom": "1rem", "display": "flex",
                   "justify-content": "space-between"}),
            html.Div([
                dcc.Graph(id="covid-bar")
            ], style={"display": "flex", "align-items": "center", "justify-content": "center"})
        ]),

        dcc.Tab(label="Scatter plot", children=[
            html.Div([
                html.Div([
                    html.Label("X"),
                    dcc.Dropdown(
                        id="scatter-x",
                        options=[{"label": ccg.metrics[k].capitalize(), "value": k} for k in ccg.metrics],
                        value="cum_cases",
                        clearable=False
                    )
                ], style={"width": "30%"}),
                html.Div([
                    html.Label("Y"),
                    dcc.Dropdown(
                        id="scatter-y",
                        options=[{"label": ccg.metrics[k].capitalize(), "value": k} for k in ccg.metrics],
                        value="mortality_rate",
                        clearable=False
                    )
                ], style={"width": "30%"}),
                html.Div([
                    html.Label("Marker size metric"),
                    dcc.Dropdown(
                        id="scatter-size",
                        options=[{"label": ccg.metrics[k].capitalize(), "value": k} for k in ccg.metrics] +
                                [{"label": "2018 population", "value": "population_2018"}],
                        value="population_2018",
                        clearable=False
                    )
                ], style={"width": "30%"})
            ],
            style={"width": "30%", "margin": "auto", "margin-top": "3rem", "margin-bottom": "1rem", "display": "flex",
                   "justify-content": "space-between"}),
            html.Div([
                dcc.Graph(id="covid-scatter")
                ], style={"display": "flex", "align-items": "center", "justify-content": "center"})
        ]),

        dcc.Tab(label="Data", children=[
            html.Div([
                html.A("Download CSV", id="download-data", href="/download_csv/")
            ], style={"display": "flex", "align-items": "flex-start", "width": "78%", "margin": "auto",
                      "margin-top": "3rem", "margin-bottom": "1rem"}),
            html.Div([
                dash_table.DataTable(
                    id="data-table",
                    columns=[{"name": col, "id": col} for col in cdh.covid_country_data.columns],
                    data=cdh.covid_country_data.to_dict("records"),
                    page_size=500,
                    style_table={"overflowX": "scroll", "overflowY": "scroll", "height": "4000px",
                                 "width": "2000px"},
                    style_data_conditional=[{"if": {"row_index": "odd"},
                                             "backgroundColor": "rgb(248, 248, 248"}],
                    style_header={"backgroundColor": "rgb(230, 230, 230", "fontWeight": "bold"},
                    style_cell={"min_width": "100px"},
                    fixed_rows={"headers": True, "data": 0}
                )
            ], style={"display": "flex", "align-items": "center", "justify-content": "center"})
        ])
    ], style={"width": "80%", "display": "flex", "align-items": "center", "justify-content": "center",
              "margin": "auto"})
])

@app.callback(
    Output("covid-map", "figure"),
    [Input("map-scope", "value"),
     Input("map-metric", "value"),
     Input("map-type", "value")]
)
def update_map(scope, metric, type):
    return ccg.generate_animated_map(scope=scope, metric=metric, chart_type=type)

@app.callback(
    Output("covid-bar", "figure"),
    [Input("bar-scope", "value"),
     Input("bar-metric", "value"),
     Input("bar-cutoff", "value"),
     Input("bar-top-n", "value")]
)
def update_bar(scope, metric, cutoff, top_n):
    return ccg.generate_animated_bar_chart(scope=scope, x=metric, x_cutoff=cutoff, top_n=top_n)

@app.callback(
    Output("covid-scatter", "figure"),
    [Input("scatter-x", "value"),
     Input("scatter-y", "value"),
     Input("scatter-size", "value")]
)
def update_scatter(x, y, size):
    return ccg.generate_animated_scatter_plot(x=x, y=y, size=size)

@app.server.route("/download_csv/")
def download_csv():
    strIO = io.StringIO()
    cdh.covid_country_data.to_csv(strIO)
    mem = io.BytesIO()
    mem.write(strIO.getvalue().encode("utf-8"))
    mem.seek(0)
    strIO.close()
    return flask.send_file(mem, mimetype="text/csv", attachment_filename="covid19_ecdc_country_data.csv",
                           as_attachment=True)

if __name__ == "__main__":
    app.run_server(8888, debug=True)
