"""Veolia API client"""

import base64
import hashlib
import logging
import os
from datetime import datetime, timedelta
from http import HTTPStatus
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp

from veolia_api.exceptions import VeoliaAPIError

from .constants import (
    API_CONNECTION_FLOW,
    AUTHORIZE_ENDPOINT,
    BACKEND_ISTEFR,
    BASE_URL,
    CALLBACK_ENDPOINT,
    CLIENT_ID,
    CODE_CHALLENGE_METHODE,
    LOGIN_IDENTIFIER_ENDPOINT,
    LOGIN_PASSWORD_ENDPOINT,
    LOGIN_URL,
    OAUTH_TOKEN,
    TYPE_FRONT,
    ConsumptionType,
)
from .model import AlertSettings, VeoliaAccountData


class VeoliaAPI:
    """Veolia API client"""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the Veolia API client"""
        self.username = username
        self.password = password
        self.account_data = VeoliaAccountData()
        self.session = aiohttp.ClientSession()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.api_flow = API_CONNECTION_FLOW

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

    async def send_request(
        self,
        url: str,
        method: str,
        params: dict | None = None,
    ) -> aiohttp.ClientResponse:
        """Make an HTTP request"""
        safe_params = params.copy()
        if "password" in safe_params:
            safe_params["password"] = "******"
        self.logger.info(
            "Making %s request to %s with params: %s",
            method,
            url,
            safe_params,
        )
        headers = {}

        if method == "GET":
            async with self.session.get(
                url,
                headers=headers,
                params=params,
                allow_redirects=False,
            ) as response:
                self.logger.info(
                    "Received response with status code %s",
                    response.status,
                )
                return response
        elif method == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            headers["Cache-Control"] = "no-cache"
            async with self.session.post(
                url,
                headers=headers,
                data=urlencode(params),
                allow_redirects=False,
            ) as response:
                self.logger.info(
                    "Received response with status code %s",
                    response.status,
                )
                return response
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    async def execute_flow(self) -> None:
        """Execute the login flow"""
        next_url = AUTHORIZE_ENDPOINT
        state = None

        while next_url:
            config = self.api_flow[next_url]
            full_url = self._get_full_url(next_url)
            params = self._get_params(next_url, config, state)

            if state:
                full_url = f"{full_url}?state={state}"

            response = await self.send_request(full_url, config["method"], params)
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
            raise VeoliaAPIError("Invalid username or password")
        if response.status != self.api_flow[next_url]["success_status"]:
            raise VeoliaAPIError(
                f"API call to {full_url} failed with status {response.status}",
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
                    raise VeoliaAPIError("Authorization code not found")
                self.logger.info("Authorization code received")
        elif response.status == HTTPStatus.OK and next_url == CALLBACK_ENDPOINT:
            next_url = None
        else:
            raise VeoliaAPIError(f"Unexpected 200 response from {full_url}")

        return next_url, state

    async def login(self) -> bool:
        """Login to the Veolia API"""
        if not self.username or not self.password:
            raise VeoliaAPIError("Username or password not provided")
        self.logger.info("Starting login process...")
        await self.execute_flow()
        await self.get_access_token()
        await self.get_client_data()

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
            self.logger.info("Login successful")
            return True
        return False

    async def check_token(self) -> None:
        """Check if the access token is still valid"""
        if (
            not self.account_data.access_token
            or datetime.now().timestamp() >= self.account_data.token_expiration
        ):
            self.logger.error("No access token or token expired")
            await self.login()

    async def get_access_token(self) -> None:
        """Request the access token"""
        token_url = f"{LOGIN_URL}{OAUTH_TOKEN}"
        self.logger.info("Requesting access token...")
        async with self.session.post(
            token_url,
            json={
                "client_id": CLIENT_ID,
                "grant_type": "authorization_code",
                "code_verifier": self.account_data.verifier,
                "code": self.account_data.code,
                "redirect_uri": f"{BASE_URL}{CALLBACK_ENDPOINT}",
            },
        ) as token_response:

            if token_response.status != HTTPStatus.OK:
                raise VeoliaAPIError("Token API call error")

            token_data = await token_response.json()
            self.account_data.access_token = token_data.get("access_token")
            if not self.account_data.access_token:
                raise VeoliaAPIError("Access token not found in the token response")
            self.account_data.token_expiration = (
                datetime.now() + timedelta(seconds=token_data.get("expires_in", 0))
            ).timestamp()
            self.logger.info("Access token received")

    async def get_client_data(self) -> None:
        """Get the account data"""
        await self.check_token()

        headers = {"Authorization": f"Bearer {self.account_data.access_token}"}
        async with self.session.get(
            url=f"{BACKEND_ISTEFR}/espace-client?type-front={TYPE_FRONT}",
            headers=headers,
        ) as userdata_response:
            if userdata_response.status != HTTPStatus.OK:
                raise VeoliaAPIError("Espace-client call error")

            userdata = await userdata_response.json()
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
                raise VeoliaAPIError("Some user data not found in the response")

        # Facturation request
        async with self.session.get(
            url=f"{BACKEND_ISTEFR}/abonnements/{self.account_data.id_abonnement}/facturation",
            headers=headers,
        ) as facturation_response:
            if facturation_response.status != HTTPStatus.OK:
                raise VeoliaAPIError("Facturation call error")

            facturation_data = await facturation_response.json()
            self.account_data.numero_pds = facturation_data.get("numero_pds")
            if not self.account_data.numero_pds:
                raise VeoliaAPIError("numero_pds not found in the response")

            self.account_data.date_debut_abonnement = facturation_data.get(
                "date_debut_abonnement",
            )
            if not self.account_data.date_debut_abonnement:
                raise VeoliaAPIError(
                    "date_debut_abonnement not found in the response",
                )

    async def get_consumption_data(
        self,
        data_type: ConsumptionType,
        year: int,
        month: int | None = None,
    ) -> dict:
        """Get the water consumption data"""
        await self.check_token()
        headers = {"Authorization": f"Bearer {self.account_data.access_token}"}
        params = {
            "annee": year,
            "numero-pds": self.account_data.numero_pds,
            "date-debut-abonnement": self.account_data.date_debut_abonnement,
        }

        if data_type == ConsumptionType.MONTHLY and month is not None:
            params["mois"] = month
            endpoint = "journalieres"
        elif data_type == ConsumptionType.YEARLY:
            endpoint = "mensuelles"
        else:
            raise ValueError("Invalid data type or missing month for monthly data")

        url = f"{BACKEND_ISTEFR}/consommations/{self.account_data.id_abonnement}/{endpoint}"

        async with self.session.get(url, headers=headers, params=params) as response:
            self.logger.info("Received response with status code %s", response.status)
            if response.status != HTTPStatus.OK:
                raise VeoliaAPIError("Get data call error")
            return await response.json()

    async def get_alerts(self) -> AlertSettings:
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
        await self.check_token()
        headers = {"Authorization": f"Bearer {self.account_data.access_token}"}
        params = {
            "abo_id": self.account_data.id_abonnement,
        }
        url = f"{BACKEND_ISTEFR}/alertes/{self.account_data.numero_pds}"

        async with self.session.get(url, headers=headers, params=params) as response:
            self.logger.info("Received response with status code %s", response.status)
            if response.status != HTTPStatus.OK:
                raise VeoliaAPIError(
                    f"Get alerts call error status code {response.status}",
                )
            data = await response.json()
            daily_alert = data["seuils"].get("journalier", None)
            monthly_alert = data["seuils"].get("mensuel", None)

        return AlertSettings(
            daily_enabled=bool(daily_alert),
            daily_threshold=daily_alert["valeur"] if daily_alert else None,
            daily_contact_email=(
                daily_alert["moyen_contact"]["souscrit_par_email"]
                if daily_alert
                else None
            ),
            daily_contact_sms=(
                daily_alert["moyen_contact"]["souscrit_par_mobile"]
                if daily_alert
                else None
            ),
            monthly_enabled=bool(monthly_alert),
            monthly_threshold=monthly_alert["valeur"] if monthly_alert else None,
            monthly_contact_email=(
                monthly_alert["moyen_contact"]["souscrit_par_email"]
                if monthly_alert
                else None
            ),
            monthly_contact_sms=(
                monthly_alert["moyen_contact"]["souscrit_par_mobile"]
                if monthly_alert
                else None
            ),
        )

    async def fetch_all_data(self, year: int, month: int) -> None:
        """Fetch all consumption data and insert it into the dataclass"""
        self.account_data.monthly_consumption = await self.get_consumption_data(
            ConsumptionType.YEARLY,
            year,
        )
        self.account_data.daily_consumption = await self.get_consumption_data(
            ConsumptionType.MONTHLY,
            year,
            month,
        )
        self.account_data.alert_settings = await self.get_alerts()

    async def set_alerts(self, alert_settings: AlertSettings) -> bool:
        """Set the consumption alerts"""
        await self.check_token()
        url = f"{BACKEND_ISTEFR}/alertes/{self.account_data.numero_pds}"
        payload = {}

        if alert_settings.daily_enabled:
            payload["alerte_journaliere"] = {
                "seuil": alert_settings.daily_threshold,
                "unite": "L",
                "souscrite": True,
                "contact_channel": {
                    "subscribed_by_email": alert_settings.daily_contact_email,
                    "subscribed_by_mobile": alert_settings.daily_contact_sms,
                },
            }

        if alert_settings.monthly_enabled:
            payload["alerte_mensuelle"] = {
                "seuil": alert_settings.monthly_threshold,
                "unite": "M3",
                "souscrite": True,
                "contact_channel": {
                    "subscribed_by_email": alert_settings.monthly_contact_email,
                    "subscribed_by_mobile": alert_settings.monthly_contact_sms,
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
        headers = {
            "Authorization": f"Bearer {self.account_data.access_token}",
            "Content-Type": "application/json",
        }

        async with self.session.post(url, headers=headers, json=payload) as response:
            self.logger.info("Received response with status code %s ", response.status)
            return response.status == HTTPStatus.NO_CONTENT

    async def close(self) -> None:
        """Close the session"""
        await self.session.close()
