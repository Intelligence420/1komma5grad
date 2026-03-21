"""API client for 1KOMMA5GRAD."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from .const import (
    AUTH_URL,
    AUTH0_CLIENT,
    CLIENT_ID,
    CUSTOMER_IDENTITY_URL,
    HEARTBEAT_URL,
)

_LOGGER = logging.getLogger(__name__)


class EinsK5GApiError(Exception):
    """Exception for API errors."""


class EinsK5GAuthError(EinsK5GApiError):
    """Exception for authentication errors."""


class EinsK5GApi:
    """API client for 1KOMMA5GRAD."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._session = session
        self._own_session = session is None
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None
        self._user_id: str | None = None
        self._system_id: str | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()

    def _get_common_headers(self) -> dict[str, str]:
        """Get common headers for API requests."""
        return {
            "accept": "*/*",
            "accept-language": "de",
            "content-type": "application/json",
            "origin": "https://app.1komma5grad.com",
            "referer": "https://app.1komma5grad.com/",
            "x-app-build-number": "2437",
            "x-app-package-name": "heartbeat_app",
            "x-app-version": "1.55.0",
            "x-platform": "web",
        }

    async def authenticate(self) -> bool:
        """Authenticate with the API and get access token."""
        session = await self._get_session()

        try:
            # Step 1: Get initial state from authorize endpoint
            authorize_url = (
                f"{AUTH_URL}/authorize?"
                f"client_id={CLIENT_ID}&"
                f"response_type=code&"
                f"response_mode=query&"
                f"auth0Client={AUTH0_CLIENT}"
            )

            async with session.get(
                authorize_url,
                headers={"host": "auth.1komma5grad.com"},
                allow_redirects=False,
            ) as response:
                text = await response.text()
                state = self._extract_state(text)

                if not state:
                    raise EinsK5GAuthError("Could not extract state from auth response")

            # Step 2: Submit login credentials
            login_url = f"{AUTH_URL}/u/login?state={state}&ui_locales=de"
            login_payload = {
                "password": self._password,
                "state": state,
                "username": self._username,
            }

            async with session.post(
                login_url,
                data=login_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                allow_redirects=False,
            ) as response:
                text = await response.text()
                authorize_path = self._extract_authorize_path(text)

                if not authorize_path:
                    raise EinsK5GAuthError("Login failed - invalid credentials")

            # Step 3: Complete authorization flow
            full_authorize_url = f"{AUTH_URL}{authorize_path}"

            async with session.get(
                full_authorize_url,
                allow_redirects=False,
            ) as response:
                location = response.headers.get("Location", "")
                code = self._extract_code(location)

                if not code:
                    raise EinsK5GAuthError("Could not extract authorization code")

            # Step 4: Exchange code for token
            token_url = f"{AUTH_URL}/oauth/token"
            token_payload = {
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "code": code,
                "redirect_uri": "https://app.1komma5grad.com",
            }

            async with session.post(
                token_url,
                json=token_payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status != 200:
                    raise EinsK5GAuthError("Failed to exchange code for token")

                data = await response.json()
                self._access_token = data.get("access_token")
                expires_in = data.get("expires_in", 86400)
                self._token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)

                # Extract user_id from token claims
                self._user_id = self._extract_user_id_from_token(self._access_token)

                _LOGGER.info("Successfully authenticated with 1KOMMA5GRAD API")
                return True

        except aiohttp.ClientError as err:
            raise EinsK5GAuthError(f"Connection error during authentication: {err}") from err

    def _extract_state(self, text: str) -> str | None:
        """Extract state parameter from response text."""
        match = re.search(r"state=([A-Za-z0-9_-]+)", text)
        return match.group(1) if match else None

    def _extract_authorize_path(self, text: str) -> str | None:
        """Extract authorize path from response text."""
        if not text:
            return None
        idx = text.find("/authorize")
        return text[idx:].split('"')[0].split("'")[0] if idx != -1 else None

    def _extract_code(self, location: str) -> str | None:
        """Extract authorization code from redirect location."""
        match = re.search(r"code=([A-Za-z0-9_-]+)", location)
        return match.group(1) if match else None

    def _extract_user_id_from_token(self, token: str) -> str | None:
        """Extract user ID from JWT token."""
        try:
            import base64
            import json

            parts = token.split(".")
            if len(parts) != 3:
                return None

            payload = parts[1]
            # Add padding if necessary
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += "=" * padding

            decoded = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded)
            return claims.get("sub")
        except Exception:
            return None

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        if (
            self._access_token is None
            or self._token_expiry is None
            or datetime.now() >= self._token_expiry
        ):
            await self.authenticate()

    async def _api_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated API request."""
        await self._ensure_authenticated()
        session = await self._get_session()

        headers = self._get_common_headers()
        headers["authorization"] = f"Bearer {self._access_token}"
        if self._user_id:
            headers["x-user-id"] = self._user_id

        headers.update(kwargs.pop("headers", {}))

        async with session.request(method, url, headers=headers, **kwargs) as response:
            if response.status == 401:
                # Token expired, try to re-authenticate
                self._access_token = None
                await self._ensure_authenticated()
                headers["authorization"] = f"Bearer {self._access_token}"

                async with session.request(method, url, headers=headers, **kwargs) as retry_response:
                    if retry_response.status != 200:
                        raise EinsK5GApiError(f"API request failed: {retry_response.status}")
                    return await retry_response.json()

            if response.status != 200:
                raise EinsK5GApiError(f"API request failed: {response.status}")

            return await response.json()

    async def get_user_info(self) -> dict[str, Any]:
        """Get current user information."""
        url = f"{CUSTOMER_IDENTITY_URL}/api/v1/users/me"
        return await self._api_request("GET", url)

    async def get_systems(self) -> list[dict[str, Any]]:
        """Get all systems for the user."""
        url = f"{HEARTBEAT_URL}/api/v2/systems"
        result = await self._api_request("GET", url)
        return result if isinstance(result, list) else [result]

    async def get_system_id(self) -> str:
        """Get the first system ID."""
        if self._system_id:
            return self._system_id

        systems = await self.get_systems()
        if not systems:
            raise EinsK5GApiError("No systems found for user")

        self._system_id = systems[0].get("id")
        return self._system_id

    async def get_live_overview(self, system_id: str | None = None) -> dict[str, Any]:
        """Get live overview data for a system."""
        if system_id is None:
            system_id = await self.get_system_id()

        url = f"{HEARTBEAT_URL}/api/v3/systems/{system_id}/live-overview"
        return await self._api_request("GET", url)

    async def get_history(
        self,
        system_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        resolution: str = "day",
    ) -> dict[str, Any]:
        """Get historical energy data.

        Args:
            system_id: System ID (uses default if not provided)
            start_date: Start date for history
            end_date: End date for history
            resolution: Data resolution (hour, day, month, year)
        """
        if system_id is None:
            system_id = await self.get_system_id()

        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        url = (
            f"{HEARTBEAT_URL}/api/v3/systems/{system_id}/history?"
            f"from={start_date.strftime('%Y-%m-%d')}&"
            f"to={end_date.strftime('%Y-%m-%d')}&"
            f"resolution={resolution}"
        )
        return await self._api_request("GET", url)

    async def get_energy_flow(self, system_id: str | None = None) -> dict[str, Any]:
        """Get current energy flow data."""
        if system_id is None:
            system_id = await self.get_system_id()

        url = f"{HEARTBEAT_URL}/api/v3/systems/{system_id}/energy-flow"
        return await self._api_request("GET", url)
