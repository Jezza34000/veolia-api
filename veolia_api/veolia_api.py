"""Veolia API client"""

import asyncio
import base64
import hashlib
import itertools
import logging
import os
import re
from collections.abc import Coroutine, Iterator
from datetime import UTC, date, datetime, timedelta
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from veolia_api.exceptions import (
    VeoliaAPIAuthCodeNotFoundError,
    VeoliaAPIAuthError,
    VeoliaAPIFlowError,
    VeoliaAPIGetDataError,
    VeoliaAPIInvalidCredentialsError,
    VeoliaAPIRateLimitError,
    VeoliaAPIResponseError,
    VeoliaAPISetDataError,
    VeoliaAPITokenError,
    VeoliaAPIUnexpectedResponseError,
)

from .constants import (
    API_CONNECTION_FLOW,
    AUTHORIZE_ENDPOINT,
    BACKEND_ISTEFR,
    BASE_URL,
    CALLBACK_ENDPOINT,
    CLIENT_ID,
    CODE_CHALLENGE_METHODE,
    CONCURRENTS_TASKS,
    GET,
    LOGIN_IDENTIFIER_ENDPOINT,
    LOGIN_PASSWORD_ENDPOINT,
    LOGIN_URL,
    OAUTH_TOKEN,
    POST,
    TIMEOUT,
    TYPE_FRONT,
    ConsumptionType,
)
from .model import AlertSettings, VeoliaAccountData

_LOGGER = logging.getLogger(__name__)


