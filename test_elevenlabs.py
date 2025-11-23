#!/usr/bin/env python
"""
Script de prueba para ElevenLabs
"""

import os
from pathlib import Path

API_KEY = os.environ.get("ELEVENLABS_API_KEY")

print("=" * 70)
print("PRUEBA DE ELEVENLABS")
print("=" * 70)

if not API_KEY:
    print("\n✗ ERROR: Variable de entorno ELEVENLABS_API_KEY no está configurada")
    print("\nPara configurarla en PowerShell:")
    print('  $env:ELEVENLABS_API_KEY = "tu-clave-aqui"')
    print("\nO en Command Prompt:")
    print('  set ELEVENLABS_API_KEY=tu-clave-aqui')
    print("\nObtén tu clave en: https://elevenlabs.io/app/settings/api-keys")
    exit(1)

print(f"\n✓ Clave API encontrada: {API_KEY[:10]}...")

try:
    print("\n1. Importando ElevenLabs...")
    from elevenlabs import ElevenLabs
    print("   ✓ Importación exitosa")
    
    print("\n2. Inicializando cliente...")
    client = ElevenLabs(api_key=API_KEY)
    print("   ✓ Cliente inicializado")
    
    print("\n3. Probando generación de audio...")
    message = "Alerta crítica: La ruta óptima excede los límites de seguridad."
    
    print(f"   Mensaje: '{message}'")
    print("   Generando audio... (esto puede tardar unos segundos)")
    
    # Usar text_to_speech que es el método correcto
    audio = client.text_to_speech.convert(
        text=message,
        voice_id="EXAVITQu4vr4xnSDxMaL",  # Bella
        model_id="eleven_multilingual_v2",
        output_format="mp3_22050_32"
    )
    
    print("   ✓ Audio generado exitosamente")
    
    # Guardar el audio
    print("\n4. Guardando audio...")
    audio_folder = Path("static/audio")
    audio_folder.mkdir(parents=True, exist_ok=True)
    
    audio_path = audio_folder / "test_alert.mp3"
    with open(audio_path, 'wb') as f:
        for chunk in audio:
            f.write(chunk)
    
    file_size = audio_path.stat().st_size
    print(f"   ✓ Audio guardado en: {audio_path}")
    print(f"   Tamaño: {file_size / 1024:.2f} KB")
    
    print("\n✓ TODAS LAS PRUEBAS PASARON")
    print(f"\nPuedes escuchar el audio en: /static/audio/test_alert.mp3")
    
except ImportError as e:
    print(f"\n✗ ERROR: No se pudo importar ElevenLabs")
    print(f"   Instala con: pip install elevenlabs")
    print(f"   Error: {e}")
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    print("\nDetalles:")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
