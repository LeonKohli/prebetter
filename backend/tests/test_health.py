import pytest
import time
from unittest.mock import patch, MagicMock

from app.services import health

# Reset health state before each test for isolation
@pytest.fixture(autouse=True)
def reset_health_state():
    health._HEALTH_STATE = {
        "api_start_time": time.time(),
        "prelude_db_available": False,
        "prebetter_db_available": False,
        "ready": False
    }
    yield # Run the test
    # Optional: reset again after test if needed, though autouse=True handles setup

def test_update_health_state_individual():
    """Test updating individual components of the health state."""
    start_time = health._HEALTH_STATE["api_start_time"]
    
    health.update_health_state(prelude_available=True)
    assert health._HEALTH_STATE == {
        "api_start_time": start_time,
        "prelude_db_available": True,
        "prebetter_db_available": False,
        "ready": False
    }
    
    health.update_health_state(prebetter_available=True)
    assert health._HEALTH_STATE == {
        "api_start_time": start_time,
        "prelude_db_available": True,
        "prebetter_db_available": True,
        "ready": False
    }

    health.update_health_state(ready=True)
    assert health._HEALTH_STATE == {
        "api_start_time": start_time,
        "prelude_db_available": True,
        "prebetter_db_available": True,
        "ready": True
    }

    health.update_health_state(prelude_available=False, ready=False)
    assert health._HEALTH_STATE == {
        "api_start_time": start_time,
        "prelude_db_available": False,
        "prebetter_db_available": True,
        "ready": False
    }


def test_get_health_status_starting():
    """Test status when not ready."""
    status = health.get_health_status()
    assert status.status == "starting"
    assert status.prelude_db is False
    assert status.prebetter_db is False
    assert status.uptime_seconds >= 0
    assert isinstance(status.timestamp, str)

def test_get_health_status_healthy():
    """Test status when all components are healthy and ready."""
    health.update_health_state(prelude_available=True, prebetter_available=True, ready=True)
    status = health.get_health_status()
    assert status.status == "healthy"
    assert status.prelude_db is True
    assert status.prebetter_db is True

def test_get_health_status_degraded():
    """Test status when prebetter db is unavailable."""
    health.update_health_state(prelude_available=True, prebetter_available=False, ready=True)
    status = health.get_health_status()
    assert status.status == "degraded"
    assert status.prelude_db is True
    assert status.prebetter_db is False

def test_get_health_status_unhealthy():
    """Test status when prelude db is unavailable."""
    health.update_health_state(prelude_available=False, prebetter_available=True, ready=True)
    status = health.get_health_status()
    assert status.status == "unhealthy"
    assert status.prelude_db is False
    assert status.prebetter_db is True # Prebetter state doesn't matter if prelude is down

def test_get_health_status_uptime():
    """Test uptime calculation."""
    sleep_time = 0.1
    initial_status = health.get_health_status()
    time.sleep(sleep_time)
    later_status = health.get_health_status()
    assert later_status.uptime_seconds > initial_status.uptime_seconds
    # Check if uptime increased roughly by sleep_time (allow some tolerance)
    assert later_status.uptime_seconds - initial_status.uptime_seconds == pytest.approx(sleep_time, abs=0.05)


def test_check_database_health_prelude_success():
    """Test successful prelude db check."""
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar.return_value = 1 # Simulate successful query
    
    result = health.check_database_health(mock_db, "prelude")
    
    assert result == {"connected": True}
    assert health._HEALTH_STATE["prelude_db_available"] is True
    mock_db.execute.assert_called_once()

def test_check_database_health_prebetter_success():
    """Test successful prebetter db check."""
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar.return_value = 1
    
    result = health.check_database_health(mock_db, "prebetter")
    
    assert result == {"connected": True}
    assert health._HEALTH_STATE["prebetter_db_available"] is True
    mock_db.execute.assert_called_once()

@patch('app.services.health.logger') # Mock logger to suppress error messages during test
def test_check_database_health_prelude_failure(mock_logger):
    """Test failed prelude db check."""
    mock_db = MagicMock()
    error_message = "Connection failed"
    mock_db.execute.side_effect = Exception(error_message)
    
    result = health.check_database_health(mock_db, "prelude")
    
    assert result == {"connected": False, "error": error_message}
    assert health._HEALTH_STATE["prelude_db_available"] is False
    mock_db.execute.assert_called_once()
    mock_logger.error.assert_called_once()

@patch('app.services.health.logger')
def test_check_database_health_prebetter_failure(mock_logger):
    """Test failed prebetter db check."""
    mock_db = MagicMock()
    error_message = "DB error"
    mock_db.execute.side_effect = Exception(error_message)
    
    result = health.check_database_health(mock_db, "prebetter")
    
    assert result == {"connected": False, "error": error_message}
    assert health._HEALTH_STATE["prebetter_db_available"] is False
    mock_db.execute.assert_called_once()
    mock_logger.error.assert_called_once()

def test_check_database_health_invalid_db_type():
    """Test check with an invalid db_type."""
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar.return_value = 1
    
    # Ensure state doesn't change for invalid type
    initial_prelude = health._HEALTH_STATE["prelude_db_available"]
    initial_prebetter = health._HEALTH_STATE["prebetter_db_available"]

    result = health.check_database_health(mock_db, "invalid_db")
    
    assert result == {"connected": True} # Still connects, just doesn't update specific state
    assert health._HEALTH_STATE["prelude_db_available"] == initial_prelude
    assert health._HEALTH_STATE["prebetter_db_available"] == initial_prebetter
    mock_db.execute.assert_called_once()

@patch('app.services.health.logger')
def test_check_database_health_invalid_db_type_failure(mock_logger):
    """Test failure check with an invalid db_type."""
    mock_db = MagicMock()
    error_message = "Failure"
    mock_db.execute.side_effect = Exception(error_message)
    
    # Ensure state doesn't change for invalid type on failure
    initial_prelude = health._HEALTH_STATE["prelude_db_available"]
    initial_prebetter = health._HEALTH_STATE["prebetter_db_available"]

    result = health.check_database_health(mock_db, "invalid_db")
    
    assert result == {"connected": False, "error": error_message} 
    assert health._HEALTH_STATE["prelude_db_available"] == initial_prelude
    assert health._HEALTH_STATE["prebetter_db_available"] == initial_prebetter
    mock_db.execute.assert_called_once()
    mock_logger.error.assert_called_once() # Should still log the error 