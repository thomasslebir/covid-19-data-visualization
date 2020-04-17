import io

import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import flask

from covid_dashboard.utils.data_handler import CovidDataHandler
from covid_dashboard.utils.chart_generator import CovidChartGenerator

external_stylesheets = ['https://codepen.io/dadamson/pen/vPVxxq.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

cdh = CovidDataHandler()
cdh.generate_country_level_dataset()
ccg = CovidChartGenerator(df=cdh.covid_country_data, plotly_template="ggplot2", dash=True)

app.layout = html.Div([
    html.H1("Covid-19 ECDC data dashboard", style={"text-align": "center", "margin-bottom": "4rem"}),

    dcc.Tabs(
        style = {"width": "80vw", "display": "flex", "align-items": "center", "justify-content": "center",
                 "margin": "auto"},
        children=[
        dcc.Tab(label="Map", children=[
            html.Div(
                style={"width": "50vw", "margin": "auto", "margin-top": "3rem", "margin-bottom": "1rem",
                       "display": "flex", "justify-content": "space-between", "position": "relative"},
                children=[
                    html.Div([
                        html.Label("Focus"),
                        dcc.Dropdown(
                            id="map-scope",
                            options=[{"label": scope.title(), "value": scope} for scope in ccg.scopes],
                            value="world",
                            clearable=False
                        )
                    ], style={"width": "22%"}),
                    html.Div([
                        html.Label("Metric"),
                        dcc.Dropdown(
                            id="map-metric",
                            options=[{"label": ccg.metrics[k].capitalize(), "value": k} for k in ccg.metrics],
                            value="cum_cases",
                            clearable=False,
                        )
                    ], style={"width": "22%"}),
                    html.Div([
                        html.Label("Map type"),
                        dcc.Dropdown(
                            id="map-type",
                            options=[{"label": "Heatmap", "value": "choropleth"}, {"label": "Scatter map",
                                                                                   "value": "scatter_geo"}],
                            value="choropleth",
                            clearable=False
                        )
                    ], style={"width": "22%"}),
                    html.Div([
                        html.Button("Refresh",
                                    id="map-refresh",
                                    n_clicks=0,
                                    className="control-refresh",
                                    style={"height": "60%", "width": "22%", "position": "absolute", "bottom": 0}),
                    ], style={"width": "22%"})
            ],
        ),
            html.Div(
                id="covid-map-div",
                style={"display": "flex", "align-items": "center", "justify-content": "center", "height": "70vh",
                       "width": "70vw", "margin": "auto"},
                children = [
                    dcc.Loading(
                        id="covid-map-loader",
                        type="graph",
                        children=[]
                    )
                ]
            )
        ]),

        dcc.Tab(label="Bar chart", children=[
            html.Div(
                style={"width": "50vw", "margin": "auto", "margin-top": "3rem", "margin-bottom": "1rem",
                       "display": "flex", "justify-content": "space-between", "position": "relative"},
                children=[
                    html.Div([
                        html.Label("Focus"),
                        dcc.Dropdown(
                            id="bar-scope",
                            options=[{"label": scope.title(), "value": scope} for scope in ccg.scopes],
                            value="world",
                            clearable=False
                        )
                    ], style={"width": "18%"}),
                    html.Div([
                        html.Label("Metric"),
                        dcc.Dropdown(
                            id="bar-metric",
                            options=[{"label": ccg.metrics[k].capitalize(), "value": k} for k in ccg.metrics],
                            value="cum_cases",
                            clearable=False
                        )
                    ], style={"width": "18%"}),
                    html.Div([
                        html.Label("Cutoff"),
                        dcc.Input(
                            id="bar-cutoff",
                            type="number",
                            value=0
                        )
                    ], style={"width": "18%"}),
                    html.Div([
                        html.Label("Top N"),
                        dcc.Input(
                            id="bar-top-n",
                            type="number",
                            value=10
                        )
                    ], style={"width": "18%"}),
                    html.Div([
                        html.Button("Refresh",
                                    id="bar-refresh",
                                    n_clicks=0,
                                    className="control-refresh",
                                    style={"height": "60%", "width": "18%", "position": "absolute", "bottom": 0,
                                           "hover": {"color": "#FFBF00", "border-color": "#FFBF00"}}),
                    ], style={"width": "18%"})
                ],
            ),
            html.Div(
                id="covid-bar-div",
                style={"display": "flex", "align-items": "center", "justify-content": "center", "height": "70vh",
                       "width": "70vw", "margin": "auto"},
                children=[
                    dcc.Loading(
                        id="covid-bar-loader",
                        type="graph",
                        children=[]
                    )
                ]
            )
        ]),

        dcc.Tab(label="Scatter plot", children=[
            html.Div(
                style={"width": "50vw", "margin": "auto", "margin-top": "3rem", "margin-bottom": "1rem",
                       "display": "flex", "justify-content": "space-between", "position": "relative"},
                children=[
                    html.Div([
                            html.Label("X"),
                            dcc.Dropdown(
                                id="scatter-x",
                                options=[{"label": ccg.metrics[k].capitalize(), "value": k} for k in ccg.metrics],
                                value="cum_cases",
                                clearable=False
                            )
                        ], style={"width": "18%"}),
                        html.Div([
                            html.Label("Y"),
                            dcc.Dropdown(
                                id="scatter-y",
                                options=[{"label": ccg.metrics[k].capitalize(), "value": k} for k in ccg.metrics],
                                value="mortality_rate",
                                clearable=False
                            )
                        ], style={"width": "18%"}),
                        html.Div([
                            html.Label("Marker size metric"),
                            dcc.Dropdown(
                                id="scatter-size",
                                options=[{"label": ccg.metrics[k].capitalize(), "value": k} for k in ccg.metrics] +
                                        [{"label": "2018 population", "value": "population_2018"}],
                                value="population_2018",
                                clearable=False
                            )
                        ], style={"width": "18%"}),
                        html.Div([
                            html.Label("Separate continents"),
                            dcc.Dropdown(
                                id="scatter-facet",
                                options=[{"label": "None", "value": "None"},
                                         {"label": "Columns", "value": "facet_col"},
                                         {"label": "Rows", "value": "facet_row"}],
                                value="None",
                                clearable=False
                            )
                        ], style={"width": "18%"}),
                        html.Div([
                            html.Button("Refresh",
                                        id="scatter-refresh",
                                        n_clicks=0,
                                        className="control-refresh",
                                        style={"height": "60%", "width": "18%", "position": "absolute", "bottom": 0}),
                        ], style={"width": "18%"})
                    ],
            ),
            html.Div(
                id="covid-scatter-div",
                style={"display": "flex", "align-items": "center", "justify-content": "center", "height": "70vh",
                       "width": "85vw", "margin": "auto"},
                children=[
                    dcc.Loading(
                        id="covid-scatter-loader",
                        type="graph",
                        children=[]
                    )
                ]
            )
        ]),

        dcc.Tab(id="data-tab", label="Data", children=[
            html.Div(
                style={"display": "flex", "align-items": "flex-start", "justify-content": "flex-start",
                       "width": "70vw", "height": "3vh", "margin": "auto", "margin-top": "3rem",
                       "margin-bottom": "1rem"},
                children=[
                    html.A(id="download-data",
                           href="/download_csv/",
                           children=[
                                html.Button("Download CSV",
                                            id="download-data-button",
                                            n_clicks=0,
                                            className="control-refresh"
                                )
                           ]
                    ),
                    html.Button(
                        children="Display data",
                        id="display-data",
                        n_clicks=0,
                        className="control-refresh",
                        style={"margin-left": "1vw"}
                    )
                ]
            ),
            html.Div(
                id="covid-data-div",
                style={"display": "none", "align-items": "flex-start", "justify-content": "center", "height": "70vh",
                       "width": "70vw", "margin": "auto"},
                children=[
                    dcc.Loading(
                        id="data-table-loader",
                        children=[]
                    )
                ]
            )
        ])
    ]),
])


@app.callback(
    Output("covid-map-loader", "children"),
    [Input("map-refresh", "n_clicks")],
    [State("map-scope", "value"),
     State("map-metric", "value"),
     State("map-type", "value")]
)
def update_map(n_clicks, scope, metric, chart_type):
    fig = ccg.generate_animated_map(scope=scope, metric=metric, chart_type=chart_type)
    return dcc.Graph(id="covid-map-graph", figure=fig, style={"responsive": True, "margin-top": "2rem",
                                                              "width": "70vw", "height": "70vh"})


@app.callback(
    Output("covid-bar-loader", "children"),
    [Input("bar-refresh", "n_clicks")],
    [State("bar-scope", "value"),
     State("bar-metric", "value"),
     State("bar-cutoff", "value"),
     State("bar-top-n", "value")]
)
def update_bar(n_clicks, scope, metric, cutoff, top_n):
    fig = ccg.generate_animated_bar_chart(scope=scope, x=metric, x_cutoff=cutoff, top_n=top_n)
    return dcc.Graph(id="covid-bar-graph", figure=fig, style={"responsive": True, "margin-top": "2rem",
                                                              "width": "70vw", "height": "70vh"})


@app.callback(
    Output("covid-scatter-loader", "children"),
    [Input("scatter-refresh", "n_clicks")],
    [State("scatter-x", "value"),
     State("scatter-y", "value"),
     State("scatter-size", "value"),
     State("scatter-facet", "value")]
)
def update_scatter(n_clicks, x, y, size, facet):
    if facet == None:
        fig = ccg.generate_animated_scatter_plot(x=x, y=y, size=size)
    elif facet == "facet_col":
        fig = ccg.generate_animated_scatter_plot(x=x, y=y, size=size, facet_col="continent")
    else:
        fig = ccg.generate_animated_scatter_plot(x=x, y=y, size=size, facet_row="continent")

    return dcc.Graph(id="covid-scatter-graph", figure=fig, style={"responsive": True, "margin-top": "2rem",
                                                              "width": "85vw", "height": "70vh"})


@app.callback(
    [Output("data-table-loader", "children"),
     Output("covid-data-div", "style"),
     Output("display-data", "children")],
    [Input("display-data", "n_clicks")],
    [State("display-data", "children")]
)
def serve_table(n_clicks, curr_val):
    if curr_val == "Display data":
        dt = dash_table.DataTable(
                        id="data-table",
                        columns=[{"name": col, "id": col} for col in cdh.covid_country_data.columns],
                        data=cdh.covid_country_data.to_dict("records"),
                        page_size=500,
                        style_table={"overflowX": "scroll", "overflowY": "scroll", "height": "70vh",
                                     "width": "70vw"},
                        style_data_conditional=[{"if": {"row_index": "odd"},
                                                 "backgroundColor": "rgb(248, 248, 248"}],
                        style_header={"backgroundColor": "rgb(230, 230, 230", "fontWeight": "bold"},
                        style_cell={"min_width": "100px"},
                        fixed_rows={"headers": True, "data": 0}
        )
        div = html.Div([dt])
        style = {"display": "flex", "align-items": "flex-start", "justify-content": "center", "height": "70vh",
                 "width": "70vw", "margin": "auto"}
        button_text = ["Hide data"]
    else:
        div = html.Div(children=[])
        style = {"display": "none", "align-items": "flex-start", "justify-content": "center", "height": "70vh",
                 "width": "70vw", "margin": "auto"}
        button_text = ["Display data"]

    return div, style, button_text


@app.server.route("/download_csv/")
def download_csv():
    str_io = io.StringIO()
    cdh.covid_country_data.to_csv(str_io)
    mem = io.BytesIO()
    mem.write(str_io.getvalue().encode("utf-8"))
    mem.seek(0)
    str_io.close()
    return flask.send_file(mem, mimetype="text/csv", attachment_filename="covid19_ecdc_country_data.csv",
                           as_attachment=True)


if __name__ == "__main__":
    app.run_server(debug=True)
