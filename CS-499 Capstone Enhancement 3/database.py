"""
Tyler Young CS-499 Capstone
database.py

This file manages all database functionality for the Insurance Exposure Dashboard.
It is responsible for creating and maintaining the SQLite database, including
both the users table and the policies table used throughout the application.

It handles all user-related operations such as retrieving user data, inserting
new users, checking setup completion, and updating MFA setup status. It also
provides functions for listing users so they can be displayed in the admin panel.

For policy data, this file supports loading, adding, updating, and deleting
records, as well as checking for duplicate policy numbers before insertion.
It also includes functionality for importing policy data from CSV files,
including cleaning column names, validating required fields, and skipping
duplicate records during import.

Additionally, it provides helper functions to generate state and county lists
based on existing policy data, allowing the dashboard filters to update dynamically.
This file acts as the main bridge between the application and the database,
ensuring data is stored consistently and accessed efficiently.
"""

import sqlite3
import pandas as pd

DATABASE_FILE = "policies.db"

# Mandatory policy data structure
REQUIRED_POLICY_COLUMNS = [
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
    "policy_status"
]


# Open a connection to the SQLite database file so other functions can run queries.
def get_connection():
    return sqlite3.connect(DATABASE_FILE)


# Create the main database tables if they do not already exist.
def initialize_database():
    with get_connection() as connection:
        cursor = connection.cursor()

        # Create the users table to store login details, MFA data, roles,
        # and whether the user has finished first-time setup.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                mfa_secret TEXT NOT NULL,
                role TEXT NOT NULL,
                setup_complete INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        # Create the policies table to store all policy records used by the dashboard.
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

        # Save the table creation changes to the database.
        connection.commit()


# Check whether at least one user has already finished setup.
def has_completed_user():
    with get_connection() as connection:
        row = connection.execute(
            "SELECT 1 FROM users WHERE setup_complete = 1 LIMIT 1"
        ).fetchone()

    return row is not None


# Look up one user by username and return the result
def get_user_by_username(username):
    with get_connection() as connection:
        # Return rows in a format that can be accessed by column name.
        connection.row_factory = sqlite3.Row

        # Pull the stored login, MFA, and role information for this user.
        row = connection.execute(
            """
            SELECT username, password_hash, mfa_secret, role, setup_complete
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

    # Return None if the username does not exist in the database.
    if row is None:
        return None

    # Convert the row into a normal dictionary before returning it.
    return {
        "username": row["username"],
        "password_hash": row["password_hash"],
        "mfa_secret": row["mfa_secret"],
        "role": row["role"],
        "setup_complete": row["setup_complete"]
    }


# Insert a brand-new user into the users table.
def insert_new_user(username, password_hash, mfa_secret, role):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (username, password_hash, mfa_secret, role, setup_complete)
            VALUES (?, ?, ?, ?, 0)
            """,
            (username, password_hash, mfa_secret, role)
        )

        # Save the new user record.
        connection.commit()


# Mark a user as fully set up after they enter a valid MFA code.
def mark_user_setup_complete(username):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET setup_complete = 1
            WHERE username = ?
            """,
            (username,)
        )

        # Save the setup status change.
        connection.commit()


# Load the user list for the admin table and sort it by username.
def list_users():
    with get_connection() as connection:
        query = """
            SELECT username, role, setup_complete
            FROM users
            ORDER BY username
        """
        return pd.read_sql_query(query, connection)


# Load all saved policy records into a DataFrame so the dashboard can use them.
def load_policy_data():
    with get_connection() as connection:
        query = "SELECT * FROM policies ORDER BY policy_number"
        return pd.read_sql_query(query, connection)


# Build the state dropdown list from the policy data currently in the database.
def get_state_list():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT DISTINCT state FROM policies ORDER BY state"
        ).fetchall()

    # Return only non-empty state values.
    return [row[0] for row in rows if row[0]]


# Build the county dropdown list.
# If a state is selected, only return counties that belong to that state.
def get_county_list(selected_state=None):
    with get_connection() as connection:
        if selected_state:
            rows = connection.execute(
                """
                SELECT DISTINCT county
                FROM policies
                WHERE state = ?
                ORDER BY county
                """,
                (selected_state,)
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT DISTINCT county FROM policies ORDER BY county"
            ).fetchall()

    # Return only non-empty county values.
    return [row[0] for row in rows if row[0]]


# Check whether a policy number already exists before trying to insert a new record.
def policy_number_exists(policy_number):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT 1 FROM policies WHERE policy_number = ?",
            (policy_number,)
        ).fetchone()

    return row is not None


# Add one new policy record to the database. Stop first if that policy number already exists so duplicates are not inserted.
def add_policy_record(policy_data):
    if policy_number_exists(policy_data["policy_number"]):
        return False, f"Policy {policy_data['policy_number']} already exists."

    with get_connection() as connection:
        connection.execute(
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

        # Save the new policy record.
        connection.commit()

    return True, f"Policy {policy_data['policy_number']} was added successfully."


# Update an existing policy record.
def update_policy_record(original_policy_number, policy_data):
    if original_policy_number != policy_data["policy_number"]:
        if policy_number_exists(policy_data["policy_number"]):
            return False, f"Policy {policy_data['policy_number']} already exists."

    with get_connection() as connection:
        cursor = connection.cursor()

        # Update every editable field for the selected policy record.
        cursor.execute(
            """
            UPDATE policies
            SET
                policy_number = ?,
                address = ?,
                city = ?,
                county = ?,
                state = ?,
                zip = ?,
                lat = ?,
                lon = ?,
                premium = ?,
                product = ?,
                phone = ?,
                email = ?,
                dwelling_coverage = ?,
                deductible = ?,
                policy_status = ?
            WHERE policy_number = ?
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
                policy_data["policy_status"],
                original_policy_number
            )
        )

        # Save the update.
        connection.commit()

        # If no row was updated, the original policy number was not found.
        if cursor.rowcount == 0:
            return False, "That policy could not be found."

    return True, f"Policy {policy_data['policy_number']} was updated successfully."


