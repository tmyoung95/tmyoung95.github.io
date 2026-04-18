"""
Tyler Young CS-499 Capstone
app.py

This file runs the Dash web application for the Insurance Exposure Dashboard.
It controls the full user interface, including account setup, login, MFA setup
and verification, and role-based dashboard behavior for admin and read-only users.
It manages page flow between setup, login, and dashboard screens while tracking
session state using stored components within the app.

It also loads and processes policy data from the database, including adding,
editing, deleting, and importing records through a CSV upload. The file defines
a fillable policy form for manual data entry and uses validation functions to
ensure data integrity before saving.

Additionally, it loads coastline shapefile data and defines the logic for
calculating the distance from each policy to the nearest coastline point.
Based on this distance, policies are categorized into coastal risk zones and
displayed visually on a Dash Leaflet map alongside policy markers and connecting
lines. The file also builds summary charts and filtering tools to allow users
to analyze policy data by state, county, product, and risk category.
"""

#Import statements. 

import base64
import io
import pandas as pd
import plotly.express as px
import dash_leaflet as dl
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import nearest_points
from dash import Dash, dcc, html, dash_table, Input, Output, State, no_update, ctx

from auth import (
    create_user_account,
    verify_first_time_mfa_setup,
    authenticate_user_login,
    build_mfa_qr_code_base64
)
from database import (
    initialize_database,
    has_completed_user,
    list_users,
    load_policy_data,
    add_policy_record,
    update_policy_record,
    delete_policy_record,
    import_policy_csv_dataframe,
    get_state_list,
    get_county_list
)
from validation import validate_new_user_form, validate_policy_form


# Initilize database on app start.
initialize_database()

# Create the Dash app
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Insurance Exposure Dashboard"


# Load the coastline data once when the app starts.
coast = gpd.read_file("COASTLINE SHAPE DATA/ne_10m_coastline.shp")
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


def load_dashboard_data():
    # Pull policy data from the database, then add the coast fields the dashboard expects.
    try:
        dataframe = load_policy_data()
        return calculate_coast_metrics(dataframe)
    except Exception:
        # If loading fails, return an empty frame with the right columns instead of crashing the app.
        return pd.DataFrame(columns=BASE_POLICY_COLUMNS)


def choose_first_screen():
    # Decide whether the app should open on setup or login. If no user is detected, the app will direct them to the account setup screen.
    if has_completed_user():
        return "login"
    return "setup_account"


def blank_policy_form_values():
    # One place for the empty policy form values for rssets.
    return (
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        ""
    )


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


