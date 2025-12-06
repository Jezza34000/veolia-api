"""Constants for the Veolia API."""

from enum import Enum

# URLS
LOGIN_URL = "https://login.eau.veolia.fr"
NEW_LOGIN_URL = "https://cognito-idp.eu-west-3.amazonaws.com"
BASE_URL = "https://www.eau.veolia.fr"
BACKEND_ISTEFR = "https://prd-ael-sirius-backend.istefr.fr"

# AUTH
LOGIN_CLIENT_ID = "3kghade1fg54739kj8pkbova8j"

# API Flow Endpoints
AUTHORIZE_RESUME_ENDPOINT = "/authorize/resume"
CALLBACK_ENDPOINT = "/callback"

LOGIN_PASSWORD_ENDPOINT = "/u/login/password"
MFA_DETECT_BROWSER_CAPABILITIES_ENDPOINT = "/u/mfa-detect-browser-capabilities"
MFA_WEBAUTHN_PLATFORM_ENROLLMENT_ENDPOINT = "/u/mfa-webauthn-platform-enrollment"
MFA_WEBAUTHN_PLATFORM_CHALLENGE_ENDPOINT = "/u/mfa-webauthn-platform-challenge"
MFA_WEBAUTHN_PLATFORM_ENROL_ERR_ENDPOINT = "/u/mfa-webauthn-platform-error-enrollment"

TYPE_FRONT = "WEB_ORDINATEUR"

# HTTP Methods
GET = "GET"
POST = "POST"

# AsyncIO HTTP/Session
TIMEOUT = 15
CONCURRENTS_TASKS = 3


class ConsumptionType(Enum):
    """Consumption type."""

    MONTHLY = "monthly"
    YEARLY = "yearly"
