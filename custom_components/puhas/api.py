"""Client for the Puhas Oy customer portal (asiointipuhas.fi)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Any

import aiohttp

from .const import BASE_URL

TIMEOUT = aiohttp.ClientTimeout(total=30)


class PuhasError(Exception):
    """Base error."""


class PuhasConnectionError(PuhasError):
    """Portal could not be reached."""


class PuhasAuthError(PuhasError):
    """Login failed."""


@dataclass(frozen=True)
class PuhasService:
    """One waste container / service."""

    key: str
    name: str
    next_date: date | None


@dataclass(frozen=True)
class PuhasData:
    """Everything the integration needs."""

    address: str
    services: tuple[PuhasService, ...]


def parse_date(value: Any) -> date | None:
    """Parse 'YYYY-MM-DD'; the portal uses 1899-11-30 for 'no date'."""
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value[:10])
    except ValueError:
        return None
    return parsed if parsed.year >= 2000 else None


def parse_services(raw: list[dict[str, Any]]) -> tuple[PuhasService, ...]:
    """Normalise the get_services_by_customer_numbers.do response."""
    services = []
    for item in raw:
        key = f"{item.get('ASTAsnro')}-{item.get('ASTTyyppi')}-{item.get('ASTPos')}"
        name = item.get("ASTNimi") or (item.get("tariff") or {}).get("name") or key
        next_date = parse_date(item.get("ASTNextDate") or item.get("ASTSeurTyhj"))
        services.append(PuhasService(key=key, name=name, next_date=next_date))
    return tuple(services)


class PuhasClient:
    """Talks to the same endpoints the web portal uses."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password

    async def _login(self) -> None:
        try:
            async with self._session.post(
                f"{BASE_URL}/j_acegi_security_check",
                params={"target": "2"},
                data={
                    "j_username": self._username,
                    "j_password": self._password,
                    "remember-me": "false",
                },
                timeout=TIMEOUT,
            ) as resp:
                await resp.read()
                if resp.status >= 500:
                    raise PuhasConnectionError(f"HTTP {resp.status}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise PuhasConnectionError(str(err)) from err

    async def _get_json(self, path: str, params: Any = None) -> Any:
        try:
            async with self._session.get(
                f"{BASE_URL}/{path}", params=params, timeout=TIMEOUT
            ) as resp:
                if resp.status >= 500:
                    raise PuhasConnectionError(f"HTTP {resp.status}")
                try:
                    return await resp.json(content_type=None)
                except ValueError as err:
                    # Not logged in -> portal returns the HTML login page
                    raise PuhasAuthError("Invalid credentials") from err
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise PuhasConnectionError(str(err)) from err

    async def async_fetch(self) -> PuhasData:
        """Log in and fetch services with their next collection dates."""
        await self._login()

        customers = await self._get_json("secure/get_customer_datas.do")
        if not isinstance(customers, dict):
            raise PuhasAuthError("Unexpected customer data")

        numbers: set[str] = set()
        address = ""
        for entries in customers.values():
            for entry in entries or []:
                if entry.get("asiakasnro"):
                    numbers.add(entry["asiakasnro"])
                if not address and entry.get("katu"):
                    address = f"{entry['katu']}, {entry.get('posti', '')}".strip(", ")
        if not numbers:
            numbers = {self._username}

        raw = await self._get_json(
            "secure/get_services_by_customer_numbers.do",
            params=[("customerNumbers[]", n) for n in sorted(numbers)],
        )
        if not isinstance(raw, list):
            raise PuhasAuthError("Unexpected service data")

        return PuhasData(address=address, services=parse_services(raw))
