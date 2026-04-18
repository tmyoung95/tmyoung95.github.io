"""
Tyler Young CS-499 Capstone
app.py

This file runs the Dash web application for the authentication dashboard.
It controls the user interface, page flow, login process, MFA setup and
verification screens, and role-based dashboard behavior for admin and
read-only users. It also handles admin user creation and keeps track of
the current session state inside the app. Additionally, it loads a fillable
form to insert one property record and defines the algorithm for calculating the
distance to coast of a policy and sorts the policy into predetermined risk zones
and displays this data on the Dash leaflet map. 
"""


import sqlite3

import dash_leaflet as dl
import geopandas as gpd
import pandas as pd
from dash import Dash, dcc, html, dash_table, Input, Output, State, no_update, ctx
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

# Define policy database
POLICY_DATABASE_NAME = "policies.db"

#File path for coastal shape data
COASTLINE_FILE = "COASTLINE SHAPE DATA/ne_10m_coastline.shp"

# Initialize the users database on app start.
initialize_database()


# Create the policy database on app start.
def initialize_policy_database():
    connection = sqlite3.connect(POLICY_DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS policies (
            policy_number TEXT PRIMARY KEY,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            county TEXT NOT NULL,
            state TEXT NOT NULL,
            zip TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            premium REAL NOT NULL,
            product TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            dwelling_coverage REAL NOT NULL,
            deductible REAL NOT NULL,
            policy_status TEXT NOT NULL
        )
        """
    )

    connection.commit()
    connection.close()


# Open the policies database when policy data needs to be loaded or saved.
def get_policy_connection():
    return sqlite3.connect(POLICY_DATABASE_NAME)


# Load all saved policy records into a DataFrame so the dashboard can use them.
def load_policy_data():
    connection = get_policy_connection()

    try:
        return pd.read_sql_query("SELECT * FROM policies ORDER BY policy_number ASC", connection)
    finally:
        connection.close()


# Check whether a policy number is already saved.
def policy_number_exists(policy_number):
    connection = get_policy_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT 1
        FROM policies
        WHERE policy_number = ?
        LIMIT 1
        """,
        (str(policy_number or "").strip(),)
    )

    result = cursor.fetchone()
    connection.close()
    return result is not None