def build_setup_account_layout(message_text=""):
    # First-time setup page for the very first account.
    # The first account created here becomes the admin.
    return html.Div(
        [
            html.H1("Insurance Exposure Dashboard"),
            html.H3("First-Time Setup"),
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
    
    #Set message to remind user that only admins can create new users
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
            html.P("Scan this QR code with the AuthenticKey phone app."),

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


def build_policy_form():
    # This form handles both add and edit mode.
    return html.Div(
        id="policy_form_area",
        style=hidden_style(),
        children=[
            html.H3(id="policy_form_title", children="Add Policy"),

            # Form formatting
            html.Div(
                [
                    html.Div([html.Label("Policy Number"), dcc.Input(id="policy_number_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("Address"), dcc.Input(id="address_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("City"), dcc.Input(id="city_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("County"), dcc.Input(id="county_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("State"), dcc.Input(id="state_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("ZIP Code"), dcc.Input(id="zip_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("Latitude"), dcc.Input(id="lat_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("Longitude"), dcc.Input(id="lon_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("Premium"), dcc.Input(id="premium_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("Product"), dcc.Input(id="product_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("Phone"), dcc.Input(id="phone_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("Email"), dcc.Input(id="email_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("Dwelling Coverage"), dcc.Input(id="dwelling_coverage_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("Deductible"), dcc.Input(id="deductible_input", type="text", style={"width": "100%"})]),
                    html.Div([html.Label("Policy Status"), dcc.Input(id="policy_status_input", type="text", style={"width": "100%"})]),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr",
                    "gap": "12px",
                    "maxWidth": "1000px"
                }
            ),

            html.Br(),

            html.Button("Save Policy", id="save_policy_button"),
            html.Button("Cancel", id="cancel_policy_form_button", style={"marginLeft": "10px"}),

            # This message area is for validation errors or save success.
            html.Div(
                id="policy_form_message",
                children="",
                style=neutral_message_style()
            )
        ]
    )


def build_new_user_mfa_panel(pending_user_data, message_text=""):
    # After an admin creates a user, this panel finishes MFA for that account.
    qr_image_base64 = build_mfa_qr_code_base64(
        username=pending_user_data["username"],
        mfa_secret=pending_user_data["mfa_secret"]
    )

    return html.Div(
        [
            html.H4(f"Finish MFA Setup for {pending_user_data['username']}"),
            html.P(
                f"Role: {pending_user_data['role']}. Have that user scan the QR code and enter one valid code below to finish setup."
            ),

            html.Img(
                src=f"data:image/png;base64,{qr_image_base64}",
                style={
                    "width": "240px",
                    "height": "240px",
                    "border": "1px solid #ccc",
                    "padding": "10px",
                    "backgroundColor": "white"
                }
            ),

            html.Br(),
            html.Br(),

            dcc.Input(
                id="new_user_mfa_code",
                type="text",
                placeholder="Enter 6-digit code",
                style={"width": "220px"}
            ),
            html.Button("Finish New User Setup", id="finish_new_user_setup_button", style={"marginLeft": "10px"}),

            html.Div(
                message_text,
                id="new_user_mfa_message",
                style=error_message_style() if message_text else neutral_message_style()
            )
        ]
    )


def build_admin_user_panel(is_admin):
    panel_style = visible_panel_style() if is_admin else hidden_style()

    return html.Div(
        [
            html.H2("User Management"),
            html.P("Only admins can create users. Read-only users can view data but cannot change records."),

            html.Button(
                "Create New User",
                id="show_new_user_form_button",
                disabled=not is_admin
            ),

            # This form starts hidden and opens only when an admin clicks the button.
            html.Div(
                id="new_user_form_area",
                style=hidden_style(),
                children=[
                    html.Div(
                        [
                            html.Div([html.Label("New Username"), dcc.Input(id="new_user_username", type="text", style={"width": "100%"})]),
                            html.Div([html.Label("Password"), dcc.Input(id="new_user_password", type="password", style={"width": "100%"})]),
                            html.Div([html.Label("Confirm Password"), dcc.Input(id="new_user_confirm_password", type="password", style={"width": "100%"})]),
                            html.Div(
                                [
                                    html.Label("Role"),
                                    dcc.Dropdown(
                                        id="new_user_role",
                                        options=[
                                            {"label": "Admin", "value": "admin"},
                                            {"label": "Read Only", "value": "read_only"}
                                        ],
                                        value="read_only",
                                        clearable=False,
                                        disabled=not is_admin
                                    )
                                ]
                            )
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "1fr 1fr",
                            "gap": "12px",
                            "maxWidth": "900px"
                        }
                    ),

                    html.Br(),

                    html.Button("Create User", id="create_new_user_button", disabled=not is_admin),
                    html.Button("Cancel", id="cancel_new_user_form_button", style={"marginLeft": "10px"}, disabled=not is_admin),

                    html.Div(
                        id="create_new_user_message",
                        children="",
                        style=neutral_message_style()
                    ),

                    # After user creation, the MFA QR panel gets created here.
                    html.Div(id="new_user_mfa_panel", style={"marginTop": "18px"})
                ]
            ),

            html.H3("Existing Users"),
            dash_table.DataTable(
                id="user_table",
                data=list_users().to_dict("records"),
                columns=[
                    {"name": "username", "id": "username"},
                    {"name": "role", "id": "role"},
                    {"name": "setup_complete", "id": "setup_complete"}
                ],
                page_size=10,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "8px"},
                style_header={"fontWeight": "bold"}
            )
        ],
        style=panel_style
    )


def build_dashboard_layout(current_user):
    # Main dashboard after a successful login.
    dataframe = load_dashboard_data()
    is_admin = current_user["role"] == "admin"

    admin_banner = html.Div()
    if is_admin:
        # Give admins a small reminder that they can manage users from here.
        admin_banner = html.Div(
            [
                html.Strong("Admin account: "),
                html.Span("You can create future users from this dashboard.")
            ],
            style={
                "padding": "10px",
                "backgroundColor": "#eef6ff",
                "border": "1px solid #b6d4fe",
                "borderRadius": "6px",
                "marginBottom": "18px"
            }
        )

    policy_action_area = html.Div(
        [
            html.H2("Policy Actions"),
            html.Button(
                "Add Policy",
                id="show_add_policy_button",
                disabled=not is_admin
            ),
            html.Div(
                "This account is read only. You can view and filter data, but you cannot change it.",
                style=neutral_message_style() if not is_admin else hidden_style()
            ),
            build_policy_form()
        ]
    )

    return html.Div(
        [
            html.Div(
                [
                    html.H1("Insurance Exposure Dashboard"),
                    html.Div(
                        [
                            html.Span(f"Signed in as: {current_user['username']} ({current_user['role']})"),
                            html.Button("Logout", id="logout_button", style={"marginLeft": "20px"})
                        ]
                    )
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center"
                }
            ),

            html.Hr(),

            admin_banner,
            policy_action_area,

            html.Hr(),

            html.H2("Import Policies from CSV"),
            html.P("Upload a CSV to add records in bulk. Duplicate policy numbers will be skipped."),

            html.Div(
                [
                    dcc.Upload(
                        id="csv_upload",
                        children=html.Div("Drag a CSV here or click to choose a file"),
                        style={
                            "width": "100%",
                            "height": "60px",
                            "lineHeight": "60px",
                            "borderWidth": "1px",
                            "borderStyle": "dashed",
                            "borderRadius": "8px",
                            "textAlign": "center",
                            "marginBottom": "12px"
                        },
                        multiple=False,
                        disabled=not is_admin
                    ),
                    html.Button("Import CSV", id="import_csv_button", disabled=not is_admin),
                    html.Div(
                        id="csv_import_message",
                        children="",
                        style=neutral_message_style()
                    )
                ]
            ),

            html.Hr(),

            html.H2("Filters and Analysis"),

            # State and county dropdowns.
            dcc.Dropdown(
                id="state_filter",
                options=[],
                placeholder="Filter by State"
            ),

            html.Br(),

            dcc.Dropdown(
                id="county_filter",
                options=[],
                placeholder="Filter by County"
            ),

            html.Br(),

            # Change what the summary chart is showing.
            dcc.RadioItems(
                id="analysis_type",
                options=[
                    {"label": "Premium by Product", "value": "premium"},
                    {"label": "Policy Count by Product", "value": "count"},
                    {"label": "Coverage Exposure", "value": "coverage"},
                    {"label": "Coastal Risk Distribution", "value": "coastal"}
                ],
                value="premium",
                inline=True
            ),

            html.Hr(),

            html.H2("Policy List"),

            html.Div(
                [
                    html.Button(
                        "Edit Selected Policy",
                        id="show_edit_policy_button",
                        disabled=not is_admin
                    ),
                    html.Button(
                        "Delete Selected Policy",
                        id="delete_selected_policy_button",
                        style={"marginLeft": "10px"},
                        disabled=not is_admin
                    ),
                    html.Div(
                        id="table_action_message",
                        children="",
                        style=neutral_message_style()
                    )
                ],
                style={"marginBottom": "12px"}
            ),

            # Main policy table
            dash_table.DataTable(
                id="policy_table",
                data=dataframe.to_dict("records"),
                columns=[{"name": column_name, "id": column_name} for column_name in dataframe.columns],
                page_size=10,
                row_selectable="single",
                selected_rows=[],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "8px"},
                style_header={"fontWeight": "bold"}
            ),

            # Summary chart
            dcc.Graph(id="summary_chart"),

            # Map for policy/coast data
            dl.Map(
                center=[39, -98],
                zoom=4,
                style={"width": "100%", "height": "500px"},
                children=[dl.TileLayer(), dl.LayerGroup(id="map_layers")]
            ),

            build_admin_user_panel(is_admin)
        ],
        style={"padding": "24px"}
    )


def build_summary_chart(dataframe, analysis_type):
    # Build chart depending on selected analysis type.
    if dataframe.empty:
        return px.bar(title="No data available")

    if analysis_type == "premium":
        grouped_dataframe = (
            dataframe.groupby("product", as_index=False)["premium"]
            .sum()
            .sort_values("premium", ascending=False)
        )
        return px.bar(
            grouped_dataframe,
            x="product",
            y="premium",
            title="Total Premium by Product"
        )

    if analysis_type == "count":
        grouped_dataframe = (
            dataframe.groupby("product", as_index=False)["policy_number"]
            .count()
            .rename(columns={"policy_number": "policy_count"})
            .sort_values("policy_count", ascending=False)
        )
        return px.bar(
            grouped_dataframe,
            x="product",
            y="policy_count",
            title="Policy Count by Product"
        )

    if analysis_type == "coverage":
        grouped_dataframe = (
            dataframe.groupby("product", as_index=False)["dwelling_coverage"]
            .sum()
            .sort_values("dwelling_coverage", ascending=False)
        )
        return px.bar(
            grouped_dataframe,
            x="product",
            y="dwelling_coverage",
            title="Total Coverage by Product"
        )

    grouped_dataframe = (
        dataframe.groupby("coast_zone", as_index=False)["policy_number"]
        .count()
        .rename(columns={"policy_number": "policy_count"})
        .sort_values("policy_count", ascending=False)
    )
    return px.bar(
        grouped_dataframe,
        x="coast_zone",
        y="policy_count",
        title="Coastal Risk Distribution"
    )


def build_map_layers(dataframe):
    # Build markers and coast lines for each visible policy.
    if dataframe.empty:
        return []

    map_items = []

    for _, row in dataframe.iterrows():
        # Popup for policy marker
        policy_popup = (
            f"Policy: {row['policy_number']} | "
            f"Product: {row['product']} | "
            f"Distance to Coast: {row['coast_distance_miles']} miles | "
            f"Zone: {row['coast_zone']}"
        )

        # Popup for coast point
        coast_popup = (
            f"Nearest Coast Point | "
            f"Distance: {row['coast_distance_miles']} miles"
        )

        # Policy marker
        map_items.append(
            dl.Marker(
                position=[row["lat"], row["lon"]],
                children=[dl.Popup(policy_popup)]
            )
        )

        # Coast point marker
        map_items.append(
            dl.CircleMarker(
                center=[row["coast_lat"], row["coast_lon"]],
                radius=5,
                color="red",
                fill=True,
                fillOpacity=0.8,
                children=[dl.Popup(coast_popup)]
            )
        )

        # Line between policy and coast point
        map_items.append(
            dl.Polyline(
                positions=[
                    [row["lat"], row["lon"]],
                    [row["coast_lat"], row["coast_lon"]]
                ],
                color="red",
                weight=3,
                opacity=0.8
            )
        )

    return map_items


def filter_policy_dataframe(dataframe, selected_state, selected_county):
    # Apply state and county filters.
    filtered_dataframe = dataframe.copy()

    if selected_state:
        filtered_dataframe = filtered_dataframe[filtered_dataframe["state"] == selected_state]

    if selected_county:
        filtered_dataframe = filtered_dataframe[filtered_dataframe["county"] == selected_county]

    return filtered_dataframe


def parse_uploaded_csv(contents):
    # Decode uploaded CSV and read it into a dataframe.
    if contents is None:
        return False, "Please upload a CSV file first.", None

    try:
        _, encoded_text = contents.split(",", 1)
        decoded_bytes = base64.b64decode(encoded_text)
        csv_text = decoded_bytes.decode("utf-8")
        dataframe = pd.read_csv(io.StringIO(csv_text))
        return True, "CSV loaded successfully.", dataframe
    except Exception as error:
        return False, f"Could not read the uploaded CSV file: {error}", None


def serve_layout():
    # Decide what screen to show when the app loads.
    starting_screen = choose_first_screen()

    if starting_screen == "setup_account":
        first_page = build_setup_account_layout()
    else:
        first_page = build_login_layout()

    return html.Div(
        [
            dcc.Store(id="logged_in_store", data=False),
            dcc.Store(id="screen_store", data=starting_screen),
            dcc.Store(id="current_user_store", data=None),
            dcc.Store(id="pending_setup_store", data=None),
            dcc.Store(id="pending_new_user_store", data=None),
            dcc.Store(id="uploaded_csv_store", data=None),
            dcc.Store(id="data_refresh_store", data=0),

            # Track whether the policy form is in add or edit mode.
            dcc.Store(id="policy_form_mode_store", data="add"),

            # Keep the original policy number for edits.
            dcc.Store(id="original_policy_number_store", data=None),

            # Both forms start closed.
            dcc.Store(id="policy_form_visible_store", data=False),
            dcc.Store(id="new_user_form_visible_store", data=False),

            html.Div(id="page_content", children=first_page)
        ]
    )


# Use function layout so it picks the right first screen.
app.layout = serve_layout


@app.callback(
    Output("screen_store", "data"),
    Output("pending_setup_store", "data"),
    Output("page_content", "children"),
    Input("create_account_button", "n_clicks"),
    State("setup_username", "value"),
    State("setup_password", "value"),
    State("setup_confirm_password", "value"),
    prevent_initial_call=True
)
def handle_first_account_creation(n_clicks, username, password, confirm_password):
    # Create first admin account.
    if not n_clicks:
        return no_update, no_update, no_update

    # Validate before creating.
    is_valid, validation_message = validate_new_user_form(username, password, confirm_password)

    if not is_valid:
        return "setup_account", None, build_setup_account_layout(validation_message)

    success, message, created_user = create_user_account(username, password, "admin")

    if not success:
        return "setup_account", None, build_setup_account_layout(message)

    # Move user to MFA setup if account creation worked.
    return (
        "verify_setup",
        created_user,
        build_verify_mfa_layout(
            created_user,
            "Admin account created. Scan the QR code and enter one valid MFA code to finish setup."
        )
    )


@app.callback(
    Output("screen_store", "data", allow_duplicate=True),
    Output("pending_setup_store", "data", allow_duplicate=True),
    Output("page_content", "children", allow_duplicate=True),
    Input("finish_setup_button", "n_clicks"),
    State("pending_setup_store", "data"),
    State("verify_mfa_code", "value"),
    prevent_initial_call=True
)
def handle_finish_first_setup(n_clicks, pending_setup_data, entered_code):
    # Finish MFA for the first account.
    if not n_clicks:
        return no_update, no_update, no_update

    if not pending_setup_data:
        return "setup_account", None, build_setup_account_layout(
            "Setup data was missing. Please create the admin account again."
        )

    if not entered_code:
        return (
            "verify_setup",
            pending_setup_data,
            build_verify_mfa_layout(pending_setup_data, "Please enter the 6-digit MFA code.")
        )

    success, message = verify_first_time_mfa_setup(
        username=pending_setup_data["username"],
        mfa_code=entered_code
    )

    if not success:
        return (
            "verify_setup",
            pending_setup_data,
            build_verify_mfa_layout(pending_setup_data, message)
        )

    # Send them to login after MFA is finished.
    return (
        "login",
        None,
        build_login_layout(
            "Setup complete. This is your admin account. Future users must be created from the dashboard after you log in."
        )
    )


@app.callback(
    Output("logged_in_store", "data"),
    Output("screen_store", "data", allow_duplicate=True),
    Output("current_user_store", "data"),
    Output("page_content", "children", allow_duplicate=True),
    Input("login_button", "n_clicks"),
    State("login_username", "value"),
    State("login_password", "value"),
    State("login_mfa_code", "value"),
    prevent_initial_call=True
)
def handle_login(n_clicks, username, password, mfa_code):
    # Normal login flow.
    if not n_clicks:
        return no_update, no_update, no_update, no_update

    success, message, current_user = authenticate_user_login(username, password, mfa_code)

    if success:
        return True, "dashboard", current_user, build_dashboard_layout(current_user)

    return False, "login", None, build_login_layout(message)


@app.callback(
    Output("logged_in_store", "data", allow_duplicate=True),
    Output("screen_store", "data", allow_duplicate=True),
    Output("current_user_store", "data", allow_duplicate=True),
    Output("page_content", "children", allow_duplicate=True),
    Input("logout_button", "n_clicks"),
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    # Log user out and send them back to login.
    if not n_clicks:
        return no_update, no_update, no_update, no_update

    return False, "login", None, build_login_layout("You have been logged out.")


@app.callback(
    Output("page_content", "children", allow_duplicate=True),
    Input("screen_store", "data"),
    State("current_user_store", "data"),
    prevent_initial_call=True
)
def rerender_page(screen_name, current_user):
    # Rebuild page if screen state changes.
    if screen_name == "dashboard" and current_user:
        return build_dashboard_layout(current_user)

    if screen_name == "login":
        return build_login_layout()

    if screen_name == "setup_account":
        return build_setup_account_layout()

    return no_update


@app.callback(
    Output("state_filter", "options"),
    Output("state_filter", "value"),
    Input("data_refresh_store", "data"),
    State("state_filter", "value")
)
def refresh_state_filter_options(refresh_count, current_state_value):
    # Refresh states after data changes.
    state_names = get_state_list()
    options = [{"label": state_name, "value": state_name} for state_name in state_names]

    # Keep current state if it still exists.
    if current_state_value in state_names:
        return options, current_state_value

    return options, None


@app.callback(
    Output("county_filter", "options"),
    Output("county_filter", "value"),
    Input("state_filter", "value"),
    Input("data_refresh_store", "data"),
    State("county_filter", "value")
)
def refresh_county_filter_options(selected_state, refresh_count, current_county_value):
    # Refresh county list when state or data changes.
    county_names = get_county_list(selected_state)
    options = [{"label": county_name, "value": county_name} for county_name in county_names]

    if current_county_value in county_names:
        return options, current_county_value

    return options, None


@app.callback(
    Output("uploaded_csv_store", "data"),
    Output("csv_import_message", "children"),
    Output("csv_import_message", "style"),
    Input("csv_upload", "contents"),
    State("current_user_store", "data"),
    prevent_initial_call=True
)
def store_uploaded_file(uploaded_contents, current_user):
    # Store uploaded file first. Import happens on button click.
    if not current_user or current_user["role"] != "admin":
        return no_update, "Only admin users can upload CSV files.", error_message_style()

    if uploaded_contents is None:
        return no_update, no_update, no_update

    return (
        uploaded_contents,
        "CSV uploaded. Click Import CSV to add the records to the database.",
        success_message_style()
    )


@app.callback(
    Output("csv_import_message", "children", allow_duplicate=True),
    Output("csv_import_message", "style", allow_duplicate=True),
    Output("data_refresh_store", "data"),
    Input("import_csv_button", "n_clicks"),
    State("uploaded_csv_store", "data"),
    State("current_user_store", "data"),
    State("data_refresh_store", "data"),
    prevent_initial_call=True
)
def handle_csv_import(n_clicks, uploaded_contents, current_user, refresh_count):
    # Import staged CSV into database.
    if not n_clicks:
        return no_update, no_update, no_update

    if not current_user or current_user["role"] != "admin":
        return "Only admin users can import CSV data.", error_message_style(), refresh_count

    is_loaded, load_message, uploaded_dataframe = parse_uploaded_csv(uploaded_contents)

    if not is_loaded:
        return load_message, error_message_style(), refresh_count

    success, import_message = import_policy_csv_dataframe(uploaded_dataframe)

    # Refresh dashboard pieces if import worked.
    if success:
        return import_message, success_message_style(), refresh_count + 1

    return import_message, error_message_style(), refresh_count


@app.callback(
    Output("new_user_form_visible_store", "data"),
    Input("show_new_user_form_button", "n_clicks"),
    Input("cancel_new_user_form_button", "n_clicks"),
    State("current_user_store", "data"),
    prevent_initial_call=True
)
def toggle_new_user_form(show_clicks, cancel_clicks, current_user):
    # Open or close create user form.
    if not current_user or current_user["role"] != "admin":
        return False

    trigger = ctx.triggered_id

    if trigger == "show_new_user_form_button":
        return True

    if trigger == "cancel_new_user_form_button":
        return False

    return no_update


@app.callback(
    Output("new_user_form_area", "style"),
    Input("new_user_form_visible_store", "data")
)
def update_new_user_form_visibility(is_visible):
    # Actually show or hide the user form.
    if is_visible:
        return visible_panel_style()

    return hidden_style()


@app.callback(
    Output("policy_form_visible_store", "data"),
    Output("policy_form_title", "children"),
    Output("policy_form_mode_store", "data"),
    Output("original_policy_number_store", "data"),
    Output("policy_number_input", "value"),
    Output("address_input", "value"),
    Output("city_input", "value"),
    Output("county_input", "value"),
    Output("state_input", "value"),
    Output("zip_input", "value"),
    Output("lat_input", "value"),
    Output("lon_input", "value"),
    Output("premium_input", "value"),
    Output("product_input", "value"),
    Output("phone_input", "value"),
    Output("email_input", "value"),
    Output("dwelling_coverage_input", "value"),
    Output("deductible_input", "value"),
    Output("policy_status_input", "value"),
    Output("policy_form_message", "children"),
    Output("policy_form_message", "style"),
    Output("table_action_message", "children"),
    Output("table_action_message", "style"),
    Input("show_add_policy_button", "n_clicks"),
    Input("show_edit_policy_button", "n_clicks"),
    Input("cancel_policy_form_button", "n_clicks"),
    State("policy_table", "selected_rows"),
    State("policy_table", "data"),
    State("current_user_store", "data"),
    prevent_initial_call=True
)
def manage_policy_form(show_add_clicks, show_edit_clicks, cancel_clicks, selected_rows, table_data, current_user):
    # Handle open/close state and preload policy values.
    if not current_user or current_user["role"] != "admin":
        return (
            False,
            "Add Policy",
            "add",
            None,
            *blank_policy_form_values(),
            "",
            neutral_message_style(),
            "",
            neutral_message_style()
        )

    trigger = ctx.triggered_id

    if trigger == "cancel_policy_form_button":
        # Close form and clear it out.
        return (
            False,
            "Add Policy",
            "add",
            None,
            *blank_policy_form_values(),
            "",
            neutral_message_style(),
            "",
            neutral_message_style()
        )

    if trigger == "show_add_policy_button":
        # Open a blank form in add mode.
        return (
            True,
            "Add Policy",
            "add",
            None,
            *blank_policy_form_values(),
            "",
            neutral_message_style(),
            "",
            neutral_message_style()
        )

    if trigger == "show_edit_policy_button":
        if not selected_rows:
            # Show message if user tries to edit without selecting a row.
            return (
                False,
                "Edit Policy",
                "edit",
                None,
                *blank_policy_form_values(),
                "",
                neutral_message_style(),
                "Please select a policy row first.",
                error_message_style()
            )

        selected_row = table_data[selected_rows[0]]

        # Open form in edit mode and preload selected row.
        return (
            True,
            "Edit Policy",
            "edit",
            selected_row["policy_number"],
            selected_row["policy_number"],
            selected_row["address"],
            selected_row["city"],
            selected_row["county"],
            selected_row["state"],
            selected_row["zip"],
            selected_row["lat"],
            selected_row["lon"],
            selected_row["premium"],
            selected_row["product"],
            selected_row["phone"],
            selected_row["email"],
            selected_row["dwelling_coverage"],
            selected_row["deductible"],
            selected_row["policy_status"],
            "",
            neutral_message_style(),
            "",
            neutral_message_style()
        )

    return no_update


@app.callback(
    Output("policy_form_area", "style"),
    Input("policy_form_visible_store", "data")
)
def update_policy_form_visibility(is_visible):
    # Actually show or hide policy form.
    if is_visible:
        return visible_panel_style()

    return hidden_style()


@app.callback(
    Output("policy_form_message", "children", allow_duplicate=True),
    Output("policy_form_message", "style", allow_duplicate=True),
    Output("table_action_message", "children", allow_duplicate=True),
    Output("table_action_message", "style", allow_duplicate=True),
    Output("data_refresh_store", "data", allow_duplicate=True),
    Input("save_policy_button", "n_clicks"),
    State("policy_form_mode_store", "data"),
    State("original_policy_number_store", "data"),
    State("current_user_store", "data"),
    State("data_refresh_store", "data"),
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
def handle_save_policy(
    n_clicks,
    form_mode,
    original_policy_number,
    current_user,
    refresh_count,
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
    # Save policy from form.
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update

    if not current_user or current_user["role"] != "admin":
        return "", neutral_message_style(), "Only admin users can save policy changes.", error_message_style(), refresh_count

    # Validate and clean policy fields first.
    is_valid, message, cleaned_policy = validate_policy_form(
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
        return message, error_message_style(), "", neutral_message_style(), refresh_count

    # Update existing record in edit mode, otherwise add a new one.
    if form_mode == "edit" and original_policy_number:
        success, database_message = update_policy_record(original_policy_number, cleaned_policy)
    else:
        success, database_message = add_policy_record(cleaned_policy)

    if success:
        return database_message, success_message_style(), "", neutral_message_style(), refresh_count + 1

    return database_message, error_message_style(), "", neutral_message_style(), refresh_count


@app.callback(
    Output("table_action_message", "children", allow_duplicate=True),
    Output("table_action_message", "style", allow_duplicate=True),
    Output("data_refresh_store", "data", allow_duplicate=True),
    Input("delete_selected_policy_button", "n_clicks"),
    State("policy_table", "selected_rows"),
    State("policy_table", "data"),
    State("current_user_store", "data"),
    State("data_refresh_store", "data"),
    prevent_initial_call=True
)
def handle_delete_policy(n_clicks, selected_rows, table_data, current_user, refresh_count):
    # Delete selected policy from table.
    if not n_clicks:
        return no_update, no_update, no_update

    if not current_user or current_user["role"] != "admin":
        return "Only admin users can delete policy records.", error_message_style(), refresh_count

    if not selected_rows:
        return "Please select a policy row first.", error_message_style(), refresh_count

    selected_row = table_data[selected_rows[0]]
    success, message = delete_policy_record(selected_row["policy_number"])

    if success:
        return message, success_message_style(), refresh_count + 1

    return message, error_message_style(), refresh_count


@app.callback(
    Output("policy_table", "data"),
    Output("policy_table", "columns"),
    Output("summary_chart", "figure"),
    Output("map_layers", "children"),
    Input("state_filter", "value"),
    Input("county_filter", "value"),
    Input("analysis_type", "value"),
    Input("data_refresh_store", "data")
)
def refresh_dashboard_data(selected_state, selected_county, analysis_type, refresh_count):
    # Refresh table, chart, and map together.
    dataframe = load_dashboard_data()
    filtered_dataframe = filter_policy_dataframe(dataframe, selected_state, selected_county)

    table_columns = [{"name": column_name, "id": column_name} for column_name in filtered_dataframe.columns]
    chart_figure = build_summary_chart(filtered_dataframe, analysis_type)
    map_layers = build_map_layers(filtered_dataframe)

    return filtered_dataframe.to_dict("records"), table_columns, chart_figure, map_layers


@app.callback(
    Output("pending_new_user_store", "data"),
    Output("create_new_user_message", "children"),
    Output("create_new_user_message", "style"),
    Output("new_user_mfa_panel", "children"),
    Output("data_refresh_store", "data", allow_duplicate=True),
    Input("create_new_user_button", "n_clicks"),
    State("current_user_store", "data"),
    State("data_refresh_store", "data"),
    State("new_user_username", "value"),
    State("new_user_password", "value"),
    State("new_user_confirm_password", "value"),
    State("new_user_role", "value"),
    prevent_initial_call=True
)
def handle_create_new_user(
    n_clicks,
    current_user,
    refresh_count,
    username,
    password,
    confirm_password,
    role
):
    # Create new user from admin panel.
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update

    if not current_user or current_user["role"] != "admin":
        return None, "Only admin users can create new users.", error_message_style(), "", refresh_count

    is_valid, validation_message = validate_new_user_form(username, password, confirm_password)
    if not is_valid:
        return None, validation_message, error_message_style(), "", refresh_count

    success, message, created_user = create_user_account(username, password, role)

    if not success:
        return None, message, error_message_style(), "", refresh_count

    # Build MFA section for the new user.
    panel = build_new_user_mfa_panel(
        created_user,
        "New user created. Finish MFA setup below."
    )

    return created_user, message, success_message_style(), panel, refresh_count + 1


@app.callback(
    Output("pending_new_user_store", "data", allow_duplicate=True),
    Output("new_user_mfa_panel", "children", allow_duplicate=True),
    Output("data_refresh_store", "data", allow_duplicate=True),
    Input("finish_new_user_setup_button", "n_clicks"),
    State("pending_new_user_store", "data"),
    State("new_user_mfa_code", "value"),
    State("data_refresh_store", "data"),
    prevent_initial_call=True
)
def handle_finish_new_user_setup(n_clicks, pending_new_user, entered_code, refresh_count):
    # Finish MFA for newly created user.
    if not n_clicks:
        return no_update, no_update, no_update

    if not pending_new_user:
        return None, html.Div("No pending user setup found."), refresh_count

    if not entered_code:
        return (
            pending_new_user,
            build_new_user_mfa_panel(pending_new_user, "Please enter the 6-digit MFA code."),
            refresh_count
        )

    success, message = verify_first_time_mfa_setup(
        username=pending_new_user["username"],
        mfa_code=entered_code
    )

    if not success:
        return (
            pending_new_user,
            build_new_user_mfa_panel(pending_new_user, message),
            refresh_count
        )

    success_message = html.Div(
        f"MFA setup is complete for {pending_new_user['username']}.",
        style={"marginTop": "12px", "color": "green", "fontWeight": "bold"}
    )

    return None, success_message, refresh_count + 1


@app.callback(
    Output("user_table", "data"),
    Input("data_refresh_store", "data")
)
def refresh_user_table(refresh_count):
    # Refresh user table after changes.
    return list_users().to_dict("records")


if __name__ == "__main__":
    app.run(debug=True)