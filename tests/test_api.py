"""Tests for Poollab API client."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import aiohttp
from poollab.api import PoollabApiClient


@pytest.fixture
def api_client():
    """Create test API client."""
    session = MagicMock()
    return PoollabApiClient("test_token_123", session)


@pytest.mark.asyncio
async def test_verify_token_success():
    """Test successful token verification."""
    session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "data": {
                "Measurements": [
                    {
                        "account": "Hemma Pool",
                        "id": 1,
                        "parameter": "PL pH",
                        "value": 7.2
                    }
                ]
            }
        }
    )

    session.post = AsyncMock(return_value=mock_response)

    client = PoollabApiClient("test_token", session)
    result = await client.verify_token()

    assert result is True


@pytest.mark.asyncio
async def test_verify_token_failure():
    """Test failed token verification."""
    session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 401

    session.post = AsyncMock(return_value=mock_response)

    client = PoollabApiClient("invalid_token", session)
    result = await client.verify_token()

    assert result is False


@pytest.mark.asyncio
async def test_get_measurements():
    """Test getting measurements."""
    session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "data": {
                "Measurements": [
                    {
                        "account": "Hemma Pool",
                        "id": 1,
                        "unit": "ppm",
                        "parameter": "PL Chlorine Free",
                        "timestamp": "2026-02-16T12:00:00Z",
                        "comment": "test",
                        "value": 2.5,
                        "device_serial": "POOL001",
                        "operator_name": "User"
                    }
                ]
            }
        }
    )

    session.post = AsyncMock(return_value=mock_response)

    client = PoollabApiClient("test_token", session)
    measurements = await client.get_measurements()

    assert len(measurements) == 1
    assert measurements[0]["parameter"] == "PL Chlorine Free"
    assert measurements[0]["value"] == 2.5


@pytest.mark.asyncio
async def test_get_devices():
    """Test getting devices from measurements."""
    session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "data": {
                "Measurements": [
                    {
                        "account": "Hemma Pool",
                        "device_serial": "POOL001",
                        "parameter": "PL pH",
                        "value": 7.2,
                        "id": 1
                    },
                    {
                        "account": "Hemma Spa",
                        "device_serial": "SPA001",
                        "parameter": "PL pH",
                        "value": 7.5,
                        "id": 2
                    }
                ]
            }
        }
    )

    session.post = AsyncMock(return_value=mock_response)

    client = PoollabApiClient("test_token", session)
    devices = await client.get_devices()

    assert len(devices) == 2
    assert any(d["account"] == "Hemma Pool" for d in devices)
    assert any(d["account"] == "Hemma Spa" for d in devices)


@pytest.mark.asyncio
async def test_get_active_chlorine():
    """Test getting active chlorine calculation."""
    session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "data": {
                "ActiveChlorine": {
                    "unbound_chlorine": 1.8,
                    "bound_to_cya": 0.7,
                    "ocl": 0.5,
                    "cl3cy": 0.2
                }
            }
        }
    )

    session.post = AsyncMock(return_value=mock_response)

    client = PoollabApiClient("test_token", session)
    result = await client.get_active_chlorine(26.0, 7.2, 2.5, 50.0)

    assert result is not None
    assert result["unbound_chlorine"] == 1.8
    assert result["bound_to_cya"] == 0.7
