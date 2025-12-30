import dash
from dash import dcc, html, callback, Input, Output
import plotly.express as px

from data_fetch import get_stations_df  # usa cache + fallback

dash.register_page(__name__, path='/', name='Map', title='Home')

layout = html.Div([
    html.Div(
        "Note: This map does not yet include the complete list of gas stations.",
        style={
            'backgroundColor': '#ffcccb',
            'color': '#800000',
            'padding': '10px',
            'marginBottom': '10px',
            'borderRadius': '5px',
            'fontWeight': 'bold',
            'textAlign': 'center'
        }
    ),

    html.Div(id="api-error", style={"color": "#800000", "marginBottom": "10px"}),

    dcc.Dropdown(
        id='address-dropdown',
        options=[],
        placeholder="Select an Address",
        style={'marginBottom': '15px'}
    ),

    dcc.Graph(id='gas-stations-map'),

    dcc.Interval(id='interval-component', interval=180*1000, n_intervals=0),
])

@callback(
    Output("address-dropdown", "options"),
    Output("api-error", "children"),
    Input("interval-component", "n_intervals"),
)
def refresh_dropdown(_):
    df, err = get_stations_df()
    opts = [{"label": a, "value": a} for a in df.get("Address", []).dropna().unique()] if not df.empty else []
    return opts, (err or "")

@callback(
    Output('gas-stations-map', 'figure'),
    [Input('interval-component', 'n_intervals'),
     Input('address-dropdown', 'value')]
)
def update_map(_, selected_address):
    df, err = get_stations_df()

    if df.empty:
        # figura vazia, mas app continua vivo
        fig = px.scatter_mapbox(lat=[], lon=[], zoom=2, height=600)
        fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
        return fig

    if selected_address:
        selected_row = df[df['Address'] == selected_address]
        if selected_row.empty:
            selected_address = None
        else:
            selected_lat = selected_row['Latitude'].iloc[0]
            selected_lon = selected_row['Longitude'].iloc[0]

            fig = px.scatter_mapbox(df, lat='Latitude', lon='Longitude',
                                    hover_name='Municipality',
                                    hover_data=['Station', 'Address'],
                                    zoom=12, height=600)
            fig.update_layout(mapbox_style="open-street-map",
                              mapbox_center={"lat": selected_lat, "lon": selected_lon},
                              margin={"r":0,"t":0,"l":0,"b":0})
            return fig

    fig = px.scatter_mapbox(df, lat='Latitude', lon='Longitude',
                            hover_name='Municipality',
                            hover_data=['Station', 'Address'],
                            zoom=5, height=600)
    fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
    return fig
