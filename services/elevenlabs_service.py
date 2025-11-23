"""
Servicio wrapper mínimo para ElevenLabs TTS.
Archivo: services/elevenlabs_service.py
"""
import os
import uuid
from pathlib import Path
from typing import Optional

# Import según la librería instalada en el repo (app.py usa `from elevenlabs import ElevenLabs`)
try:
    from elevenlabs import ElevenLabs
except Exception:
    ElevenLabs = None

AUDIO_FOLDER = Path("static/audio")
AUDIO_FOLDER.mkdir(parents=True, exist_ok=True)


class ElevenLabsService:
    def __init__(self, api_key: Optional[str] = None, voice_id: Optional[str] = None):
        api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY no configurada")

        if ElevenLabs is None:
            raise RuntimeError("SDK de ElevenLabs no disponible. Instala la dependencia 'elevenlabs'.")

        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = voice_id or os.environ.get("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"

    def generate_alert_audio(self, text: str, alert_type: str = "info") -> bytes:
        """Genera y retorna bytes de audio en MP3.

        Ajusta parámetros de "stability" según severidad.
        """
        stability_map = {"danger": 0.3, "warning": 0.5, "info": 0.7}
        stability = stability_map.get(alert_type, 0.7)

        # Usar el método de la SDK para convertir texto a audio.
        # El SDK puede devolver un iterable de chunks o bytes directamente.
        audio_iterable = self.client.text_to_speech.convert(
            text=text,
            voice_id=self.voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_22050_32",
            stability=stability,
        )

        # Normalizar a bytes
        audio_bytes = b""
        try:
            for chunk in audio_iterable:
                audio_bytes += chunk
        except TypeError:
            # Si la SDK devuelve bytes
            audio_bytes = audio_iterable

        return audio_bytes

    def save_audio_file(self, audio_bytes: bytes, prefix: str = "alert") -> str:
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.mp3"
        path = AUDIO_FOLDER / filename
        with open(path, "wb") as f:
            f.write(audio_bytes)
        return str(path)
