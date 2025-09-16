"""Custom exception classes for Veolia API errors"""


class VeoliaAPIError(Exception):
    """Custom exception class for Veolia API errors"""


class VeoliaAPIInvalidCredentialsError(VeoliaAPIError):
    """Custom exception class for Veolia API missing credentials"""


class VeoliaAPIAuthError(VeoliaAPIError):
    """Custom exception class for Veolia API authentication errors"""


class VeoliaAPIFlowError(VeoliaAPIError):
    """Custom exception class for Veolia API connection errors"""


class VeoliaAPIAuthCodeNotFoundError(VeoliaAPIError):
    """Custom exception class for Veolia API parsing errors"""


class VeoliaAPIUnexpectedResponseError(VeoliaAPIError):
    """Custom exception class for Veolia API connection errors"""


class VeoliaAPITokenError(VeoliaAPIError):
    """Custom exception class for Veolia API rate limit errors"""


class VeoliaAPIResponseError(VeoliaAPIError):
    """Custom exception class for Veolia API response errors"""


class VeoliaAPIGetDataError(VeoliaAPIError):
    """Custom exception class for Veolia API connection errors"""


class VeoliaAPISetDataError(VeoliaAPIError):
    """Custom exception class for Veolia API connection errors"""


class VeoliaAPIUnknownError(VeoliaAPIError):
    """Custom exception class for Veolia API unknown errors"""


class VeoliaAPIRateLimitError(VeoliaAPIError):
    """Exception for HTTP 429 Too Many Requests."""
