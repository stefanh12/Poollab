"""Tests for Poollab API client."""

import pytest
from unittest.mock import MagicMock, AsyncMock
import aiohttp
from poollab.api import PoollabApiClient


def create_async_context_manager_mock(mock_obj):
    """Helper to create an async context manager mock."""
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = mock_obj
    async_cm.__aexit__.return_value = None
    return async_cm


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

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

    client = PoollabApiClient("test_token", session)
    result = await client.verify_token()

    assert result is True


@pytest.mark.asyncio
async def test_verify_token_failure():
    """Test failed token verification."""
    session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 401

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

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

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

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

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

    client = PoollabApiClient("test_token", session)
    devices = await client.get_devices()

    assert len(devices) == 2
    assert any(d["account"] == "Hemma Pool" for d in devices)
    assert any(d["account"] == "Hemma Spa" for d in devices)


@pytest.mark.asyncio
async def test_get_devices_keeps_multiple_pools_with_same_account_name():
    """Test multiple pools are preserved when the account name is identical."""
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
                        "id": 1,
                    },
                    {
                        "account": "Hemma Pool",
                        "device_serial": "POOL002",
                        "parameter": "PL pH",
                        "value": 7.5,
                        "id": 2,
                    },
                ]
            }
        }
    )

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

    client = PoollabApiClient("test_token", session)
    devices = await client.get_devices()

    assert len(devices) == 2
    assert {device["serialNumber"] for device in devices} == {"POOL001", "POOL002"}
    assert {device["name"] for device in devices} == {
        "Hemma Pool (POOL001)",
        "Hemma Pool (POOL002)",
    }


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

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

    client = PoollabApiClient("test_token", session)
    result = await client.get_active_chlorine(26.0, 7.2, 2.5, 50.0)

    assert result is not None
    assert result["unbound_chlorine"] == 1.8
    assert result["bound_to_cya"] == 0.7


@pytest.mark.asyncio
async def test_get_measurements_with_multiple_same_parameter():
    """Test getting measurements with multiple values for the same parameter."""
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
                        "value": 7.0,
                        "timestamp": "2026-02-16T10:00:00Z",
                        "device_serial": "POOL001",
                    },
                    {
                        "account": "Hemma Pool",
                        "id": 2,
                        "parameter": "PL pH",
                        "value": 7.2,
                        "timestamp": "2026-02-16T11:00:00Z",
                        "device_serial": "POOL001",
                    },
                    {
                        "account": "Hemma Pool",
                        "id": 3,
                        "parameter": "PL pH",
                        "value": 7.1,
                        "timestamp": "2026-02-16T10:30:00Z",
                        "device_serial": "POOL001",
                    }
                ]
            }
        }
    )

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

    client = PoollabApiClient("test_token", session)
    measurements = await client.get_measurements()

    assert len(measurements) == 3
    # Verify all measurements are returned
    assert all(m["parameter"] == "PL pH" for m in measurements)


@pytest.mark.asyncio
async def test_get_measurements_empty_response():
    """Test handling empty measurements response."""
    session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={"data": {"Measurements": []}}
    )

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

    client = PoollabApiClient("test_token", session)
    measurements = await client.get_measurements()

    assert measurements == []


@pytest.mark.asyncio
async def test_get_devices_filters_tutorial_entries():
    """Test that tutorial/demo entries are filtered out."""
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
                        "id": 1,
                    },
                    {
                        "account": "Tutorial Pool",
                        "device_serial": "tutorial",
                        "parameter": "PL pH",
                        "value": 7.5,
                        "id": 2,
                    },
                    {
                        "account": "Demo Pool",
                        "device_serial": "DEMO001",
                        "parameter": "PL pH",
                        "value": 7.0,
                        "id": 3,
                        "operator_name": "Tutorial",
                    }
                ]
            }
        }
    )

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

    client = PoollabApiClient("test_token", session)
    devices = await client.get_devices()

    # Only non-tutorial devices should be returned
    assert len(devices) == 1
    assert devices[0]["serialNumber"] == "POOL001"


