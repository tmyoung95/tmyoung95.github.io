"""
Tyler Young CS-499 Capstone
validation.py

This file handles all input validation and data cleaning for the Insurance Exposure Dashboard.
It ensures that user input is properly formatted and meets required rules before being
processed or stored in the database.

It includes helper functions for cleaning text, checking for blank values, and validating
common fields such as email addresses, phone numbers, and ZIP codes. It also provides
functions for safely converting values into numeric types and ensuring that values like
premium, coverage, and deductible are non-negative.

For location data, it validates that latitude and longitude values fall within real-world
ranges so mapping and distance calculations work correctly.

Additionally, this file contains the main validation logic for both user account creation
and policy form submission. It checks required fields, enforces password rules, and ensures
all policy data is valid before returning a cleaned version of the data that can be safely
saved to the database. This helps prevent errors and keeps the application data consistent.
"""

import re


def clean_text(value):
    # Turn whatever came in into a trimmed string.
    if value is None:
        return ""
    return str(value).strip()


def is_blank(value):
    # Small helper for required field checks.
    return clean_text(value) == ""


def is_valid_email(email_value):
    # Basic email check.
    email_text = clean_text(email_value)
    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(email_pattern, email_text) is not None


def is_valid_phone(phone_value):
    # Let people type spaces, dashes, or parentheses.
    phone_text = clean_text(phone_value)
    digits_only = re.sub(r"\D", "", phone_text)
    return 10 <= len(digits_only) <= 15


def is_valid_zip(zip_value):
    # Allow normal ZIP and ZIP+4.
    zip_text = clean_text(zip_value)
    zip_pattern = r"^\d{5}(-\d{4})?$"
    return re.match(zip_pattern, zip_text) is not None


def parse_float(value, field_name):
    # Try to turn text into a number and return an error if that fails.
    text_value = clean_text(value)

    try:
        return True, float(text_value), ""
    except ValueError:
        return False, None, f"{field_name} must be a number."


def parse_non_negative_float(value, field_name):
    # Same as parse_float, but rejects negative values.
    is_valid, parsed_value, error_message = parse_float(value, field_name)

    if not is_valid:
        return False, None, error_message

    if parsed_value < 0:
        return False, None, f"{field_name} cannot be negative."

    return True, parsed_value, ""


def validate_latitude(latitude_value):
    # Latitude must stay inside real-world bounds.
    is_valid, parsed_value, error_message = parse_float(latitude_value, "Latitude")

    if not is_valid:
        return False, None, error_message

    if parsed_value < -90 or parsed_value > 90:
        return False, None, "Latitude must be between -90 and 90."

    return True, parsed_value, ""


def validate_longitude(longitude_value):
    # Longitude must stay inside real-world bounds.
    is_valid, parsed_value, error_message = parse_float(longitude_value, "Longitude")

    if not is_valid:
        return False, None, error_message

    if parsed_value < -180 or parsed_value > 180:
        return False, None, "Longitude must be between -180 and 180."

    return True, parsed_value, ""


def validate_new_user_form(username, password, confirm_password):
    # Validate account creation fields.
    cleaned_username = clean_text(username)
    cleaned_password = clean_text(password)
    cleaned_confirm_password = clean_text(confirm_password)

    if cleaned_username == "":
        return False, "Username is required."

    if cleaned_password == "":
        return False, "Password is required."

    if len(cleaned_password) < 8:
        return False, "Password must be at least 8 characters long."

    if cleaned_password != cleaned_confirm_password:
        return False, "Passwords do not match."

    return True, "User form looks good."


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
    # Validate the policy form and return cleaned data ready for the database.
    required_text_fields = {
        "Policy Number": policy_number,
        "Address": address,
        "City": city,
        "County": county,
        "State": state,
        "ZIP Code": zip_code,
        "Product": product,
        "Phone": phone,
        "Email": email,
        "Policy Status": policy_status
    }

    for field_name, field_value in required_text_fields.items():
        if is_blank(field_value):
            return False, f"{field_name} is required.", None

    if not is_valid_zip(zip_code):
        return False, "ZIP Code must be 5 digits or ZIP+4.", None

    if not is_valid_email(email):
        return False, "Email format is invalid.", None

    if not is_valid_phone(phone):
        return False, "Phone number format is invalid.", None

    latitude_ok, latitude_number, latitude_error = validate_latitude(latitude)
    if not latitude_ok:
        return False, latitude_error, None

    longitude_ok, longitude_number, longitude_error = validate_longitude(longitude)
    if not longitude_ok:
        return False, longitude_error, None

    premium_ok, premium_number, premium_error = parse_non_negative_float(premium, "Premium")
    if not premium_ok:
        return False, premium_error, None

    coverage_ok, coverage_number, coverage_error = parse_non_negative_float(
        dwelling_coverage,
        "Dwelling Coverage"
    )
    if not coverage_ok:
        return False, coverage_error, None

    deductible_ok, deductible_number, deductible_error = parse_non_negative_float(
        deductible,
        "Deductible"
    )
    if not deductible_ok:
        return False, deductible_error, None

    cleaned_policy = {
        "policy_number": clean_text(policy_number),
        "address": clean_text(address),
        "city": clean_text(city),
        "county": clean_text(county),
        "state": clean_text(state).upper(),
        "zip": clean_text(zip_code),
        "lat": latitude_number,
        "lon": longitude_number,
        "premium": premium_number,
        "product": clean_text(product),
        "phone": clean_text(phone),
        "email": clean_text(email),
        "dwelling_coverage": coverage_number,
        "deductible": deductible_number,
        "policy_status": clean_text(policy_status)
    }

    return True, "Policy form looks good.", cleaned_policy