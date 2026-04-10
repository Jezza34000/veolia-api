"""
Community-contributed Veolia portal instances.

To add support for your portal, add an entry here:
    "your-portal-hostname.veolia.fr": "your-cognito-client-id"

The client_id can be found in the network traffic when logging in to your portal.
"""

VEOLIA_PORTAL_CLIENTS: dict[str, str] = {
    "eau.veolia.fr": "3kghade1fg54739kj8pkbova8j",
    "eaudetm.monespace.eau.veolia.fr": "19bjc8ldefie683n889iiubjc8", # Eau de Toulouse Métropole
}