@pytest.mark.asyncio
async def test_get_measurements_caching():
    """Test that measurements are cached and reused within TTL."""
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
                        "value": 7.2,
                        "device_serial": "POOL001",
                    }
                ]
            }
        }
    )

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

    client = PoollabApiClient("test_token", session)
    
    # First call
    measurements1 = await client.get_measurements()
    assert len(measurements1) == 1
    
    # Second call should use cache (within 30 second TTL)
    measurements2 = await client.get_measurements()
    assert len(measurements2) == 1
    
    # Session.post should still only have been called once due to caching
    # (The mock tracks how many times post was called)
    assert session.post.call_count == 1


@pytest.mark.asyncio
async def test_active_chlorine_with_zero_cya():
    """Test active chlorine calculation with zero CYA."""
    session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "data": {
                "ActiveChlorine": {
                    "unbound_chlorine": 2.5,
                    "bound_to_cya": 0.0,
                    "ocl": 2.0,
                    "cl3cy": 0.0
                }
            }
        }
    )

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

    client = PoollabApiClient("test_token", session)
    result = await client.get_active_chlorine(25.0, 7.2, 2.5, 0.0)

    assert result is not None
    assert result["unbound_chlorine"] == 2.5
    assert result["bound_to_cya"] == 0.0


@pytest.mark.asyncio
async def test_get_measurements_with_all_parameter_types():
    """Test getting various water parameter measurements."""
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
                        "value": 7.2,
                        "unit": None,
                        "timestamp": "2026-02-16T12:00:00Z",
                        "device_serial": "POOL001",
                    },
                    {
                        "account": "Hemma Pool",
                        "id": 2,
                        "parameter": "PL Chlorine Free",
                        "value": 2.5,
                        "unit": "ppm",
                        "timestamp": "2026-02-16T12:00:00Z",
                        "device_serial": "POOL001",
                    },
                    {
                        "account": "Hemma Pool",
                        "id": 3,
                        "parameter": "PL Temperature",
                        "value": 26.5,
                        "unit": "°C",
                        "timestamp": "2026-02-16T12:00:00Z",
                        "device_serial": "POOL001",
                    },
                    {
                        "account": "Hemma Pool",
                        "id": 4,
                        "parameter": "PL T-Alka",
                        "value": 80,
                        "unit": "ppm",
                        "timestamp": "2026-02-16T12:00:00Z",
                        "device_serial": "POOL001",
                    },
                    {
                        "account": "Hemma Pool",
                        "id": 5,
                        "parameter": "PL Cyanuric Acid",
                        "value": 45,
                        "unit": "ppm",
                        "timestamp": "2026-02-16T12:00:00Z",
                        "device_serial": "POOL001",
                    },
                    {
                        "account": "Hemma Pool",
                        "id": 6,
                        "parameter": "PL Salt",
                        "value": 1200,
                        "unit": "ppm",
                        "timestamp": "2026-02-16T12:00:00Z",
                        "device_serial": "POOL001",
                    }
                ]
            }
        }
    )

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

    client = PoollabApiClient("test_token", session)
    measurements = await client.get_measurements()

    assert len(measurements) == 6
    
    # Verify all parameter types are present
    parameters = {m["parameter"] for m in measurements}
    assert "PL pH" in parameters
    assert "PL Chlorine Free" in parameters
    assert "PL Temperature" in parameters
    assert "PL T-Alka" in parameters
    assert "PL Cyanuric Acid" in parameters
    assert "PL Salt" in parameters


@pytest.mark.asyncio
async def test_get_devices_no_measurements():
    """Test getting devices when no measurements available."""
    session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={"data": {"Measurements": []}}
    )

    session.post = MagicMock(return_value=create_async_context_manager_mock(mock_response))

    client = PoollabApiClient("test_token", session)
    devices = await client.get_devices()

    assert devices == []
