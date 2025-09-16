"""Constants for the Veolia API."""

from enum import Enum
from http import HTTPStatus

# URLS
LOGIN_URL = "https://login.eau.veolia.fr"
BASE_URL = "https://www.eau.veolia.fr"
BACKEND_ISTEFR = "https://prd-ael-sirius-backend.istefr.fr"

# AUTH
CLIENT_ID = "tHBtoPOLiI2NSbCzqYz6pydZ1Xil0Bw2"
CODE_CHALLENGE_METHODE = "S256"

# API Flow Endpoints
OAUTH_TOKEN = "/oauth/token"
AUTHORIZE_ENDPOINT = "/authorize"
AUTHORIZE_RESUME_ENDPOINT = "/authorize/resume"
CALLBACK_ENDPOINT = "/callback"

LOGIN_IDENTIFIER_ENDPOINT = "/u/login/identifier"
LOGIN_PASSWORD_ENDPOINT = "/u/login/password"
MFA_DETECT_BROWSER_CAPABILITIES_ENDPOINT = "/u/mfa-detect-browser-capabilities"
MFA_WEBAUTHN_PLATFORM_ENROLLMENT_ENDPOINT = "/u/mfa-webauthn-platform-enrollment"
MFA_WEBAUTHN_PLATFORM_CHALLENGE_ENDPOINT = "/u/mfa-webauthn-platform-challenge"
MFA_WEBAUTHN_PLATFORM_ENROL_ERR_ENDPOINT = "/u/mfa-webauthn-platform-error-enrollment"

TYPE_FRONT = "WEB_ORDINATEUR"

# HTTP Methods
GET = "GET"
POST = "POST"

# Session
TIMEOUT = 15

# API Connection flow
API_CONNECTION_FLOW = {
    AUTHORIZE_ENDPOINT: {
        "method": GET,
        "params": None,
        "success_status": HTTPStatus.FOUND,
    },
    LOGIN_IDENTIFIER_ENDPOINT: {
        "method": POST,
        "params": lambda state, username: {
            "username": username,
            "js-available": "true",
            "webauthn-available": "true",
            "is-brave": "false",
            "webauthn-platform-available": "true",
            "action": "default",
            "state": state,
        },
        "success_status": HTTPStatus.FOUND,
    },
    LOGIN_PASSWORD_ENDPOINT: {
        "method": POST,
        "params": lambda state, username, password: {
            "username": username,
            "password": password,
            "action": "default",
            "state": state,
        },
        "success_status": HTTPStatus.FOUND,
    },
    AUTHORIZE_RESUME_ENDPOINT: {
        "method": GET,
        "params": None,
        "success_status": HTTPStatus.FOUND,
    },
    MFA_DETECT_BROWSER_CAPABILITIES_ENDPOINT: {
        "method": POST,
        "params": lambda state: {
            "js-available": "true",
            "webauthn-available": "true",
            "is-brave": "false",
            "webauthn-platform-available": "true",
            "action": "default",
            "state": state,
        },
        "success_status": HTTPStatus.FOUND,
    },
    MFA_WEBAUTHN_PLATFORM_ENROLLMENT_ENDPOINT: {
        "method": POST,
        "params": lambda state: {
            "action": "refuse-add-device",
            "state": state,
        },
        "success_status": HTTPStatus.FOUND,
    },
    CALLBACK_ENDPOINT: {
        "method": GET,
        "params": lambda state, code: {
            "code": code,
            "state": state,
        },
        "success_status": HTTPStatus.OK,
    },
}


class ConsumptionType(Enum):
    """Consumption type."""

    MONTHLY = "monthly"
    YEARLY = "yearly"
