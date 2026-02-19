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
        self._measurements_cache: Optional[List[Dict[str, Any]]] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 30  # Cache measurements for 30 seconds

    async def _apply_throttle(self) -> None:
        """Apply API request throttling to prevent rate limiting."""
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < MIN_TIME_BETWEEN_UPDATES:
                wait_time = MIN_TIME_BETWEEN_UPDATES - elapsed
                _LOGGER.debug("Throttling API request, waiting %.1f seconds", wait_time)
                await asyncio.sleep(wait_time)

    async def _query(
        self,
        query: str,
        variables: Optional[Dict] = None,
        skip_throttle: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Execute a GraphQL query with throttling and retry logic."""
        if not self._session:
            return None

        # Use lock to serialize API requests (prevent concurrent calls)
        async with self._request_lock:
            # Apply request throttling unless explicitly skipped
            if not skip_throttle:
                await self._apply_throttle()

            retry_delay = 1  # Start with 1 second delay

            for attempt in range(self._max_retries):
                try:
                    async with async_timeout.timeout(API_TIMEOUT):
                        headers = {
                            "Authorization": self.token,
                            "Content-Type": "application/json",
                        }

                        payload = {
                            "query": query,
                            "variables": variables or {},
                        }

                        _LOGGER.debug(
                            "Making GraphQL request to %s with headers: %s",
                            API_BASE_URL,
                            {k: (v[:20] + "..." if len(v) > 20 else v) for k, v in headers.items()},
                        )

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
                                _LOGGER.error("Invalid API token (401 Unauthorized)")
                                return None
                            elif resp.status == 403:
                                body = await resp.text()
                                _LOGGER.error("Access forbidden (403 Forbidden). Response: %s", body)
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
                                    try:
                                        error_body = await resp.text()
                                    except:
                                        error_body = "Could not read response"
                                    _LOGGER.warning(
                                        "API request failed (%s), retrying (attempt %d/%d). Response: %s",
                                        resp.status,
                                        attempt + 1,
                                        self._max_retries,
                                        error_body[:200] if error_body else "No response body",
                                    )
                                    await asyncio.sleep(retry_delay)
                                    retry_delay *= RETRY_BACKOFF_MULTIPLIER
                                    continue
                                try:
                                    error_body = await resp.text()
                                except:
                                    error_body = "Could not read response"
                                _LOGGER.error("API request failed: %s. Response: %s", resp.status, error_body[:200] if error_body else "No response body")
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
        """Verify the API token is valid by querying measurements."""
        result = await self.get_measurements()
        return result is not None and len(result) >= 0

    async def get_measurements(self) -> Optional[List[Dict[str, Any]]]:
        """Get all measurements from Labcom cloud."""
        # Check cache validity
        if self._measurements_cache is not None and self._cache_time is not None:
            elapsed = (datetime.now() - self._cache_time).total_seconds()
            if elapsed < self._cache_ttl:
                _LOGGER.debug(
                    "Using cached measurements (cache age: %.1f seconds)",
                    elapsed,
                )
                return self._measurements_cache

        query = """
        {
          Measurements {
            account
            id
            unit
            parameter
            timestamp
            comment
            value
            device_serial
            operator_name
          }
        }
        """
        result = await self._query(query)
        _LOGGER.debug("Raw API response: %s", result)

        if result and "Measurements" in result:
            measurements = result["Measurements"]
            _LOGGER.info("Retrieved %d measurements from Labcom", len(measurements))

            # Cache the measurements
            self._measurements_cache = measurements
            self._cache_time = datetime.now()

            for idx, measurement in enumerate(measurements):
                _LOGGER.debug(
                    "Measurement %d: account=%s, parameter=%s, value=%s, device_serial=%s, timestamp=%s",
                    idx,
                    measurement.get("account"),
                    measurement.get("parameter"),
                    measurement.get("value"),
                    measurement.get("device_serial"),
                    measurement.get("timestamp"),
                )
            return measurements

        _LOGGER.warning("No measurements found in API response or error occurred")
        return []

    async def get_active_chlorine(
        self, temperature: float, ph: float, chlorine: float, cya: float
    ) -> Optional[Dict[str, Any]]:
        """Calculate active chlorine values based on water parameters."""
        _LOGGER.debug(
            "Calculating active chlorine with temp=%s, pH=%s, chlorine=%s, cya=%s",
            temperature,
            ph,
            chlorine,
            cya,
        )
        query = """
        {{
          ActiveChlorine (temperature: {temperature}, pH: {ph}, chlorine: {chlorine}, cya: {cya}) {{
            unbound_chlorine
            bound_to_cya
            ocl
            cl3cy
            cl2cy
            hocl
            hclcy
            hcl2cy
            h2clcy
          }}
        }}
        """.format(temperature=temperature, ph=ph, chlorine=chlorine, cya=cya)
        _LOGGER.debug("ActiveChlorine query: %s", query.strip())
        start_time = datetime.now()
        result = await self._query(query, skip_throttle=True)
        duration = (datetime.now() - start_time).total_seconds()
        _LOGGER.debug("ActiveChlorine API call completed in %.2fs", duration)
        if result and "ActiveChlorine" in result:
            _LOGGER.debug("Active chlorine result: %s", result["ActiveChlorine"])
            return result["ActiveChlorine"]
        if result is None:
            _LOGGER.warning("ActiveChlorine API returned no data (None)")
        else:
            _LOGGER.warning("No ActiveChlorine data in API response: %s", result)
        return None

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get list of unique devices from measurements."""
        measurements = await self.get_measurements()
        if not measurements:
            _LOGGER.warning("No measurements available to extract devices from")
            return []

        devices = {}
        for measurement in measurements:
            device_serial = measurement.get("device_serial", "unknown")
            account = measurement.get("account", "unknown")
            if device_serial not in devices:
                device = {
                    "id": device_serial,
                    "name": account,
                    "serialNumber": device_serial,
                    "account": account,
                }
                devices[device_serial] = device
                _LOGGER.info(
                    "Added device: account=%s, serial=%s",
                    account,
                    device_serial,
                )

        device_list = list(devices.values())
        _LOGGER.info("Total unique devices found: %d", len(device_list))
        return device_list

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()


class PoollabApiException(Exception):
    """Exception raised when API request fails."""

    pass
