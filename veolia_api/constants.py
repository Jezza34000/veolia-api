"""Constants for the Veolia API."""

from enum import Enum

# URLS
LOGIN_URL = "https://cognito-idp.eu-west-3.amazonaws.com"
BACKEND_ISTEFR = "https://prd-ael-sirius-backend.istefr.fr"

# AUTH
LOGIN_CLIENT_ID = "3kghade1fg54739kj8pkbova8j"

# API Flow Endpoints
CALLBACK_ENDPOINT = "/callback"

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
