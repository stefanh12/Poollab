"""API client for Poollab/Labcom integration."""

import asyncio
import aiohttp
import async_timeout
from typing import Any, Dict, Optional, List
import logging
from datetime import datetime, timedelta

from .const import (
    API_BASE_URL,
    API_TIMEOUT,
    MIN_TIME_BETWEEN_UPDATES,
    MAX_API_RETRIES,
    RATE_LIMIT_RETRY_WAIT,
    RETRY_BACKOFF_MULTIPLIER,
)

_LOGGER = logging.getLogger(__name__)


class PoollabApiClient:
    """Client for interacting with the Labcom Cloud GraphQL API."""

    def __init__(self, token: str, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the API client."""
        self.token = token
        self._session = session
        self._request_lock = asyncio.Lock()
        self._last_request_time: Optional[datetime] = None
        self._max_retries = MAX_API_RETRIES

    async def _apply_throttle(self) -> None:
        """Apply API request throttling to prevent rate limiting."""
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < MIN_TIME_BETWEEN_UPDATES:
                wait_time = MIN_TIME_BETWEEN_UPDATES - elapsed
                _LOGGER.debug("Throttling API request, waiting %.1f seconds", wait_time)
                await asyncio.sleep(wait_time)

    async def _query(self, query: str, variables: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Execute a GraphQL query with throttling and retry logic."""
        if not self._session:
            return None

        # Use lock to serialize API requests (prevent concurrent calls)
        async with self._request_lock:
            # Apply request throttling
            await self._apply_throttle()

            retry_delay = 1  # Start with 1 second delay

            for attempt in range(self._max_retries):
                try:
                    async with async_timeout.timeout(API_TIMEOUT):
                        headers = {
                            "Authorization": f"Bearer {self.token}",
                            "Content-Type": "application/json",
                        }

                        payload = {
                            "query": query,
                            "variables": variables or {},
                        }

                        async with self._session.post(
                            API_BASE_URL,
                            json=payload,
                            headers=headers,
                        ) as resp:
                            # Update last request time for throttling
                            self._last_request_time = datetime.now()

                            if resp.status == 200:
                                data = await resp.json()
                                if "errors" in data:
                                    _LOGGER.error("GraphQL error: %s", data["errors"])
                                    return None
                                return data.get("data")
                            elif resp.status == 401:
                                _LOGGER.error("Invalid API token")
                                return None
                            elif resp.status == 429:  # Rate limited
                                if attempt < self._max_retries - 1:
                                    _LOGGER.warning(
                                        "API rate limited, retrying in %d seconds (attempt %d/%d)",
                                        RATE_LIMIT_RETRY_WAIT,
                                        attempt + 1,
                                        self._max_retries,
                                    )
                                    await asyncio.sleep(RATE_LIMIT_RETRY_WAIT)
                                    continue
                                _LOGGER.error(
                                    "API rate limit exceeded after %d retries", self._max_retries
                                )
                                return None
                            else:
                                if attempt < self._max_retries - 1:
                                    _LOGGER.warning(
                                        "API request failed (%s), retrying (attempt %d/%d)",
                                        resp.status,
                                        attempt + 1,
                                        self._max_retries,
                                    )
                                    await asyncio.sleep(retry_delay)
                                    retry_delay *= RETRY_BACKOFF_MULTIPLIER
                                    continue
                                _LOGGER.error("API request failed: %s", resp.status)
                                return None
                except asyncio.TimeoutError:
                    if attempt < self._max_retries - 1:
                        _LOGGER.warning(
                            "GraphQL request timeout, retrying (attempt %d/%d)",
                            attempt + 1,
                            self._max_retries,
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= RETRY_BACKOFF_MULTIPLIER
                        continue
                    _LOGGER.error(
                        "GraphQL request timeout after %d retries", self._max_retries
                    )
                    return None
                except Exception as err:
                    if attempt < self._max_retries - 1:
                        _LOGGER.warning(
                            "GraphQL request failed: %s, retrying (attempt %d/%d)",
                            err,
                            attempt + 1,
                            self._max_retries,
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= RETRY_BACKOFF_MULTIPLIER
                        continue
                    _LOGGER.error(
                        "GraphQL request failed after %d retries: %s", self._max_retries, err
                    )
                    return None

            return None

    async def verify_token(self) -> bool:
        """Verify the API token is valid."""
        query = """
            query {
                me {
                    id
                    email
                }
            }
        """
        result = await self._query(query)
        return result is not None and "me" in result

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get list of devices associated with the account."""
        query = """
            query {
                devices {
                    id
                    name
                    serialNumber
                    status
                }
            }
        """
        result = await self._query(query)
        if result and "devices" in result:
            return result["devices"]
        return []

    async def get_device_readings(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get latest readings for a specific device."""
        query = """
            query GetDeviceReadings($deviceId: ID!) {
                device(id: $deviceId) {
                    id
                    name
                    lastReading {
                        ph
                        chlorine
                        freeChlorine
                        totalChlorine
                        temperature
                        alkalinity
                        cya
                        salt
                        timestamp
                    }
                }
            }
        """
        result = await self._query(query, {"deviceId": device_id})
        if result and "device" in result:
            return result["device"]
        return None

    async def get_device_readings_history(
        self, device_id: str, hours: int = 24
    ) -> Optional[List[Dict[str, Any]]]:
        """Get historical readings for a device."""
        query = """
            query GetReadingsHistory($deviceId: ID!, $hours: Int!) {
                device(id: $deviceId) {
                    id
                    readings(last: $hours) {
                        edges {
                            node {
                                ph
                                chlorine
                                freeChlorine
                                totalChlorine
                                temperature
                                alkalinity
                                cya
                                salt
                                timestamp
                            }
                        }
                    }
                }
            }
        """
        result = await self._query(query, {"deviceId": device_id, "hours": hours})
        if result and "device" in result and "readings" in result["device"]:
            readings = result["device"]["readings"]
            return [edge["node"] for edge in readings.get("edges", [])]
        return None

    async def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a specific device."""
        query = """
            query GetDevice($deviceId: ID!) {
                device(id: $deviceId) {
                    id
                    name
                    serialNumber
                    status
                    model
                    firmwareVersion
                }
            }
        """
        result = await self._query(query, {"deviceId": device_id})
        if result and "device" in result:
            return result["device"]
        return None

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()


class PoollabApiException(Exception):
    """Exception raised when API request fails."""

    pass
