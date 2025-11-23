import os
import pytest
from services import opensky_api, elevenlabs_service


def test_opensky_missing_env():
    # Ensure env vars not set
    os.environ.pop("OPENSKY_CLIENT_ID", None)
    os.environ.pop("OPENSKY_CLIENT_SECRET", None)
    with pytest.raises(RuntimeError):
        opensky_api.get_opensky_token()


def test_elevenlabs_missing_key():
    os.environ.pop("ELEVENLABS_API_KEY", None)
    # If 'elevenlabs' SDK isn't installed the constructor raises RuntimeError too
    with pytest.raises(RuntimeError):
        elevenlabs_service.ElevenLabsService()