class VeoliaAPI:
    """Veolia API client"""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the Veolia API client"""
        self.username = username
        self.password = password
        self.account_data = VeoliaAccountData()
        self.api_flow = API_CONNECTION_FLOW
        self.session = session or aiohttp.ClientSession(timeout=TIMEOUT)

    @staticmethod
    def _base64_url_encode(data: bytes) -> str:
        """Base64 URL encode the data"""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    @staticmethod
    def _sha256(data: bytes) -> bytes:
        """Calculate the SHA-256 hash of the data"""
        return hashlib.sha256(data).digest()

    def _get_authorize_params(self, state: str | None) -> dict:
        """Get the parameters for the /authorize API call"""
        state = self._base64_url_encode(os.urandom(32))
        nonce = self._base64_url_encode(os.urandom(32))
        verifier = self._base64_url_encode(os.urandom(32))
        challenge = self._base64_url_encode(self._sha256(verifier.encode("utf-8")))
        self.account_data.verifier = verifier
        return {
            "audience": BACKEND_ISTEFR,
            "redirect_uri": f"{BASE_URL}{CALLBACK_ENDPOINT}",
            "client_id": CLIENT_ID,
            "scope": "openid profile email offline_access",
            "response_type": "code",
            "state": state,
            "nonce": nonce,
            "response_mode": "query",
            "code_challenge": challenge,
            "code_challenge_method": CODE_CHALLENGE_METHODE,
            "auth0Client": self._base64_url_encode(
                b'{"name": "auth0-react", "version": "1.11.0"}',
            ),
        }

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        retry=retry_if_exception_type((aiohttp.ClientError, VeoliaAPIRateLimitError)),
    )
    async def _send_request(
        self,
        url: str,
        method: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> aiohttp.ClientResponse:
        """Make an HTTP request with support for params, headers and JSON body."""
        safe_params = {**params} if params else {}
        if "password" in safe_params:
            safe_params["password"] = "REDACTED"

        req_headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
        }

        if self.account_data.access_token:
            req_headers["Authorization"] = f"Bearer {self.account_data.access_token}"

        if method == POST:
            req_headers["Content-Type"] = "application/json"

        _LOGGER.debug(
            "Making %s request to %s with params: %s, headers: %s, json: %s",
            method,
            url,
            safe_params,
            req_headers,
            json_data,
        )

        kwargs: dict = {"headers": req_headers, "allow_redirects": False}

        if params:
            kwargs["params"] = params

        if json_data is not None:
            req_headers["Content-Type"] = "application/json"
            kwargs["json"] = json_data

        elif method.upper() == POST and params:
            req_headers.update(
                {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Cache-Control": "no-cache",
                },
            )
            kwargs["data"] = urlencode(params)

        response = await self.session.request(method.upper(), url, **kwargs)
        _LOGGER.debug("Received response with status code %s", response.status)
        if response.status == HTTPStatus.TOO_MANY_REQUESTS:
            _LOGGER.warning(
                "Rate limit hit (HTTP 429) for %s %s, retrying...",
                method,
                url,
            )
            raise VeoliaAPIRateLimitError("HTTP 429 Too Many Requests")

        return response

    async def _execute_flow(self) -> None:
        """Execute the login flow"""
        next_url = AUTHORIZE_ENDPOINT
        state = None

        while next_url:
            config = self.api_flow.get(next_url, None)

            if config is None:
                raise VeoliaAPIFlowError(
                    f"Flow error on URL : {next_url}",
                )

            full_url = self._get_full_url(next_url)
            params = self._get_params(next_url, config, state)

            if state:
                full_url = f"{full_url}?state={state}"

            response = await self._send_request(
                url=full_url,
                method=config.get("method", GET),
                params=params,
            )
            next_url, state = self._handle_response(response, next_url, state, full_url)

    @staticmethod
    def _get_full_url(next_url: str) -> str:
        """Get the full URL for the next API call"""
        return (
            f"{LOGIN_URL}{next_url}"
            if next_url != CALLBACK_ENDPOINT
            else f"{BASE_URL}{next_url}"
        )

    def _get_params(
        self,
        next_url: str,
        config: dict,
        current_state: str | None,
    ) -> dict:
        """Get the parameters for the next API call"""
        param_functions = {
            AUTHORIZE_ENDPOINT: lambda state: self._get_authorize_params(state),
            LOGIN_IDENTIFIER_ENDPOINT: lambda state: config["params"](
                state,
                self.username,
            ),
            LOGIN_PASSWORD_ENDPOINT: lambda state: config["params"](
                state,
                self.username,
                self.password,
            ),
            CALLBACK_ENDPOINT: lambda state: config["params"](
                state,
                self.account_data.code,
            ),
        }
        return param_functions.get(
            next_url,
            lambda state: config["params"](state) if config["params"] else {},
        )(current_state)

    def _handle_response(
        self,
        response: aiohttp.ClientResponse,
        next_url: str,
        state: str | None,
        full_url: str,
    ) -> tuple:
        """Handle the response from the API call"""
        if (
            response.status == HTTPStatus.BAD_REQUEST
            and next_url == LOGIN_PASSWORD_ENDPOINT
        ):
            raise VeoliaAPIAuthError("Invalid username or password")
        if response.status != self.api_flow[next_url]["success_status"]:
            raise VeoliaAPIFlowError(
                f"Call to= {full_url} failed with status= {response.status}",
            )

        if response.status == HTTPStatus.FOUND:
            redirect_url = urlparse(response.headers.get("Location"))
            next_url = redirect_url.path
            new_state = parse_qs(redirect_url.query).get("state")
            if new_state:
                state = new_state[0]

            if next_url == CALLBACK_ENDPOINT:
                self.account_data.code = parse_qs(redirect_url.query).get(
                    "code",
                    [None],
                )[0]
                if not self.account_data.code:
                    raise VeoliaAPIAuthCodeNotFoundError("Authorization code not found")
                _LOGGER.debug("Authorization code received")
        elif response.status == HTTPStatus.OK and next_url == CALLBACK_ENDPOINT:
            next_url = None
        else:
            raise VeoliaAPIUnexpectedResponseError(
                f"Unexpected http status code: {response.status} at {full_url}",
            )

        return next_url, state

    async def login(self) -> bool:
        """Login to the Veolia API"""
        _LOGGER.info("Logging in...")
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

        if not self.username or not self.password:
            raise VeoliaAPIInvalidCredentialsError("Missing username or password")
        if not re.match(email_regex, self.username):
            raise VeoliaAPIInvalidCredentialsError("Invalid email format")
        _LOGGER.debug("Starting login process...")
        await self._execute_flow()
        await self._get_access_token()
        await self._get_client_data()

        # Check if login was successful
        if (
            self.account_data.access_token
            and self.account_data.id_abonnement
            and self.account_data.numero_pds
            and self.account_data.contact_id
            and self.account_data.tiers_id
            and self.account_data.numero_compteur
            and self.account_data.date_debut_abonnement
        ):
            _LOGGER.info("Login successful")
            return True
        return False

    async def _check_token(self) -> None:
        """Check if the access token is still valid"""
        if (
            not self.account_data.access_token
            or datetime.now().timestamp() >= self.account_data.token_expiration
        ):
            _LOGGER.debug("No access token or token expired")
            await self.login()

    async def _get_access_token(self) -> None:
        """Request the access token"""
        token_url = f"{LOGIN_URL}{OAUTH_TOKEN}"
        _LOGGER.debug("Requesting access token...")
        json_payload = {
            "client_id": CLIENT_ID,
            "grant_type": "authorization_code",
            "code_verifier": self.account_data.verifier,
            "code": self.account_data.code,
            "redirect_uri": f"{BASE_URL}{CALLBACK_ENDPOINT}",
        }

        response = await self._send_request(
            url=token_url,
            method=POST,
            json_data=json_payload,
        )

        if response.status != HTTPStatus.OK:
            raise VeoliaAPITokenError("Token API call error")

        token_data = await response.json()
        self.account_data.access_token = token_data.get("access_token")
        if not self.account_data.access_token:
            raise VeoliaAPITokenError("Access token not found")
        self.account_data.token_expiration = (
            datetime.now() + timedelta(seconds=token_data.get("expires_in", 0))
        ).timestamp()
        _LOGGER.debug("OK - Access token retrieved")

    async def _get_client_data(self) -> None:
        """Get the account data"""
        _LOGGER.debug("Fetching user & billing data...")
        url = f"{BACKEND_ISTEFR}/espace-client?type-front={TYPE_FRONT}"
        response = await self._send_request(url=url, method=GET)
        if response.status != HTTPStatus.OK:
            raise VeoliaAPIGetDataError(
                f"call to= espace-client failed with http status= {response.status}",
            )

        userdata = await response.json()
        self.account_data.id_abonnement = (
            userdata.get("contacts", None)[0]
            .get("tiers", None)[0]
            .get("abonnements", None)[0]
            .get("id_abonnement", None)
        )
        self.account_data.tiers_id = (
            userdata.get("contacts", None)[0].get("tiers", None)[0].get("id", None)
        )
        self.account_data.contact_id = userdata.get("contacts", None)[0].get(
            "id_contact",
            None,
        )
        self.account_data.numero_compteur = (
            userdata.get("contacts", None)[0]
            .get("tiers", None)[0]
            .get("abonnements", None)[0]
            .get("numero_compteur", None)
        )
        if (
            not self.account_data.id_abonnement
            or not self.account_data.tiers_id
            or not self.account_data.contact_id
            or not self.account_data.numero_compteur
        ):
            raise VeoliaAPIResponseError("Some user data not found in the response")
        _LOGGER.debug("OK - Fetch done for user & billing data")

        # Facturation request
        url_facturation = f"{BACKEND_ISTEFR}/abonnements/{self.account_data.id_abonnement}/facturation"
        response_facturation = await self._send_request(url=url_facturation, method=GET)
        if response_facturation.status != HTTPStatus.OK:
            raise VeoliaAPIGetDataError(
                f"call to= facturation failed with http status= {response_facturation.status}",
            )

        facturation_data = await response_facturation.json()
        self.account_data.numero_pds = facturation_data.get("numero_pds")
        if not self.account_data.numero_pds:
            raise VeoliaAPIResponseError("numero_pds not found in the response")

        self.account_data.date_debut_abonnement = facturation_data.get(
            "date_debut_abonnement",
        )
        if not self.account_data.date_debut_abonnement:
            raise VeoliaAPIResponseError(
                "date_debut_abonnement not found in the response",
            )
        _LOGGER.debug("OK - Billing data received")

    async def _get_consumption_data(
        self,
        data_type: ConsumptionType,
        year: int,
        month: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get the water consumption data"""
        date_debut = datetime.strptime(
            self.account_data.date_debut_abonnement,
            "%Y-%m-%d",
        ).replace(tzinfo=UTC)
        if month is not None:
            requested_date = datetime(year, month, 1, tzinfo=UTC)
        else:
            requested_date = datetime(year, 1, 1, tzinfo=UTC)

        if requested_date < date_debut:
            _LOGGER.warning(
                "Requested data for %s-%s is before subscription start date %s. Request aborted.",
                year,
                month,
                self.account_data.date_debut_abonnement,
            )
            return []

        params = {
            "annee": year,
            "numero-pds": self.account_data.numero_pds,
            "date-debut-abonnement": self.account_data.date_debut_abonnement,
        }

        if data_type == ConsumptionType.MONTHLY and month is not None:
            params["mois"] = month
            endpoint = "journalieres"
            _LOGGER.debug(
                "Fetching daily consumption data for : %s-%s",
                year,
                month,
            )
        elif data_type == ConsumptionType.YEARLY:
            endpoint = "mensuelles"
            _LOGGER.debug("Fetching monthly consumption data for year : %s", year)
        else:
            raise ValueError("Invalid data type or missing month for monthly data")

        url = f"{BACKEND_ISTEFR}/consommations/{self.account_data.id_abonnement}/{endpoint}"

        response = await self._send_request(
            url=url,
            method=GET,
            params=params,
        )
        _LOGGER.debug("Received response with status code %s", response.status)
        if response.status != HTTPStatus.OK:
            raise VeoliaAPIGetDataError(
                f"call to= consommations failed with http status= {response.status}",
            )
        _LOGGER.debug("OK - Fetch done for %s-%s", year, month)
        return await response.json()

    async def get_alerts_settings(self) -> AlertSettings:
        """Get the consumption alerts
        Response example:
        {
            "seuils": {
                "journalier": {
                    "valeur": 100,
                    "unite": "L",
                    "moyen_contact": {
                        "souscrit_par_email": true,
                        "souscrit_par_mobile": true
                    }
                },
                "mensuel": {
                    "valeur": 5,
                    "unite": "M3",
                    "moyen_contact": {
                        "souscrit_par_email": true,
                        "souscrit_par_mobile": false
                    }
                }
            }
        }
        """
        await self._check_token()

        _LOGGER.debug("Fetching alerts settings...")
        params = {
            "abo_id": self.account_data.id_abonnement,
        }
        url = f"{BACKEND_ISTEFR}/alertes/{self.account_data.numero_pds}"
        response = await self._send_request(
            url=url,
            method=GET,
            params=params,
        )
        _LOGGER.debug("Received response with status code %s", response.status)

        if response.status == HTTPStatus.NO_CONTENT:
            _LOGGER.info("No alerts settings found")
            return AlertSettings(
                daily_enabled=False,
                daily_threshold=0,
                daily_notif_email=False,
                daily_notif_sms=False,
                monthly_enabled=False,
                monthly_threshold=0,
                monthly_notif_email=False,
                monthly_notif_sms=False,
            )

        if response.status == HTTPStatus.OK:
            data = await response.json()
            seuils = data.get("seuils", {})
            daily_alert = seuils.get("journalier", None)
            monthly_alert = seuils.get("mensuel", None)

            _LOGGER.debug("Alerts settings: %s", data)
            _LOGGER.debug("OK - Fetch done for alerts settings")

            return AlertSettings(
                daily_enabled=bool(daily_alert),
                daily_threshold=daily_alert["valeur"] if daily_alert else None,
                daily_notif_email=(
                    daily_alert["moyen_contact"]["souscrit_par_email"]
                    if daily_alert
                    else None
                ),
                daily_notif_sms=(
                    daily_alert["moyen_contact"]["souscrit_par_mobile"]
                    if daily_alert
                    else None
                ),
                monthly_enabled=bool(monthly_alert),
                monthly_threshold=(monthly_alert["valeur"] if monthly_alert else None),
                monthly_notif_email=(
                    monthly_alert["moyen_contact"]["souscrit_par_email"]
                    if monthly_alert
                    else None
                ),
                monthly_notif_sms=(
                    monthly_alert["moyen_contact"]["souscrit_par_mobile"]
                    if monthly_alert
                    else None
                ),
            )
        raise VeoliaAPIGetDataError(
            f"call to= alertes failed with http status= {response.status}",
        )

    async def _get_mensualisation_plan(self) -> dict:
        """Get the plan de mensualisation for the given abonnement ID"""
        _LOGGER.debug("Getting mensualisation plan...")
        url = f"{BACKEND_ISTEFR}/abonnements/{self.account_data.id_abonnement}/facturation/mensualisation/plan"

        response = await self._send_request(url=url, method=GET)
        _LOGGER.debug("Received response with status code %s", response.status)

        if response.status == HTTPStatus.NO_CONTENT:
            _LOGGER.info("No mensualisation plan found")
            return {}

        if response.status == HTTPStatus.OK:
            _LOGGER.debug("OK - Mensualisation plan received")
            return await response.json()

        error_message = (
            f"call to= mensualisation/plan failed with http status= {response.status}",
        )
        _LOGGER.error(error_message)
        return {}

    @staticmethod
    def _iter_months(start_date: date, end_date: date) -> Iterator[tuple[int, int]]:
        """Yield (year, month) pairs covering [start_date, end_date]."""
        y, m = start_date.year, start_date.month
        while (y < end_date.year) or (y == end_date.year and m <= end_date.month):
            yield y, m
            if m == 12:  # noqa: PLR2004
                y, m = y + 1, 1
            else:
                m += 1

    async def fetch_all_data(self, start_date: date, end_date: date) -> None:
        """Fetch consumption for a date range and store in the dataclass.

        - monthly_consumption: list of yearly payloads for each covered year
        - daily_consumption: list of monthly payloads for each covered (year, month)
        """
        _LOGGER.info(
            "Fetching all data for range %s -> %s...",
            start_date,
            end_date,
        )
        await self._check_token()

        semaphore = asyncio.Semaphore(CONCURRENTS_TASKS)

        async def _sem_task(
            task_coro: Coroutine[Any, Any, list[dict[str, Any]]],
        ) -> list[dict[str, Any]]:
            """Semaphore coro"""
            async with semaphore:
                return await task_coro

        years = list(range(start_date.year, end_date.year + 1))
        monthly_tasks = [
            _sem_task(self._get_consumption_data(ConsumptionType.YEARLY, y))
            for y in years
        ]
        daily_tasks = [
            _sem_task(self._get_consumption_data(ConsumptionType.MONTHLY, y, m))
            for (y, m) in self._iter_months(start_date, end_date)
        ]

        monthly_results = await asyncio.gather(*monthly_tasks) if monthly_tasks else []
        daily_results = await asyncio.gather(*daily_tasks) if daily_tasks else []

        self.account_data.monthly_consumption = list(
            itertools.chain.from_iterable(monthly_results),
        )
        self.account_data.daily_consumption = list(
            itertools.chain.from_iterable(daily_results),
        )
        # Fetch other data with no historical
        self.account_data.billing_plan = await self._get_mensualisation_plan()
        self.account_data.alert_settings = await self.get_alerts_settings()
        _LOGGER.info("OK - All data fetched for range")

    async def set_alerts_settings(self, alert_settings: AlertSettings) -> bool:
        """Set the consumption alerts"""
        await self._check_token()

        _LOGGER.debug("Setting alerts params...")
        url = f"{BACKEND_ISTEFR}/alertes/{self.account_data.numero_pds}"
        payload = {}

        if alert_settings.daily_enabled:
            payload["alerte_journaliere"] = {
                "seuil": alert_settings.daily_threshold,
                "unite": "L",
                "souscrite": True,
                "contact_channel": {
                    "subscribed_by_email": alert_settings.daily_notif_email,
                    "subscribed_by_mobile": alert_settings.daily_notif_sms,
                },
            }

        if alert_settings.monthly_enabled:
            payload["alerte_mensuelle"] = {
                "seuil": alert_settings.monthly_threshold,
                "unite": "M3",
                "souscrite": True,
                "contact_channel": {
                    "subscribed_by_email": alert_settings.monthly_notif_email,
                    "subscribed_by_mobile": alert_settings.monthly_notif_sms,
                },
            }

        payload.update(
            {
                "contact_id": self.account_data.contact_id,
                "numero_compteur": self.account_data.numero_compteur,
                "tiers_id": self.account_data.tiers_id,
                "abo_id": str(self.account_data.id_abonnement),
                "type_front": TYPE_FRONT,
            },
        )

        _LOGGER.debug("Alert settings payload: %s", payload)

        response = await self._send_request(url=url, method=POST, json_data=payload)
        _LOGGER.debug("Received response with status code %s ", response.status)

        if response.status != HTTPStatus.NO_CONTENT:
            raise VeoliaAPISetDataError(
                f"Failed to set alerts settings with status code {response.status}, maybe alert are not supported on this account ?",
            )

        _LOGGER.debug("OK - Alerts settings set")
        return True
