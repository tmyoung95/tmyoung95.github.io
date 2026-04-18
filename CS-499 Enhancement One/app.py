import sqlite3

import geopandas as gpd
import pandas as pd
from dash import Dash, dcc, html, dash_table, Input, Output, State, no_update
import dash_leaflet as dl
from shapely.geometry import Point
from shapely.ops import nearest_points

from auth import (
    initialize_database,
    has_completed_user,
    create_user_account,
    verify_first_time_mfa_setup,
    authenticate_user_login,
    build_mfa_qr_code_base64,
    list_users
)

POLICY_DATABASE_NAME = "policies.db"
COASTLINE_FILE = "coastline shape data/ne_10m_coastline.shp"

initialize_database()

def initialize_policy_database():
    connection = sqlite3.connect(POLICY_DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS policies (
            policy_number TEXT PRIMARY KEY,
            address TEXT,
            city TEXT,
            county TEXT,
            state TEXT,
            zip TEXT,
            lat REAL,
            lon REAL,
            premium REAL,
            product TEXT,
            phone TEXT,
            email TEXT,
            dwelling_coverage REAL,
            deductible REAL,
            policy_status TEXT
        )
        """
    )

    connection.commit()
    connection.close()

def get_policy_connection():
    return sqlite3.connect(POLICY_DATABASE_NAME)

def load_policy_data():
    connection = get_policy_connection()
    try:
        return pd.read_sql_query("SELECT * FROM policies ORDER BY policy_number ASC", connection)
    finally:
        connection.close()

def add_policy_record(policy_data):
    connection = get_policy_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO policies VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            policy_data["policy_number"],
            policy_data["address"],
            policy_data["city"],
            policy_data["county"],
            policy_data["state"],
            policy_data["zip"],
            policy_data["lat"],
            policy_data["lon"],
            policy_data["premium"],
            policy_data["product"],
            policy_data["phone"],
            policy_data["email"],
            policy_data["dwelling_coverage"],
            policy_data["deductible"],
            policy_data["policy_status"]
        )
    )

    connection.commit()
    connection.close()

initialize_policy_database()

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Insurance Exposure Dashboard"

coast = gpd.read_file(COASTLINE_FILE)
coast = coast.to_crs(epsg=4326)
coastline = coast.geometry.union_all()

BASE_POLICY_COLUMNS = [
    "policy_number","address","city","county","state","zip","lat","lon",
    "premium","product","phone","email","dwelling_coverage","deductible",
    "policy_status","coast_distance_miles","coast_zone","coast_lat","coast_lon"
]

def coast_distance_and_point(lat, lon):
    property_point = Point(lon, lat)
    nearest_geom = nearest_points(property_point, coastline)[1]
    distance = property_point.distance(nearest_geom) * 69
    return round(distance, 2), nearest_geom

def calculate_coast_metrics(dataframe):
    if dataframe.empty:
        for column_name in ["coast_distance_miles","coast_zone","coast_lat","coast_lon"]:
            dataframe[column_name] = []
        return dataframe

    working_dataframe = dataframe.copy()

    distances, zones, coast_latitudes, coast_longitudes = [], [], [], []

    for _, row in working_dataframe.iterrows():
        distance_miles, nearest_point = coast_distance_and_point(row["lat"], row["lon"])
        distances.append(distance_miles)
        coast_latitudes.append(nearest_point.y)
        coast_longitudes.append(nearest_point.x)

        if distance_miles <= 5:
            zones.append("Coastal")
        elif distance_miles <= 10:
            zones.append("Midland")
        else:
            zones.append("Inland")

    working_dataframe["coast_distance_miles"] = distances
    working_dataframe["coast_zone"] = zones
    working_dataframe["coast_lat"] = coast_latitudes
    working_dataframe["coast_lon"] = coast_longitudes

    return working_dataframe

def load_dashboard_data():
    try:
        return calculate_coast_metrics(load_policy_data())
    except:
        return pd.DataFrame(columns=BASE_POLICY_COLUMNS)

def build_login_layout(message=""):
    return html.Div([
        html.H2("Login"),
        dcc.Input(id="username", placeholder="Username"),
        dcc.Input(id="password", type="password", placeholder="Password"),
        dcc.Input(id="code", placeholder="MFA Code"),
        html.Button("Login", id="login"),
        html.Div(message)
    ])

def build_dashboard_layout():
    return html.Div([
        html.H3("Add Policy"),
        dcc.Input(id="policy_number"),
        dcc.Input(id="address"),
        dcc.Input(id="city"),
        dcc.Input(id="county"),
        dcc.Input(id="state"),
        dcc.Input(id="zip"),
        dcc.Input(id="lat"),
        dcc.Input(id="lon"),
        dcc.Input(id="premium"),
        dcc.Input(id="product"),
        dcc.Input(id="phone"),
        dcc.Input(id="email"),
        dcc.Input(id="dwelling"),
        dcc.Input(id="deductible"),
        dcc.Input(id="status"),
        html.Button("Add", id="add"),

        dash_table.DataTable(id="table"),

        dl.Map(center=[39,-98], zoom=4, children=[
            dl.TileLayer(),
            dl.LayerGroup(id="map")
        ], style={"height":"500px"})
    ])

app.layout = html.Div([
    dcc.Store(id="logged_in", data=False),
    html.Div(id="page")
])

@app.callback(
    Output("page","children"),
    Input("logged_in","data")
)
def render(logged_in):
    if logged_in:
        return build_dashboard_layout()
    return build_login_layout()

@app.callback(
    Output("logged_in","data"),
    Input("login","n_clicks"),
    State("username","value"),
    State("password","value"),
    State("code","value"),
    prevent_initial_call=True
)
def login(_, u,p,c):
    user = authenticate_user_login(u,p,c)
    return True if user else False

@app.callback(
    Output("table","data"),
    Output("map","children"),
    Input("add","n_clicks"),
    State("policy_number","value"),
    State("address","value"),
    State("city","value"),
    State("county","value"),
    State("state","value"),
    State("zip","value"),
    State("lat","value"),
    State("lon","value"),
    State("premium","value"),
    State("product","value"),
    State("phone","value"),
    State("email","value"),
    State("dwelling","value"),
    State("deductible","value"),
    State("status","value"),
    prevent_initial_call=True
)
def add_policy(_, *vals):
    data = dict(zip([
        "policy_number","address","city","county","state","zip",
        "lat","lon","premium","product","phone","email",
        "dwelling_coverage","deductible","policy_status"
    ], vals))

    data["lat"] = float(data["lat"])
    data["lon"] = float(data["lon"])

    add_policy_record(data)

    df = load_dashboard_data()

    markers = []
    for _, r in df.iterrows():
        markers.append(dl.Marker(position=[r["lat"], r["lon"]]))
        markers.append(dl.Marker(position=[r["coast_lat"], r["coast_lon"]]))
        markers.append(dl.Polyline(positions=[
            [r["lat"], r["lon"]],
            [r["coast_lat"], r["coast_lon"]]
        ]))

    return df.to_dict("records"), markers

if __name__ == "__main__":
    app.run(debug=True)