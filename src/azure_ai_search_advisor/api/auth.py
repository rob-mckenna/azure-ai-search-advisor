"""Authentication helpers for FastAPI endpoints."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from threading import Lock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

bearer_scheme = HTTPBearer(auto_error=False)

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_DEV_ENVIRONMENTS = {"dev", "development", "local", "test"}
_PROD_ENVIRONMENTS = {"prod", "production", "staging"}
_ENVIRONMENT_KEYS = ("ENVIRONMENT", "APP_ENV", "FASTAPI_ENV", "PYTHON_ENV")


@dataclass(frozen=True)
class CurrentUser:
    """Authenticated caller details."""

    sub: str
    name: str
    oid: str | None
    roles: tuple[str, ...]


class _JwksCache:
    """Simple in-memory JWKS cache."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._keys: dict[str, Any] | None = None
        self._metadata: dict[str, Any] | None = None
        self._tenant_id: str | None = None

    def get_signing_key(self, *, tenant_id: str, kid: str, refresh: bool = False) -> dict[str, Any]:
        """Return a signing key from cached or refreshed JWKS data."""

        with self._lock:
            if refresh or self._keys is None or self._tenant_id != tenant_id:
                self._metadata = _fetch_openid_metadata(tenant_id)
                jwks_uri = self._metadata.get("jwks_uri")
                if not jwks_uri:
                    raise _auth_error("Microsoft Entra ID discovery metadata is missing a JWKS URI.")
                self._keys = _fetch_json(jwks_uri)
                self._tenant_id = tenant_id

            for key in self._keys.get("keys", []):
                if key.get("kid") == kid:
                    return key

        raise KeyError(kid)

    def get_issuer(self, *, tenant_id: str, refresh: bool = False) -> str:
        """Return the expected issuer value from metadata."""

        with self._lock:
            if refresh or self._metadata is None or self._tenant_id != tenant_id:
                self._metadata = _fetch_openid_metadata(tenant_id)
                self._tenant_id = tenant_id
            issuer = self._metadata.get("issuer")

        if not issuer:
            raise _auth_error("Microsoft Entra ID discovery metadata is missing an issuer.")
        return issuer


_jwks_cache = _JwksCache()


def _auth_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _configuration_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Authentication is enabled but misconfigured: {message}",
    )


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(f"Unsupported boolean value: {value}")


def _get_environment_name() -> str | None:
    for key in _ENVIRONMENT_KEYS:
        value = os.getenv(key)
        if value:
            return value.strip().lower()
    return None


def is_auth_enabled() -> bool:
    """Return whether bearer token validation is enabled."""

    configured = os.getenv("AUTH_ENABLED")
    if configured is not None:
        try:
            return _parse_bool(configured)
        except ValueError as exc:
            raise _configuration_error(str(exc)) from exc

    environment = _get_environment_name()
    if environment in _PROD_ENVIRONMENTS:
        return True
    if environment in _DEV_ENVIRONMENTS:
        return False
    return False


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise _configuration_error(f"{name} must be set.")
    return value


def _fetch_json(url: str) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=5) as response:  # noqa: S310 - Microsoft metadata endpoint
            payload = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise _auth_error("Failed to contact Microsoft Entra ID for token validation.") from exc

    return json.loads(payload)


def _fetch_openid_metadata(tenant_id: str) -> dict[str, Any]:
    return _fetch_json(
        f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
    )


def _normalize_roles(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(role) for role in value)
    if isinstance(value, str) and value:
        return (value,)
    return ()


def _decode_token(token: str, *, tenant_id: str, client_id: str, refresh: bool = False) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise _auth_error("Bearer token header is invalid.") from exc

    kid = header.get("kid")
    if not kid:
        raise _auth_error("Bearer token header is missing a key identifier.")

    try:
        key = _jwks_cache.get_signing_key(tenant_id=tenant_id, kid=kid, refresh=refresh)
        issuer = _jwks_cache.get_issuer(tenant_id=tenant_id, refresh=refresh)
    except KeyError as exc:
        if not refresh:
            return _decode_token(token, tenant_id=tenant_id, client_id=client_id, refresh=True)
        raise _auth_error("Bearer token signing key was not found.") from exc

    algorithm = str(header.get("alg") or "RS256")
    if algorithm != "RS256":
        raise _auth_error("Bearer token uses an unsupported signing algorithm.")

    options = {"verify_at_hash": False}
    try:
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=issuer,
            options=options,
        )
    except JWTError as exc:
        if not refresh:
            return _decode_token(token, tenant_id=tenant_id, client_id=client_id, refresh=True)
        raise _auth_error("Bearer token validation failed.") from exc


def _mock_current_user() -> CurrentUser:
    return CurrentUser(
        sub="local-development-user",
        name="Local Development User",
        oid="local-development-oid",
        roles=("developer",),
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Return the authenticated caller or a mock local user."""

    if not is_auth_enabled():
        return _mock_current_user()

    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise _auth_error("Bearer token is required.")

    tenant_id = _get_required_env("AZURE_TENANT_ID")
    client_id = _get_required_env("AZURE_CLIENT_ID")
    claims = _decode_token(credentials.credentials, tenant_id=tenant_id, client_id=client_id)

    subject = str(claims.get("sub") or claims.get("oid") or "")
    if not subject:
        raise _auth_error("Bearer token is missing a subject claim.")

    return CurrentUser(
        sub=subject,
        name=str(claims.get("name") or claims.get("preferred_username") or "Authenticated User"),
        oid=str(claims["oid"]) if claims.get("oid") else None,
        roles=_normalize_roles(claims.get("roles")),
    )