# Save one policy record so the dashboard has real data to calculate coastal distance from.
def add_policy_record(policy_data):
    if policy_number_exists(policy_data["policy_number"]):
        return False, f"Policy {policy_data['policy_number']} already exists."

    connection = get_policy_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO policies (
            policy_number,
            address,
            city,
            county,
            state,
            zip,
            lat,
            lon,
            premium,
            product,
            phone,
            email,
            dwelling_coverage,
            deductible,
            policy_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    return True, f"Policy {policy_data['policy_number']} was added successfully."


# Create the Dash app.
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Insurance Exposure Dashboard"

# Create the policies database before the app starts loading pages.
initialize_policy_database()

# Load the coastline data once when the app starts.
coast = gpd.read_file(COASTLINE_FILE)
coast = coast.to_crs(epsg=4326)

# Combine the coastline geometry into one object so nearest-point checks are simpler.
coastline = coast.geometry.union_all()

# Base policy structure
BASE_POLICY_COLUMNS = [
    "policy_number",
    "address",
    "city",
    "county",
    "state",
    "zip",
    "lat",
    "lon",
    "premium",
    "product",
    "phone",
    "email",
    "dwelling_coverage",
    "deductible",
    "policy_status",
    "coast_distance_miles",
    "coast_zone",
    "coast_lat",
    "coast_lon"
]


def choose_first_screen():
    # If a fully set up user already exists, start at login.
    if has_completed_user():
        return "login"
    return "setup_account"


def hidden_style():
    # Shared hidden style for sections we want invisible.
    return {"display": "none"}


def visible_panel_style():
    # Shared panel style for forms that open and close.
    return {
        "display": "block",
        "border": "1px solid #ccc",
        "borderRadius": "8px",
        "padding": "16px",
        "marginTop": "12px",
        "backgroundColor": "#fafafa"
    }


def neutral_message_style():
    # Default message styling when nothing is wrong.
    return {
        "marginTop": "12px",
        "fontWeight": "bold",
        "color": "black"
    }


def error_message_style():
    # Shared styling for validation errors and failed actions.
    return {
        "marginTop": "12px",
        "fontWeight": "bold",
        "color": "crimson"
    }


def success_message_style():
    # Shared styling for success messages.
    return {
        "marginTop": "12px",
        "fontWeight": "bold",
        "color": "green"
    }


# Check the new user form values before trying to create the account.
def validate_new_user_form(username, password, confirm_password):
    cleaned_username = str(username or "").strip()
    cleaned_password = str(password or "").strip()
    cleaned_confirm_password = str(confirm_password or "").strip()

    if cleaned_username == "":
        return False, "Please enter a username."

    if cleaned_password == "":
        return False, "Please enter a password."

    if len(cleaned_password) < 8:
        return False, "Password must be at least 8 characters long."

    if cleaned_confirm_password == "":
        return False, "Please confirm the password."

    if cleaned_password != cleaned_confirm_password:
        return False, "Passwords do not match."

    return True, ""


# Check that the policy form is complete and convert number fields before saving.
def validate_policy_form(
    policy_number,
    address,
    city,
    county,
    state,
    zip_code,
    latitude,
    longitude,
    premium,
    product,
    phone,
    email,
    dwelling_coverage,
    deductible,
    policy_status
):
    cleaned_policy_number = str(policy_number or "").strip()
    cleaned_address = str(address or "").strip()
    cleaned_city = str(city or "").strip()
    cleaned_county = str(county or "").strip()
    cleaned_state = str(state or "").strip().upper()
    cleaned_zip = str(zip_code or "").strip()
    cleaned_product = str(product or "").strip()
    cleaned_phone = str(phone or "").strip()
    cleaned_email = str(email or "").strip()
    cleaned_status = str(policy_status or "").strip()

    if cleaned_policy_number == "":
        return False, "Please enter a policy number.", None

    if cleaned_address == "":
        return False, "Please enter an address.", None

    if cleaned_city == "":
        return False, "Please enter a city.", None

    if cleaned_county == "":
        return False, "Please enter a county.", None

    if cleaned_state == "":
        return False, "Please enter a state.", None

    if cleaned_zip == "":
        return False, "Please enter a ZIP code.", None

    if cleaned_product == "":
        return False, "Please enter a product.", None

    if cleaned_phone == "":
        return False, "Please enter a phone number.", None

    if cleaned_email == "":
        return False, "Please enter an email.", None

    if cleaned_status == "":
        return False, "Please enter a policy status.", None

    try:
        parsed_latitude = float(str(latitude or "").strip())
    except ValueError:
        return False, "Latitude must be a number.", None

    if parsed_latitude < -90 or parsed_latitude > 90:
        return False, "Latitude must be between -90 and 90.", None

    try:
        parsed_longitude = float(str(longitude or "").strip())
    except ValueError:
        return False, "Longitude must be a number.", None

    if parsed_longitude < -180 or parsed_longitude > 180:
        return False, "Longitude must be between -180 and 180.", None

    try:
        parsed_premium = float(str(premium or "").strip())
    except ValueError:
        return False, "Premium must be a number.", None

    try:
        parsed_dwelling_coverage = float(str(dwelling_coverage or "").strip())
    except ValueError:
        return False, "Dwelling coverage must be a number.", None

    try:
        parsed_deductible = float(str(deductible or "").strip())
    except ValueError:
        return False, "Deductible must be a number.", None

    cleaned_policy = {
        "policy_number": cleaned_policy_number,
        "address": cleaned_address,
        "city": cleaned_city,
        "county": cleaned_county,
        "state": cleaned_state,
        "zip": cleaned_zip,
        "lat": parsed_latitude,
        "lon": parsed_longitude,
        "premium": parsed_premium,
        "product": cleaned_product,
        "phone": cleaned_phone,
        "email": cleaned_email,
        "dwelling_coverage": parsed_dwelling_coverage,
        "deductible": parsed_deductible,
        "policy_status": cleaned_status
    }

    return True, "", cleaned_policy


def coast_distance_and_point(lat, lon):
    # Build a point from the policy coordinates.
    property_point = Point(lon, lat)

    # nearest_points returns two geometries:
    # the original point and the closest point on the coastline.
    nearest_geom = nearest_points(property_point, coastline)[1]

    #Convert degrees to miles roughly (multiplying by 69 for length, 1 degree of latitude = 69 miles)
    distance = property_point.distance(nearest_geom) * 69

    return round(distance, 2), nearest_geom


def calculate_coast_metrics(dataframe):
    # Add the coast-related fields the dashboard uses later in the table, chart, and map.
    if dataframe.empty:
        # Even with no rows, keep the extra columns so the rest of the UI still works cleanly.
        for column_name in ["coast_distance_miles", "coast_zone", "coast_lat", "coast_lon"]:
            dataframe[column_name] = []
        return dataframe

    # Work on a copy so we do not change the original DataFrame by accident.
    working_dataframe = dataframe.copy()

    distances = []
    zones = []
    coast_latitudes = []
    coast_longitudes = []

    # Go policy by policy and calculate the nearest coast point.
    for _, row in working_dataframe.iterrows():
        distance_miles, nearest_point = coast_distance_and_point(row["lat"], row["lon"])

        distances.append(distance_miles)
        coast_latitudes.append(nearest_point.y)
        coast_longitudes.append(nearest_point.x)

        # Catagorize by risk zone depending on distance to caost
        if distance_miles <= 5:
            zones.append("Coastal")
        elif distance_miles <= 10:
            zones.append("Midland")
        else:
            zones.append("Inland")

    # Attach the new values back onto the DataFrame.
    working_dataframe["coast_distance_miles"] = distances
    working_dataframe["coast_zone"] = zones
    working_dataframe["coast_lat"] = coast_latitudes
    working_dataframe["coast_lon"] = coast_longitudes

    return working_dataframe


# Load the dashboard data and attach coast values so the table can display the calculation results.
def load_dashboard_data():
    try:
        return calculate_coast_metrics(load_policy_data())
    except Exception:
        return pd.DataFrame(columns=BASE_POLICY_COLUMNS)


# Build map layers from the policy data so the policy point and nearest coast point can be displayed.
def build_map_layers(policy_dataframe):
    layers = [dl.TileLayer()]

    for _, row in policy_dataframe.iterrows():
        try:
            property_position = [float(row["lat"]), float(row["lon"])]
            coast_position = [float(row["coast_lat"]), float(row["coast_lon"])]
        except (TypeError, ValueError):
            continue

        layers.append(
            dl.Marker(
                position=property_position,
                children=dl.Tooltip(f"Policy {row['policy_number']}")
            )
        )

        layers.append(
            dl.CircleMarker(
                center=coast_position,
                radius=6,
                color="red",
                children=dl.Tooltip(f"Nearest coast: {row['coast_distance_miles']} miles")
            )
        )

        layers.append(
            dl.Polyline(
                positions=[property_position, coast_position],
                color="red"
            )
        )

    return layers


def build_setup_account_layout(message_text=""):
    # First-time setup page for the very first account.
    # The first account created here becomes the admin.
    return html.Div(
        [
            html.H1("Insurance Exposure Dashboard"),
            html.H3("First-Time Setup"),
            html.P("This version focuses on basic dashboard access, MFA, and user roles."),
            html.P("The first account created in this app will be the admin account."),
            html.P("That admin account will be responsible for creating all future users."),

            html.Div(
                [
                    html.Label("Username"),
                    dcc.Input(
                        id="setup_username",
                        type="text",
                        placeholder="Enter a username",
                        style={"width": "100%"}
                    ),

                    html.Br(),
                    html.Br(),

                    html.Label("Password"),
                    dcc.Input(
                        id="setup_password",
                        type="password",
                        placeholder="Enter a password",
                        style={"width": "100%"}
                    ),

                    html.Br(),
                    html.Br(),

                    html.Label("Confirm Password"),
                    dcc.Input(
                        id="setup_confirm_password",
                        type="password",
                        placeholder="Re-enter your password",
                        style={"width": "100%"}
                    ),

                    html.Br(),
                    html.Br(),

                    html.Button("Create Admin Account", id="create_account_button"),

                    # Reuse the same message area for validation feedback.
                    html.Div(
                        message_text,
                        id="setup_account_message",
                        style=error_message_style() if message_text else neutral_message_style()
                    )
                ],
                style={
                    "maxWidth": "500px",
                    "padding": "24px",
                    "border": "1px solid #ccc",
                    "borderRadius": "8px",
                    "backgroundColor": "#fafafa"
                }
            )
        ],
        style={"padding": "30px"}
    )


def build_verify_mfa_layout(pending_setup_data, message_text=""):
    # Show the QR code and let the user finish MFA setup.
    username = pending_setup_data["username"]
    qr_image_base64 = build_mfa_qr_code_base64(
        username=username,
        mfa_secret=pending_setup_data["mfa_secret"]
    )

    is_admin = pending_setup_data["role"] == "admin"

    # Set a reminder that only admins can create new users.
    extra_message = ""
    if is_admin:
        extra_message = (
            " This is your admin account. After this is finished, all new users must be created through that admin account."
        )

    return html.Div(
        [
            html.H1("Insurance Exposure Dashboard"),
            html.H3("Finish MFA Setup"),
            html.P(f"Account created for {username}.{extra_message}"),
            html.P("Scan this QR code with the AUthentickey phone app."),

            html.Img(
                src=f"data:image/png;base64,{qr_image_base64}",
                style={
                    "width": "260px",
                    "height": "260px",
                    "border": "1px solid #ccc",
                    "padding": "10px",
                    "backgroundColor": "white"
                }
            ),

            html.Br(),
            html.Br(),

            html.Label("Enter the 6-digit code from your authenticator app"),
            dcc.Input(
                id="verify_mfa_code",
                type="text",
                placeholder="123456",
                style={"width": "250px"}
            ),

            html.Br(),
            html.Br(),

            html.Button("Verify and Finish Setup", id="finish_setup_button"),

            html.Div(
                message_text,
                id="verify_setup_message",
                style=error_message_style() if message_text else neutral_message_style()
            )
        ],
        style={"padding": "30px"}
    )


def build_login_layout(message_text=""):
    # Standard login screen after setup is complete.
    return html.Div(
        [
            html.H1("Insurance Exposure Dashboard"),
            html.H3("Login"),

            html.Div(
                [
                    html.Label("Username"),
                    dcc.Input(
                        id="login_username",
                        type="text",
                        placeholder="Enter your username",
                        style={"width": "100%"}
                    ),

                    html.Br(),
                    html.Br(),

                    html.Label("Password"),
                    dcc.Input(
                        id="login_password",
                        type="password",
                        placeholder="Enter your password",
                        style={"width": "100%"}
                    ),

                    html.Br(),
                    html.Br(),

                    html.Label("Authenticator Code"),
                    dcc.Input(
                        id="login_mfa_code",
                        type="text",
                        placeholder="Enter your 6-digit code",
                        style={"width": "100%"}
                    ),

                    html.Br(),
                    html.Br(),

                    html.Button("Login", id="login_button"),

                    html.Div(
                        message_text,
                        id="login_message",
                        style=error_message_style() if message_text else neutral_message_style()
                    )
                ],
                style={
                    "maxWidth": "500px",
                    "padding": "24px",
                    "border": "1px solid #ccc",
                    "borderRadius": "8px",
                    "backgroundColor": "#fafafa"
                }
            )
        ],
        style={"padding": "30px"}
    )


def build_admin_dashboard_layout(
    current_user,
    create_user_message="",
    pending_user_mfa_data=None,
    pending_user_mfa_message="",
    new_user_form_visible=False,
    policy_form_visible=False,
    policy_form_message="",
    policy_form_message_style=None
):
    # Basic admin dashboard with user management.
    user_rows = list_users()
    policy_rows = load_dashboard_data()

    pending_mfa_panel = html.Div()
    if pending_user_mfa_data is not None:
        qr_image_base64 = build_mfa_qr_code_base64(
            username=pending_user_mfa_data["username"],
            mfa_secret=pending_user_mfa_data["mfa_secret"]
        )

        pending_mfa_panel = html.Div(
            [
                html.H4("Finish New User MFA Setup"),
                html.P(f"Complete authenticator enrollment for {pending_user_mfa_data['username']} ({pending_user_mfa_data['role']})."),
                html.P("Scan this QR code with Google Authenticator, Microsoft Authenticator, or Authy, then enter the 6-digit code below."),
                html.Img(
                    src=f"data:image/png;base64,{qr_image_base64}",
                    style={
                        "width": "260px",
                        "height": "260px",
                        "border": "1px solid #ccc",
                        "padding": "10px",
                        "backgroundColor": "white"
                    }
                ),
                html.Br(),
                html.Br(),
                html.Label("Enter the 6-digit code from the authenticator app"),
                dcc.Input(
                    id="admin_verify_new_user_mfa_code",
                    type="text",
                    placeholder="123456",
                    style={"width": "250px"}
                ),
                html.Br(),
                html.Br(),
                html.Button("Verify New User MFA", id="admin_finish_new_user_mfa_button"),
                html.Div(
                    pending_user_mfa_message,
                    id="admin_pending_user_mfa_message",
                    style=success_message_style() if pending_user_mfa_message and "complete" in pending_user_mfa_message.lower() else (error_message_style() if pending_user_mfa_message else neutral_message_style())
                )
            ],
            style=visible_panel_style()
        )

    if policy_form_message_style is None:
        policy_form_message_style = neutral_message_style()

    new_user_form_style = visible_panel_style() if new_user_form_visible else hidden_style()
    policy_form_style = visible_panel_style() if policy_form_visible else hidden_style()

    new_user_form_panel = html.Div(
        [
            html.H4("Create New User"),

            html.Label("Username"),
            dcc.Input(id="admin_new_username", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Password"),
            dcc.Input(id="admin_new_password", type="password", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Confirm Password"),
            dcc.Input(id="admin_confirm_password", type="password", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Role"),
            dcc.Dropdown(
                id="admin_new_role",
                options=[
                    {"label": "Admin", "value": "admin"},
                    {"label": "Read Only", "value": "read_only"}
                ],
                value="read_only",
                clearable=False
            ),

            html.Br(),
            html.Button("Create User", id="admin_create_user_button"),
            html.Button("Cancel", id="cancel_new_user_button", style={"marginLeft": "8px"}),

            html.Div(
                create_user_message,
                id="admin_create_user_message",
                style=success_message_style() if create_user_message and "created" in create_user_message.lower() else (error_message_style() if create_user_message else neutral_message_style())
            )
        ],
        style=new_user_form_style
    )

    policy_form_panel = html.Div(
        [
            html.H4("Add Policy"),

            html.Label("Policy Number"),
            dcc.Input(id="policy_number_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Address"),
            dcc.Input(id="address_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("City"),
            dcc.Input(id="city_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("County"),
            dcc.Input(id="county_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("State"),
            dcc.Input(id="state_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("ZIP"),
            dcc.Input(id="zip_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Latitude"),
            dcc.Input(id="lat_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Longitude"),
            dcc.Input(id="lon_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Premium"),
            dcc.Input(id="premium_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Product"),
            dcc.Input(id="product_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Phone"),
            dcc.Input(id="phone_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Email"),
            dcc.Input(id="email_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Dwelling Coverage"),
            dcc.Input(id="dwelling_coverage_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Deductible"),
            dcc.Input(id="deductible_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Label("Policy Status"),
            dcc.Input(id="policy_status_input", type="text", style={"width": "100%"}),

            html.Br(),
            html.Br(),

            html.Button("Save Policy", id="save_policy_button"),
            html.Button("Cancel", id="cancel_policy_button", style={"marginLeft": "8px"}),

            html.Div(
                policy_form_message,
                id="policy_form_message",
                style=policy_form_message_style
            )
        ],
        style=policy_form_style
    )

    return html.Div(
        [
            html.Div(
                [
                    html.H1("Insurance Exposure Dashboard"),
                    html.P(f"Logged in as {current_user['username']} ({current_user['role']})"),
                    html.Button("Logout", id="logout_button")
                ]
            ),

            html.H3("Admin Dashboard"),
            html.P("Admins can create new users and review the current user list."),

            html.Div(
                [
                    html.H4("User Management"),
                    html.Button("Add User", id="show_new_user_form_button"),
                    new_user_form_panel
                ],
                style={"marginTop": "20px"}
            ),

            pending_mfa_panel,

            html.Div(
                [
                    html.H4("Policy Entry"),
                    html.Button("Add Policy", id="show_policy_form_button"),
                    policy_form_panel
                ],
                style={"marginTop": "20px"}
            ),

            html.H4("Current Policies"),
            dash_table.DataTable(
                id="policy_table",
                columns=[{"name": column_name, "id": column_name} for column_name in BASE_POLICY_COLUMNS],
                data=policy_rows.to_dict("records"),
                page_size=10,
                style_table={"overflowX": "auto", "marginTop": "12px"},
                style_cell={"textAlign": "left", "padding": "8px"}
            ),

            html.H4("Policy Map"),
            dl.Map(
                center=[39, -98],
                zoom=4,
                children=build_map_layers(policy_rows),
                style={"height": "500px", "width": "100%", "marginTop": "12px"}
            ),

            html.H4("Current Users"),
            dash_table.DataTable(
                id="user_table",
                columns=[
                    {"name": "Username", "id": "username"},
                    {"name": "Role", "id": "role"},
                    {"name": "Setup Complete", "id": "setup_complete"}
                ],
                data=user_rows,
                page_size=10,
                style_table={"overflowX": "auto", "marginTop": "12px"},
                style_cell={"textAlign": "left", "padding": "8px"}
            )
        ],
        style={"padding": "30px"}
    )


def build_read_only_dashboard_layout(current_user):
    # Basic read-only dashboard for non-admin users.
    policy_rows = load_dashboard_data()

    return html.Div(
        [
            html.Div(
                [
                    html.H1("Insurance Exposure Dashboard"),
                    html.P(f"Logged in as {current_user['username']} ({current_user['role']})"),
                    html.Button("Logout", id="logout_button")
                ]
            ),

            html.H3("Read-Only Dashboard"),
            html.P("This basic version only demonstrates successful authentication, MFA, and role-based access."),
            html.P("Read-only users can sign in and access the dashboard, but they cannot create new users."),

            html.H4("Current Policies"),
            dash_table.DataTable(
                id="policy_table",
                columns=[{"name": column_name, "id": column_name} for column_name in BASE_POLICY_COLUMNS],
                data=policy_rows.to_dict("records"),
                page_size=10,
                style_table={"overflowX": "auto", "marginTop": "12px"},
                style_cell={"textAlign": "left", "padding": "8px"}
            ),

            html.H4("Policy Map"),
            dl.Map(
                center=[39, -98],
                zoom=4,
                children=build_map_layers(policy_rows),
                style={"height": "500px", "width": "100%", "marginTop": "12px"}
            )
        ],
        style={"padding": "30px"}
    )


app.layout = html.Div(
    [
        dcc.Store(id="screen_store", data=choose_first_screen()),
        dcc.Store(id="pending_setup_store"),
        dcc.Store(id="current_user_store"),
        dcc.Store(id="admin_create_user_message_store", data=""),
        dcc.Store(id="admin_pending_user_mfa_store"),
        dcc.Store(id="new_user_form_visible_store", data=False),
        dcc.Store(id="policy_form_visible_store", data=False),
        dcc.Store(id="policy_form_message_store", data=""),
        dcc.Store(id="policy_form_message_style_store", data=neutral_message_style()),
        dcc.Store(id="policy_refresh_store", data=0),
        html.Div(id="page_container")
    ]
)


@app.callback(
    Output("page_container", "children"),
    Input("screen_store", "data"),
    Input("pending_setup_store", "data"),
    Input("current_user_store", "data"),
    Input("admin_create_user_message_store", "data"),
    Input("admin_pending_user_mfa_store", "data"),
    Input("new_user_form_visible_store", "data"),
    Input("policy_form_visible_store", "data"),
    Input("policy_form_message_store", "data"),
    Input("policy_form_message_style_store", "data"),
    Input("policy_refresh_store", "data")
)
def render_page(
    screen_name,
    pending_setup_data,
    current_user,
    admin_create_user_message,
    admin_pending_user_mfa_data,
    new_user_form_visible,
    policy_form_visible,
    policy_form_message,
    policy_form_message_style,
    _policy_refresh
):
    # Render the right screen based on the current app state.
    if screen_name == "setup_account":
        return build_setup_account_layout()

    if screen_name == "verify_mfa" and pending_setup_data is not None:
        return build_verify_mfa_layout(pending_setup_data)

    if screen_name == "login":
        return build_login_layout()

    if screen_name == "dashboard" and current_user is not None:
        if current_user["role"] == "admin":
            pending_user_mfa_message = ""
            if admin_pending_user_mfa_data is not None:
                pending_user_mfa_message = admin_pending_user_mfa_data.get("message", "")
            return build_admin_dashboard_layout(
                current_user,
                admin_create_user_message,
                admin_pending_user_mfa_data,
                pending_user_mfa_message,
                new_user_form_visible,
                policy_form_visible,
                policy_form_message,
                policy_form_message_style
            )
        return build_read_only_dashboard_layout(current_user)

    return build_login_layout()


@app.callback(
    Output("screen_store", "data", allow_duplicate=True),
    Output("pending_setup_store", "data", allow_duplicate=True),
    Output("setup_account_message", "children", allow_duplicate=True),
    Output("setup_account_message", "style", allow_duplicate=True),
    Input("create_account_button", "n_clicks"),
    State("setup_username", "value"),
    State("setup_password", "value"),
    State("setup_confirm_password", "value"),
    prevent_initial_call=True
)
def create_first_admin_account(n_clicks, username, password, confirm_password):
    # Create the very first admin account and move to MFA setup.
    is_valid, validation_message = validate_new_user_form(username, password, confirm_password)
    if not n_clicks:
        return no_update, no_update, no_update, no_update

    if not is_valid:
        return no_update, no_update, validation_message, error_message_style()

    was_created, message_text, created_user = create_user_account(username, password, "admin")
    if not was_created:
        return no_update, no_update, message_text, error_message_style()

    return "verify_mfa", created_user, "", neutral_message_style()


@app.callback(
    Output("screen_store", "data", allow_duplicate=True),
    Output("verify_setup_message", "children", allow_duplicate=True),
    Output("verify_setup_message", "style", allow_duplicate=True),
    Input("finish_setup_button", "n_clicks"),
    State("pending_setup_store", "data"),
    State("verify_mfa_code", "value"),
    prevent_initial_call=True
)
def finish_first_time_setup(n_clicks, pending_setup_data, mfa_code):
    # Finish the MFA setup flow for the pending account.
    if not n_clicks:
        return no_update, no_update, no_update

    if pending_setup_data is None:
        return no_update, "No account is waiting for MFA setup.", error_message_style()

    was_verified, message_text = verify_first_time_mfa_setup(
        username=pending_setup_data["username"],
        mfa_code=mfa_code
    )

    if not was_verified:
        return no_update, message_text, error_message_style()

    return "login", message_text, success_message_style()


@app.callback(
    Output("screen_store", "data", allow_duplicate=True),
    Output("current_user_store", "data", allow_duplicate=True),
    Output("login_message", "children", allow_duplicate=True),
    Output("login_message", "style", allow_duplicate=True),
    Input("login_button", "n_clicks"),
    State("login_username", "value"),
    State("login_password", "value"),
    State("login_mfa_code", "value"),
    prevent_initial_call=True
)
def login_user(n_clicks, username, password, mfa_code):
    # Authenticate the user with username, password, and MFA.
    was_authenticated, message_text, current_user = authenticate_user_login(username, password, mfa_code)

    if not n_clicks:
        return no_update, no_update, no_update, no_update

    if not was_authenticated:
        return no_update, no_update, message_text, error_message_style()

    return "dashboard", current_user, "", neutral_message_style()


@app.callback(
    Output("screen_store", "data", allow_duplicate=True),
    Output("current_user_store", "data", allow_duplicate=True),
    Output("pending_setup_store", "data", allow_duplicate=True),
    Output("admin_create_user_message_store", "data", allow_duplicate=True),
    Output("admin_pending_user_mfa_store", "data", allow_duplicate=True),
    Output("new_user_form_visible_store", "data", allow_duplicate=True),
    Output("policy_form_visible_store", "data", allow_duplicate=True),
    Output("policy_form_message_store", "data", allow_duplicate=True),
    Output("policy_form_message_style_store", "data", allow_duplicate=True),
    Input("logout_button", "n_clicks"),
    prevent_initial_call=True
)
def logout_user(n_clicks):
    # Clear the session stores and send the user back to login.
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

    return "login", None, None, "", None, False, False, "", neutral_message_style()


@app.callback(
    Output("new_user_form_visible_store", "data", allow_duplicate=True),
    Output("admin_create_user_message_store", "data", allow_duplicate=True),
    Input("show_new_user_form_button", "n_clicks"),
    Input("cancel_new_user_button", "n_clicks"),
    prevent_initial_call=True
)
def toggle_new_user_form(show_clicks, cancel_clicks):
    triggered_id = ctx.triggered_id

    if triggered_id == "show_new_user_form_button":
        return True, ""

    if triggered_id == "cancel_new_user_button":
        return False, ""

    return no_update, no_update


@app.callback(
    Output("screen_store", "data", allow_duplicate=True),
    Output("pending_setup_store", "data", allow_duplicate=True),
    Output("admin_create_user_message_store", "data", allow_duplicate=True),
    Output("admin_pending_user_mfa_store", "data", allow_duplicate=True),
    Output("new_user_form_visible_store", "data", allow_duplicate=True),
    Input("admin_create_user_button", "n_clicks"),
    State("current_user_store", "data"),
    State("admin_new_username", "value"),
    State("admin_new_password", "value"),
    State("admin_confirm_password", "value"),
    State("admin_new_role", "value"),
    prevent_initial_call=True
)
def admin_create_user(n_clicks, current_user, username, password, confirm_password, role):
    # Let the admin create another user and send that new user through MFA setup.
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update

    if current_user is None or current_user.get("role") != "admin":
        return no_update, no_update, "Only admins can create users.", no_update, no_update

    is_valid, validation_message = validate_new_user_form(username, password, confirm_password)
    if not is_valid:
        return no_update, no_update, validation_message, no_update, True

    was_created, message_text, created_user = create_user_account(username, password, role)
    if not was_created:
        return no_update, no_update, message_text, no_update, True

    created_user["message"] = ""
    return "dashboard", no_update, "User created successfully. Complete MFA setup below.", created_user, False


@app.callback(
    Output("screen_store", "data", allow_duplicate=True),
    Output("admin_pending_user_mfa_store", "data", allow_duplicate=True),
    Output("admin_create_user_message_store", "data", allow_duplicate=True),
    Input("admin_finish_new_user_mfa_button", "n_clicks"),
    State("current_user_store", "data"),
    State("admin_pending_user_mfa_store", "data"),
    State("admin_verify_new_user_mfa_code", "value"),
    prevent_initial_call=True
)
def finish_admin_created_user_mfa(n_clicks, current_user, pending_user_mfa_data, mfa_code):
    # Let the admin finish MFA setup for a newly created user without leaving the dashboard.
    if not n_clicks:
        return no_update, no_update, no_update

    if current_user is None or current_user.get("role") != "admin":
        return no_update, no_update, "Only admins can verify new users."

    if pending_user_mfa_data is None:
        return no_update, no_update, "No new user is waiting for MFA setup."

    was_verified, message_text = verify_first_time_mfa_setup(
        username=pending_user_mfa_data["username"],
        mfa_code=mfa_code
    )

    if not was_verified:
        pending_user_mfa_data["message"] = message_text
        return "dashboard", pending_user_mfa_data, no_update

    return "dashboard", None, f"MFA setup complete for {pending_user_mfa_data['username']}."


@app.callback(
    Output("policy_form_visible_store", "data", allow_duplicate=True),
    Output("policy_form_message_store", "data", allow_duplicate=True),
    Output("policy_form_message_style_store", "data", allow_duplicate=True),
    Input("show_policy_form_button", "n_clicks"),
    Input("cancel_policy_button", "n_clicks"),
    prevent_initial_call=True
)
def toggle_policy_form(show_policy_form_clicks, cancel_policy_clicks):
    triggered_id = ctx.triggered_id

    if triggered_id == "show_policy_form_button":
        return True, "", neutral_message_style()

    if triggered_id == "cancel_policy_button":
        return False, "", neutral_message_style()

    return no_update, no_update, no_update


@app.callback(
    Output("policy_form_visible_store", "data", allow_duplicate=True),
    Output("policy_form_message_store", "data", allow_duplicate=True),
    Output("policy_form_message_style_store", "data", allow_duplicate=True),
    Output("policy_refresh_store", "data", allow_duplicate=True),
    Input("save_policy_button", "n_clicks"),
    State("policy_refresh_store", "data"),
    State("policy_number_input", "value"),
    State("address_input", "value"),
    State("city_input", "value"),
    State("county_input", "value"),
    State("state_input", "value"),
    State("zip_input", "value"),
    State("lat_input", "value"),
    State("lon_input", "value"),
    State("premium_input", "value"),
    State("product_input", "value"),
    State("phone_input", "value"),
    State("email_input", "value"),
    State("dwelling_coverage_input", "value"),
    State("deductible_input", "value"),
    State("policy_status_input", "value"),
    prevent_initial_call=True
)
def save_policy(
    n_clicks,
    current_refresh_value,
    policy_number,
    address,
    city,
    county,
    state,
    zip_code,
    latitude,
    longitude,
    premium,
    product,
    phone,
    email,
    dwelling_coverage,
    deductible,
    policy_status
):
    if not n_clicks:
        return no_update, no_update, no_update, no_update

    is_valid, message_text, cleaned_policy = validate_policy_form(
        policy_number,
        address,
        city,
        county,
        state,
        zip_code,
        latitude,
        longitude,
        premium,
        product,
        phone,
        email,
        dwelling_coverage,
        deductible,
        policy_status
    )

    if not is_valid:
        return True, message_text, error_message_style(), no_update

    was_saved, save_message = add_policy_record(cleaned_policy)
    if not was_saved:
        return True, save_message, error_message_style(), no_update

    refreshed_dataframe = load_dashboard_data()
    saved_row = refreshed_dataframe[refreshed_dataframe["policy_number"] == cleaned_policy["policy_number"]]

    if not saved_row.empty:
        saved_policy = saved_row.iloc[0]
        save_message = (
            f"Policy {saved_policy['policy_number']} was added successfully. "
            f"Distance to coast: {saved_policy['coast_distance_miles']} miles. "
            f"Zone: {saved_policy['coast_zone']}."
        )

    return False, save_message, success_message_style(), (current_refresh_value or 0) + 1


if __name__ == "__main__":
    app.run(debug=True)