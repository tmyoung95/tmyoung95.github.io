"""
Tyler Young CS-499 Capstone
auth.py

This file handles the authentication logic for the application.
It is responsible for creating the users database, storing user
credentials, hashing and verifying passwords, generating MFA secrets
and QR codes, verifying MFA codes, and managing role information
for each user account.
"""

import base64
import io

import pyotp
import qrcode
from werkzeug.security import generate_password_hash, check_password_hash

from database import (
    get_user_by_username,
    insert_new_user,
    mark_user_setup_complete
)


# Generate a unique MFA secret for a user
def generate_mfa_secret():
    return pyotp.random_base32()


# Build the MFA setup URI for the authenticator app.
def build_mfa_uri(username, mfa_secret):
    totp = pyotp.TOTP(mfa_secret)
    return totp.provisioning_uri(
        name=username,
        issuer_name="InsuranceDashboard"
    )


# Turn the MFA setup URI into a QR code image and convert it to base64
def build_mfa_qr_code_base64(username, mfa_secret):
    # First build the URI that the authenticator app needs.
    mfa_uri = build_mfa_uri(username, mfa_secret)

    # Create a QR code 
    qr_image = qrcode.make(mfa_uri)

    # Store the image in memory
    image_buffer = io.BytesIO()
    qr_image.save(image_buffer, format="PNG")

    # Convert the image bytes into base64 text 
    return base64.b64encode(image_buffer.getvalue()).decode("utf-8")


# Create a new user account by cleaning the inputs, checking for duplicate usernames,
# hashing the password, generating an MFA secret, and saving the new user to the database.
def create_user_account(username, password, role):
    # Clean the input values first so extra spaces do not cause bad saved data.
    cleaned_username = str(username).strip()
    cleaned_password = str(password).strip()
    cleaned_role = str(role).strip()

    # Check whether the username is already in use before creating the account.
    existing_user = get_user_by_username(cleaned_username)
    if existing_user is not None:
        return False, "That username is already taken.", None

    # Hash the password so the real password is never stored verbatum
    password_hash = generate_password_hash(cleaned_password)

    # Generate the MFA secret that will be used during login and setup.
    mfa_secret = generate_mfa_secret()

    # Save the new user record in the database.
    insert_new_user(
        username=cleaned_username,
        password_hash=password_hash,
        mfa_secret=mfa_secret,
        role=cleaned_role
    )

    # Return the new user details needed for the MFA setup step.
    created_user = {
        "username": cleaned_username,
        "mfa_secret": mfa_secret,
        "role": cleaned_role
    }

    return True, "Account created successfully.", created_user


# Check whether the MFA code entered by the user matches the current authenticator code.
def verify_totp_code(mfa_secret, mfa_code):
    # Clean the code first in case the user entered extra spaces.
    cleaned_code = str(mfa_code).strip()

    # Build a TOTP object from the user's MFA secret and verify the code.
    totp = pyotp.TOTP(mfa_secret)
    return totp.verify(cleaned_code)


# Finish first-time MFA setup by checking the entered code and marking the user as setup complete.
def verify_first_time_mfa_setup(username, mfa_code):
    # Clean the username before looking it up in the database.
    cleaned_username = str(username).strip()

    # Load the user record 
    user_record = get_user_by_username(cleaned_username)
    if user_record is None:
        return False, "Could not find that user account."

    # Stop here if the MFA code is not valid for this user's secret.
    if not verify_totp_code(user_record["mfa_secret"], mfa_code):
        return False, "That MFA code was not valid. Please try again."

    # Mark the account as fully set up once MFA has been confirmed.
    mark_user_setup_complete(cleaned_username)
    return True, "MFA setup complete."


# Log a user in by checking that all fields were entered correctly

def authenticate_user_login(username, password, mfa_code):
    # Clean all login values first so blank spaces do not interfere with validation.
    cleaned_username = str(username or "").strip()
    cleaned_password = str(password or "").strip()
    cleaned_code = str(mfa_code or "").strip()

    # Make sure the user filled out all required login fields.
    if cleaned_username == "" or cleaned_password == "" or cleaned_code == "":
        return False, "Please enter username, password, and MFA code.", None

    # Look up the user account by username.
    user_record = get_user_by_username(cleaned_username)
    if user_record is None:
        return False, "Invalid username or password.", None

    # Do not allow login until the user has completed the MFA setup process.
    if user_record["setup_complete"] != 1:
        return False, "This account has not finished MFA setup yet.", None

    # Compare the entered password against the stored password hash.
    if not check_password_hash(user_record["password_hash"], cleaned_password):
        return False, "Invalid username or password.", None

    # Verify the MFA code as the final login check.
    if not verify_totp_code(user_record["mfa_secret"], cleaned_code):
        return False, "Invalid MFA code.", None

    # Build the user object that the app stores after a successful login.
    current_user = {
        "username": user_record["username"],
        "role": user_record["role"]
    }

    return True, "Login successful.", current_user