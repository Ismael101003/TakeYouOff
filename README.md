# TakeYouOff (Opti-Ruta Sky)

Proyecto demo: frontend (Leaflet + Chart.js) + backend Flask que usa Wolfram Engine para optimizar rutas.

Requisitos mínimos

- Python 3.10+
- Wolfram Engine / Mathematica (WolframKernel) instalado si desea usar el motor real.

Instalación rápida (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Variables de entorno importantes

- `WOLFRAM_KERNEL_PATH` — ruta absoluta al `WolframKernel.exe` (opcional; hay un valor por defecto en `app.py`).
- `OPENROUTER_API_KEY` — clave para OpenRouter / Gemini (si usas análisis IA).
- `ELEVENLABS_API_KEY` — clave para ElevenLabs (si quieres audio real).
- `DEV_MOCK` — (valor `1`) activa modo mock para desarrollo sin Wolfram Kernel.

Cómo ejecutar

```powershell
$env:DEV_MOCK = "1"  # opcional para desarrollo sin Kernel
python app.py
```

Endpoints

- `GET /` — dashboard UI (templates/index.html)
- `POST /api/optimize-route` — calcula ruta óptima. En modo mock devuelve datos de ejemplo.
- `GET /health` — healthcheck (200 OK)

Notas

- Si el frontend muestra consola con `ReferenceError: Chart is not defined`, asegúrate de que `templates/index.html` carga Chart.js desde CDN (ya incluido).
- Para desarrollo sin Wolfram, activa `DEV_MOCK=1`.

Siguientes pasos recomendados

- Implementar tests unitarios y de integración.
- Añadir manejo de almacenamiento/serving de audio real para ElevenLabs.
- Revisar y adaptar la llamada a OpenRouter según su documentación actual.
