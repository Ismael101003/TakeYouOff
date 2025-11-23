#!/usr/bin/env python
"""
Setup script para Opti-Ruta Sky
Configura el entorno automáticamente
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_environment():
    """Configura el entorno para desarrollo."""
    
    print("=" * 60)
    print("🚀 OPTI-RUTA SKY - Setup Automático")
    print("=" * 60)
    
    # 1. Verificar Python version
    print("\n✓ Verificando versión de Python...")
    if sys.version_info < (3, 10):
        print("❌ Se requiere Python 3.10+")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} detectado")
    
    # 2. Crear carpetas necesarias
    print("\n✓ Creando estructura de carpetas...")
    folders = ['static/audio', 'logs', '.github/workflows']
    for folder in folders:
        Path(folder).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {folder}/")
    
    # 3. Instalar dependencias
    print("\n✓ Instalando dependencias...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencias instaladas correctamente")
    except subprocess.CalledProcessError:
        print("❌ Error al instalar dependencias")
        sys.exit(1)
    
    # 4. Variables de entorno
    print("\n✓ Configurando variables de entorno...")
    env_template = """
# Copiar estas líneas en tu terminal PowerShell:

# Para Desarrollo (con Mock)
$env:DEV_MOCK = "1"
$env:OPENROUTER_API_KEY = "tu_clave_aqui"
$env:ELEVENLABS_API_KEY = "tu_clave_aqui"

# Para Producción
$env:DEV_MOCK = "0"
$env:OPENROUTER_API_KEY = "tu_clave_aqui"
$env:ELEVENLABS_API_KEY = "tu_clave_aqui"
    """
    print(env_template)
    
    # 5. Verificar archivos clave
    print("\n✓ Verificando archivos del proyecto...")
    required_files = ['app.py', 'requirements.txt', 'templates/index.html']
    for file in required_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ⚠️  {file} - NO ENCONTRADO")
    
    # 6. Health check
    print("\n✓ Ejecutando health check...")
    try:
        import app as test_import
        print("✅ app.py importa correctamente")
    except Exception as e:
        print(f"⚠️  Error al importar app.py: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Setup completado exitosamente")
    print("=" * 60)
    print("\n📝 Próximos pasos:")
    print("1. Configurar variables de entorno (ver arriba)")
    print("2. Ejecutar: python app.py")
    print("3. Abrir: http://localhost:5000")
    print("4. Para tests: pytest test_app.py -v")
    print("\n📚 Documentación: Ver README_NEW.md y TECHNICAL.md")
    print("=" * 60)

if __name__ == '__main__':
    setup_environment()