# Delete one policy record using its policy number.
def delete_policy_record(policy_number):
    with get_connection() as connection:
        cursor = connection.cursor()

        # Remove the matching policy from the table.
        cursor.execute(
            "DELETE FROM policies WHERE policy_number = ?",
            (policy_number,)
        )

        # Save the deletion.
        connection.commit()

        # If nothing was deleted, the policy was not found.
        if cursor.rowcount == 0:
            return False, "Selected policy could not be found."

    return True, f"Policy {policy_number} was deleted successfully."


# Clean up incoming CSV column names
def normalize_policy_dataframe(dataframe):

    # Work on a copy to prevent erros.
    cleaned_dataframe = dataframe.copy()

    # Clean column names by trimming spaces and making them lowercase.
    cleaned_dataframe.columns = [str(column).strip().lower() for column in cleaned_dataframe.columns]

    # Rename common alternate column names to the names the app expects.
    rename_map = {
        "zip_code": "zip",
        "latitude": "lat",
        "longitude": "lon"
    }

    return cleaned_dataframe.rename(columns=rename_map)


# Import policy records from an uploaded CSV file without deleting existing data.
def import_policy_csv_dataframe(dataframe):
    # First normalize the uploaded DataFrame so the column names match expected names.
    cleaned_dataframe = normalize_policy_dataframe(dataframe)

    # Check whether any required columns are missing before processing rows.
    missing_columns = [
        column_name
        for column_name in REQUIRED_POLICY_COLUMNS
        if column_name not in cleaned_dataframe.columns
    ]

    if missing_columns:
        return False, "The CSV is missing these required columns: " + ", ".join(missing_columns)

    # Track how many records were added and how many were skipped as duplicates.
    records_added = 0
    records_skipped = 0

    with get_connection() as connection:
        cursor = connection.cursor()

        # Go row by row through the uploaded CSV data.
        for _, row in cleaned_dataframe.iterrows():
            # Clean the policy number first because it is used as the duplicate check.
            policy_number = str(row["policy_number"]).strip()

            # Skip this row if the policy number is already in the database.
            existing_row = cursor.execute(
                "SELECT 1 FROM policies WHERE policy_number = ?",
                (policy_number,)
            ).fetchone()

            if existing_row is not None:
                records_skipped += 1
                continue

            # Insert the cleaned row values into the policies table.
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
                    str(row["policy_number"]).strip(),
                    str(row["address"]).strip(),
                    str(row["city"]).strip(),
                    str(row["county"]).strip(),
                    str(row["state"]).strip().upper(),
                    str(row["zip"]).strip(),
                    float(row["lat"]),
                    float(row["lon"]),
                    float(row["premium"]),
                    str(row["product"]).strip(),
                    str(row["phone"]).strip(),
                    str(row["email"]).strip(),
                    float(row["dwelling_coverage"]),
                    float(row["deductible"]),
                    str(row["policy_status"]).strip()
                )
            )

            # Count this row as successfully added.
            records_added += 1

        # Save all inserted rows at the end of the import.
        connection.commit()

    return True, (
        f"Import complete. Added {records_added} record(s). "
        f"Skipped {records_skipped} duplicate record(s)."
    )