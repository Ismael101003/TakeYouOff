# ✈️ OPTI-RUTA SKY - Optimización de Rutas Aéreas Inteligentes

## 🎯 Descripción General

**OPTI-RUTA SKY** es un sistema completo de optimización de rutas aéreas que combina:
- 📡 **Monitoreo de Tráfico Aéreo** (OpenSky Network)
- 🧮 **Solvers Matemáticos** (Wolfram Engine)
- 🤖 **Análisis de Riesgo con IA** (Google Gemini)
- 🔊 **Alertas de Voz** (ElevenLabs)

### Premios Objetivo
✅ Wolfram Award | ✅ Mejor Uso de Gemini | ✅ Mejor Uso de ElevenLabs | ✅ Mejor Despliegue Vultr

---

## 🚀 Quick Start

### Requisitos
- Python 3.10+
- Git
- API Keys (gratuitas):
  - OpenRouter (para Gemini)
  - ElevenLabs (para síntesis de voz)

### Instalación (Windows PowerShell)

```powershell
# Clonar repositorio
git clone https://github.com/Ismael101003/TakeYouOff.git
cd TakeYouOff

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
$env:OPENROUTER_API_KEY = "sk-or-xxxxxxxxxxxx"
$env:ELEVENLABS_API_KEY = "sk_xxxxxxxxxxxx"
$env:DEV_MOCK = "1"  # Para desarrollo sin Wolfram

# Ejecutar
python app.py
```

Acceder a: **http://localhost:5000**

---

## 📡 Endpoints Disponibles

| Endpoint | Método | Descripción |
|:---|:---|:---|
| `/` | GET | Dashboard interactivo |
| `/health` | GET | Health check |
| `/api/vuelos` | GET | Monitoreo OpenSky (conflictos detectados) |
| `/api/optimize-route` | POST | Optimizar ruta (Wolfram + Gemini) |
| `/api/emergency-route` | POST | Ruta de emergencia rápida |
| `/api/conflict-analysis` | POST | Análisis detallado de conflicto |
| `/api/statistics` | GET | Estadísticas en tiempo real |

---

## 🔧 Variables de Entorno

```powershell
# Requeridas para features completos
$env:OPENROUTER_API_KEY = "tu_clave_aqui"      # Gemini Analysis
$env:ELEVENLABS_API_KEY = "tu_clave_aqui"      # Voice Alerts

# Opcionales
$env:DEV_MOCK = "1"                             # Mock mode (sin Wolfram)
$env:WOLFRAM_KERNEL_PATH = "ruta_a_kernel.exe" # Wolfram path
```

---

## 📊 Arquitectura

```
Frontend (HTML/JS)
  ↓ HTTP REST
Backend (Flask)
  ├→ FlightMonitor (OpenSky)
  ├→ Optimizer (Wolfram)
  ├→ AI Analysis (Gemini)
  └→ Alerts (ElevenLabs)
```

---

## 🧪 Testing

```powershell
# Instalar pytest
pip install pytest

# Ejecutar tests
pytest test_app.py -v

# Con coverage
pytest test_app.py --cov=app
```

**Tests incluidos:**
- ✅ Cálculos de distancia geodésica
- ✅ Optimización de rutas (TSP)
- ✅ Endpoints HTTP
- ✅ Detección de conflictos
- ✅ Monitoreo de vuelos

---

## 🐳 Despliegue con Docker

```bash
# Build imagen
docker build -t opti-ruta-sky .

# Run
docker run -p 5000:5000 \
  -e OPENROUTER_API_KEY="tu_clave" \
  -e ELEVENLABS_API_KEY="tu_clave" \
  opti-ruta-sky

# Con Docker Compose
docker-compose up -d
```

---

## 🎮 Modo Desarrollo vs Producción

### Desarrollo (DEV_MOCK=1)
- ✅ Sin necesidad de Wolfram
- ✅ Datos simulados realistas
- ✅ API responses mock
- ⏱️ Iteración rápida

### Producción (DEV_MOCK=0)
- ✅ Wolfram Engine real
- ✅ OpenSky API real
- ✅ Análisis Gemini completo
- ✅ Alertas ElevenLabs auténticas

---

## 📁 Estructura del Proyecto

```
TakeYouOff/
├── app.py                 # Backend principal (Flask)
├── requirements.txt       # Dependencias Python
├── Dockerfile            # Despliegue Docker
├── docker-compose.yml    # Orquestación
├── templates/
│   └── index.html        # Frontend (Leaflet + Chart.js)
├── static/
│   ├── audio/            # Audios generados (ElevenLabs)
│   └── css/             # Estilos
├── test_app.py           # Tests unitarios (pytest)
├── README.md             # Este archivo
├── TECHNICAL.md          # Documentación técnica detallada
└── requirements-dev.txt  # Dev dependencies
```

---

## 🔍 Componentes Clave

### 1. **FlightMonitor** - Sistema de Detección
- Monitorea vuelos en CDMX
- Detecta conflictos de proximidad (<5 km)
- Identifica zonas de restricción
- Genera alertas automáticas

### 2. **Route Optimizer** - Solver Matemático
- Haversine: distancia geodésica
- Algoritmo Greedy + 2-opt para TSP
- Optimización multi-variable
- Integración con Wolfram (producción)

### 3. **Gemini Analysis** - IA Explicable
- Análisis de riesgo estructurado
- Recomendaciones accionables
- Confianza del modelo
- XAI completo

### 4. **ElevenLabs Voice** - Alertas Críticas
- Síntesis de voz natural
- MP3 de alta calidad
- Servido en `/static/audio/`
- Hands-free UX

---

## 🐛 Troubleshooting

| Problema | Solución |
|:---|:---|
| `Chart.js undefined` | Verificar CDN en index.html |
| `/api/vuelos` error | Reiniciar app.py |
| Sin audio de alerta | Verificar ELEVENLABS_API_KEY |
| Wolfram no conecta | Usar DEV_MOCK=1 |

---

## 📚 Recursos

- [Documentación Técnica Completa](./TECHNICAL.md)
- [Wolfram Optimization](https://reference.wolfram.com/language/)
- [Google Gemini API](https://ai.google.dev/)
- [ElevenLabs API](https://elevenlabs.io/docs)
- [OpenSky Network](https://opensky-network.org/)

---

## 👥 Contribuidores

- **Ismael Ruiz** - Programador Principal
- **Kevin ⚡** - Mentor & Estrategia PoliHacks

---

## 📄 Licencia

MIT License - Ver LICENSE.md

---

**Status:** 🎉 Production Ready
**Última actualización:** 23 Nov 2025
**Hackathon:** PoliHacks 2025 (28 horas)
