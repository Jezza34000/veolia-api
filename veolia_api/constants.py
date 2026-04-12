"""Constants for the Veolia API."""

from enum import Enum

from .portals import VEOLIA_PORTAL_CLIENTS

# URLS
LOGIN_URL = "https://cognito-idp.eu-west-3.amazonaws.com"
BACKEND_ISTEFR = "https://prd-ael-sirius-backend.istefr.fr"

# Backward-compatibility alias / by default 1st entry
LOGIN_CLIENT_ID = next(iter(VEOLIA_PORTAL_CLIENTS.values()))

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
