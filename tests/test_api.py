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
                "me": {
                    "id": "user_123",
                    "email": "test@example.com"
                }
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
async def test_get_devices():
    """Test getting devices."""
    session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "data": {
                "devices": [
                    {
                        "id": "device_1",
                        "name": "Pool",
                        "serialNumber": "ABC123",
                        "status": "online"
                    }
                ]
            }
        }
    )
    
    session.post = AsyncMock(return_value=mock_response)
    
    client = PoollabApiClient("test_token", session)
    devices = await client.get_devices()
    
    assert len(devices) == 1
    assert devices[0]["id"] == "device_1"


@pytest.mark.asyncio
async def test_get_device_readings():
    """Test getting device readings."""
    session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "data": {
                "device": {
                    "id": "device_1",
                    "name": "Pool",
                    "lastReading": {
                        "ph": 7.2,
                        "chlorine": 2.5,
                        "temperature": 26,
                        "alkalinity": 80,
                        "cya": 50,
                        "salt": 1200,
                        "timestamp": "2026-02-16T12:00:00Z"
                    }
                }
            }
        }
    )
    
    session.post = AsyncMock(return_value=mock_response)
    
    client = PoollabApiClient("test_token", session)
    readings = await client.get_device_readings("device_1")
    
    assert readings["lastReading"]["ph"] == 7.2
    assert readings["lastReading"]["chlorine"] == 2.5
    assert readings["lastReading"]["temperature"] == 26
