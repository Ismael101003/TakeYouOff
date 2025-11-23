from flask import Flask, jsonify, render_template, request
from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wl

import os
import requests 
import random   
import json     
import logging
import uuid
from threading import Lock
from pathlib import Path

try:
    from flask_cors import CORS
    _HAS_CORS = True
except Exception:
    _HAS_CORS = False

from elevenlabs import ElevenLabs
import base64


# Asegúrate de haber instalado: pip install google-genai
from google import genai
# -----------------------------------------------------------

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Crear carpeta de audios si no existe
AUDIO_FOLDER = Path('static/audio')
AUDIO_FOLDER.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno desde un archivo .env (si existe)
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info(".env cargado (si estaba presente).")
except Exception:
    # Si python-dotenv no está instalado, continuamos y usamos las env vars del sistema
    logger.debug("python-dotenv no está disponible; usando variables de entorno del sistema.")

# ===================================================================
# 1. CONFIGURACIÓN DE LLAVES Y KERNEL (Variables de Entorno)
# ===================================================================

# A. Wolfram Kernel Path (La ruta que encontraste y te funcionó)
KERNEL_PATH = os.environ.get("WOLFRAM_KERNEL_PATH", r"C:\Program Files\Wolfram Research\Wolfram\14.3\WolframKernel.exe")

# B. APIs Externas (Se recuperan de las variables de entorno)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
# Leer la clave de ElevenLabs correctamente desde la variable de entorno
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

# C. Configuración de OpenRouter
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Modo de desarrollo: si se activa, el endpoint devuelve rutas mock sin necesitar Wolfram
DEV_MOCK = os.environ.get("DEV_MOCK", "0") == "1"


# ===================================================================
# 2. CONEXIÓN AL MOTOR DE WOLFRAM
# ===================================================================

# ===================================================================
# 2. CONEXIÓN AL MOTOR DE WOLFRAM (usando implementación Python puro)
# ===================================================================

from math import radians, cos, sin, asin, sqrt

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia entre dos puntos en km usando la fórmula haversine
    (aproximación de la distancia geodésica)
    """
    # Convertir a radianes
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Diferencias
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Fórmula haversine
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radio de la Tierra en km
    km = 6371 * c
    return km


def find_shortest_tour(points):
    """
    Implementación simplificada del algoritmo del viajante de comercio (TSP)
    usando una heurística greedy + 2-opt.
    
    Retorna [distancia_total, ruta_optimizada]
    """
    if not points or len(points) <= 1:
        return [0, points]
    
    n = len(points)
    
    # 1. Heurística greedy: comenzar desde el primer punto
    tour = [0]  # Comenzar en el punto 0
    unvisited = set(range(1, n))
    
    while unvisited:
        current = tour[-1]
        nearest = min(unvisited, key=lambda j: haversine_distance(
            points[current][0], points[current][1],
            points[j][0], points[j][1]
        ))
        tour.append(nearest)
        unvisited.remove(nearest)
    
    # 2. Calcular distancia total
    total_distance = 0
    # Distancia como TRAYECTO (one-way): sumar solo aristas consecutivas sin volver al origen
    for i in range(len(tour) - 1):
        current = tour[i]
        next_point = tour[i + 1]
        total_distance += haversine_distance(
            points[current][0], points[current][1],
            points[next_point][0], points[next_point][1]
        )
    
    # 3. Aplicar mejora 2-opt (opcional, pero mejora significativamente)
    improved = True
    iterations = 0
    max_iterations = 100
    
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        
        for i in range(n - 1):
            for j in range(i + 2, n):
                if j - i == 1:
                    continue
                
                # Calcular el cambio de distancia si invertimos el segmento
                curr_dist = (
                    haversine_distance(points[tour[i]][0], points[tour[i]][1],
                                      points[tour[i+1]][0], points[tour[i+1]][1]) +
                    haversine_distance(points[tour[j]][0], points[tour[j]][1],
                                      points[tour[(j+1) % n]][0], points[tour[(j+1) % n]][1])
                )
                
                new_dist = (
                    haversine_distance(points[tour[i]][0], points[tour[i]][1],
                                      points[tour[j]][0], points[tour[j]][1]) +
                    haversine_distance(points[tour[i+1]][0], points[tour[i+1]][1],
                                      points[tour[(j+1) % n]][0], points[tour[(j+1) % n]][1])
                )
                
                # Si es mejor, hacer el cambio
                if new_dist < curr_dist:
                    tour[i+1:j+1] = reversed(tour[i+1:j+1])
                    # Actualizamos total_distance localmente (se recalculará exactamente al final)
                    total_distance = total_distance - curr_dist + new_dist
                    improved = True
                    break
            if improved:
                break
    
    # Convertir índices a coordenadas reales
    ruta_optimizada = [points[i] for i in tour]

    # Recalcular distancia exacta como suma de segmentos consecutivos (one-way)
    total_distance = 0
    for i in range(len(tour) - 1):
        a = tour[i]
        b = tour[i + 1]
        total_distance += haversine_distance(points[a][0], points[a][1], points[b][0], points[b][1])

    return [total_distance, ruta_optimizada]


def optimize_route_wolfram(origen, destino, restricciones):
    """
    Simula OptimizeRoute de Wolfram usando Python puro.
    Retorna un diccionario con el resultado.
    """
    try:
        # Construir lista de puntos: origen + restricciones + destino
        puntos_de_control = [origen] + restricciones + [destino]
        
        logger.info("Calculando ruta óptima para %d puntos", len(puntos_de_control))
        
        # Encontrar la ruta más corta
        distancia_total, ruta_final = find_shortest_tour(puntos_de_control)
        
        logger.info("Ruta calculada: %.2f km", distancia_total)
        
        # Retornar resultado en formato compatible
        return {
            "Status": "Optimizado con Éxito",
            "RutaTotalKM": round(distancia_total, 2),
            "RutaOptimizada": ruta_final,
            "Mensaje": "Ruta calculada con éxito. Listo para el análisis de IA."
        }
        
    except Exception as e:
        logger.error("ERROR calculando ruta: %s", e)
        return None


# ===================================================================
# 3. SISTEMA DE MONITOREO OPENSKY (Simulador + API Real)
# ===================================================================

class FlightMonitor:
    """Sistema de monitoreo de tráfico aéreo con detección de conflictos."""
    
    def __init__(self):
        self.flights = []
        self.conflict_zones = [
            {"lat": 19.5, "lon": -99.5, "radius": 15, "name": "CDMX Centro"},
            {"lat": 19.4, "lon": -99.3, "radius": 10, "name": "Zona Este"}
        ]
        self.known_conflicts = set()
        self._generate_mock_flights()
    
    def _generate_mock_flights(self):
        """Genera vuelos simulados para demo."""
        self.flights = [
            {
                "icao24": "a0a1b2c3",
                "callsign": "AM456",
                "lat": 19.45,
                "lon": -99.25,
                "alt": 2500,
                "velocity": 450,
                "heading": 90,
                "type": "pasajero",
                "origin": "BENITO JUÁREZ",
                "destination": "QUERÉTARO"
            },
            {
                "icao24": "d4e5f6g7",
                "callsign": "AM789",
                "lat": 19.55,
                "lon": -99.35,
                "alt": 3000,
                "velocity": 420,
                "heading": 180,
                "type": "carga",
                "origin": "CDMX",
                "destination": "GUADALAJARA"
            },
            {
                "icao24": "h8i9j0k1",
                "callsign": "AM123",
                "lat": 19.48,
                "lon": -99.28,
                "alt": 2800,
                "velocity": 410,
                "heading": 270,
                "type": "pasajero",
                "origin": "TLAXCALA",
                "destination": "CDMX"
            },
            {
                "icao24": "l2m3n4o5",
                "callsign": "CARGO-01",
                "lat": 19.52,
                "lon": -99.50,
                "alt": 3500,
                "velocity": 480,
                "heading": 45,
                "type": "carga",
                "origin": "CDMX",
                "destination": "TOLUCA"
            }
        ]
    
    def fetch_opensky_data(self):
        """Fetch real OpenSky data (usa OpenSky API si hay credenciales; si no, simula).

        Intento de comportamiento:
        1. Si existen `OPENSKY_CLIENT_ID` y `OPENSKY_CLIENT_SECRET` en el entorno,
           intenta llamar a `services.opensky_api.get_flights(...)` con el bounding box
           definido en `OPENSKY_BOUNDS` o el por defecto.
        2. Si falla la llamada real por cualquier motivo, cae al modo simulación
           (movimiento aleatorio de vuelos mock) para mantener la demo funcional.
        """
        try:
            # Si están disponibles las credenciales, intentar fetch real
            if os.environ.get("OPENSKY_CLIENT_ID") and os.environ.get("OPENSKY_CLIENT_SECRET"):
                try:
                    # Use the OpenSkyApi class from the bundled client library
                    from services.opensky_api import OpenSkyApi

                    # OPENSKY_BOUNDS esperado: lat_min,lon_min,lat_max,lon_max
                    bounds = os.environ.get("OPENSKY_BOUNDS", "18.0,-100.0,21.0,-98.0").split(",")
                    if len(bounds) == 4:
                        lat_min = float(bounds[0])
                        lon_min = float(bounds[1])
                        lat_max = float(bounds[2])
                        lon_max = float(bounds[3])
                    else:
                        lat_min, lon_min, lat_max, lon_max = 18.0, -100.0, 21.0, -98.0

                    client = OpenSkyApi(username=os.environ.get("OPENSKY_CLIENT_ID"), password=os.environ.get("OPENSKY_CLIENT_SECRET"))

                    # Note: OpenSkyApi.get_states expects bbox as (min_lat, max_lat, min_lon, max_lon)
                    states_obj = client.get_states(time_secs=0, bbox=(lat_min, lat_max, lon_min, lon_max))

                    flights = []
                    if states_obj and getattr(states_obj, 'states', None):
                        for sv in states_obj.states:
                            try:
                                lat = getattr(sv, 'latitude', None)
                                lon = getattr(sv, 'longitude', None)
                                alt = getattr(sv, 'geo_altitude', None) or getattr(sv, 'baro_altitude', None)
                                velocity = getattr(sv, 'velocity', None)
                                # velocity from OpenSky is m/s; keep as-is or convert as needed
                                flights.append({
                                    "icao24": getattr(sv, 'icao24', None),
                                    "callsign": getattr(sv, 'callsign', None),
                                    "lat": lat,
                                    "lon": lon,
                                    "alt": alt,
                                    "velocity": velocity,
                                    "heading": getattr(sv, 'true_track', None),
                                    "type": "desconocido",
                                    "origin": getattr(sv, 'origin_country', None),
                                    "destination": None,
                                })
                            except Exception:
                                continue

                    if flights:
                        self.flights = flights
                        logger.info("OpenSky: fetched %d flights", len(self.flights))
                        return self.flights
                except Exception as e:
                    logger.warning("OpenSky real fetch failed, falling back to mock: %s", e)

            # Fallback: simulación local (mantener comportamiento anterior)
            for flight in self.flights:
                # Simular movimiento
                flight["lat"] += random.uniform(-0.02, 0.02)
                flight["lon"] += random.uniform(-0.02, 0.02)
                # Ajustar altitud con un pequeño delta
                try:
                    flight["alt"] = (flight.get("alt") or 3000) + random.randint(-100, 100)
                except Exception:
                    flight["alt"] = flight.get("alt", 3000)

            logger.info(f"Monitoreo (mock): {len(self.flights)} vuelos activos en CDMX")
            return self.flights
        except Exception as e:
            logger.error("Error fetching OpenSky (general): %s", e)
            return []
    
    def detect_conflicts(self):
        """Detecta conflictos entre vuelos y zonas de restricción."""
        conflicts = []
        alerts = []
        
        # 1. Conflictos entre vuelos (proximidad)
        for i in range(len(self.flights)):
            for j in range(i + 1, len(self.flights)):
                f1, f2 = self.flights[i], self.flights[j]
                
                # Calcular distancia 3D (lat, lon, altitud)
                dist_horizontal = haversine_distance(
                    f1['lat'], f1['lon'],
                    f2['lat'], f2['lon']
                )
                dist_vertical = abs(f1['alt'] - f2['alt']) / 1000  # convertir a km
                dist_3d = (dist_horizontal**2 + dist_vertical**2)**0.5
                
                # Si están a menos de 5 km en 3D, es un conflicto
                if dist_3d < 5:
                    conflict_id = f"{f1['icao24']}-{f2['icao24']}"
                    if conflict_id not in self.known_conflicts:
                        self.known_conflicts.add(conflict_id)
                        conflicts.append({
                            "type": "proximitad",
                            "flight1": f1['callsign'],
                            "flight2": f2['callsign'],
                            "distance_km": round(dist_3d, 2),
                            "severity": "crítica" if dist_3d < 2 else "alta"
                        })
                        alerts.append({
                            "title": "⚠️ Conflicto de Proximidad",
                            "message": f"{f1['callsign']} y {f2['callsign']} a {dist_3d:.1f} km",
                            "severity": "danger"
                        })
        
        # 2. Conflictos en zonas de restricción
        for flight in self.flights:
            for zone in self.conflict_zones:
                dist = haversine_distance(
                    flight['lat'], flight['lon'],
                    zone['lat'], zone['lon']
                )
                
                if dist < zone['radius']:
                    zone_id = f"{flight['icao24']}-{zone['name']}"
                    if zone_id not in self.known_conflicts:
                        self.known_conflicts.add(zone_id)
                        severity_level = "crítica" if dist < zone['radius']/2 else "alta"
                        alerts.append({
                            "title": f"⚡ Zona Restringida: {zone['name']}",
                            "message": f"{flight['callsign']} en zona de restricción",
                            "severity": "warning" if severity_level == "alta" else "danger"
                        })
        
        return conflicts, alerts


# Instancia global del monitor
flight_monitor = FlightMonitor()


# ===================================================================
# 4. CONEXIÓN AL CLIENTE ELEVENLABS
# ===================================================================

ELEVENLABS_CLIENT = None
if ELEVENLABS_API_KEY:
    try:
        # Inicializa el cliente ElevenLabs
        ELEVENLABS_CLIENT = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        logger.info("SERVERS: ElevenLabs Client Inicializado.")
    except Exception as e:
        logger.error("ERROR: Falló al inicializar ElevenLabs. %s", e)

# Enable CORS if available (helps when frontend served from different origin)
if _HAS_CORS:
    CORS(app)
    logger.info("CORS habilitado (flask_cors detected).")


# --- Gemini API vía OpenRouter (Explicabilidad de IA) ---
def call_gemini_analysis(route_data_str):
    """Genera un análisis contextual sobre el riesgo de la ruta vía OpenRouter."""
    
    if not OPENROUTER_API_KEY:
        return "OpenRouter Desconectado. (Clave API no configurada)"

    # Prompt mejorado para forzar una salida estructurada y de valor (XAI Avanzada)
    if isinstance(route_data_str, dict):
        # Si recibimos un dict, convertirlo a JSON
        prompt_text = f"Eres un experto en seguridad aérea y optimización de rutas. Analiza este escenario de tráfico aéreo:\n\n{json.dumps(route_data_str, indent=2)}\n\nProporciona:\n1. EVALUACIÓN DE RIESGO (Crítico/Alto/Medio/Bajo)\n2. FACTORES CLAVE que afectan la seguridad\n3. RECOMENDACIONES ACCIONABLES para el controlador\n4. CONFIANZA DEL MODELO (0-100%)"
    else:
        # Análisis de ruta geodésica
        prompt_text = (
            f"Eres un analista de seguridad aérea y modelador de riesgos. Analiza los siguientes datos numéricos de cálculo de ruta geodésica (Wolfram): {route_data_str}. "
            "Tu tarea es generar un informe contextual y accionable. "
            "1. RESUMEN CRÍTICO (Tono urgente, máximo 3 oraciones): Identifica la principal causa de riesgo (ej: 'ruta excesivamente larga' o 'múltiples restricciones'). "
            "2. RECOMENDACIONES DE MITIGACIÓN (Lista de 3 puntos): Ofrece acciones concretas y verificables para el piloto que minimicen el riesgo. "
            "3. CONFIANZA DEL ANÁLISIS: % de confianza en la recomendación basado en datos disponibles. "
            "Formatea tu respuesta en un solo bloque de texto claro y profesional."
        )
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "google/gemini-2.5-pro", 
            "messages": [
                {"role": "user", "content": prompt_text}
            ]
        }

        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()

        # Defensive access: ensure expected structure
        data = response.json()
        try:
            return data['choices'][0]['message']['content']
        except Exception:
            logger.error("Respuesta inesperada de OpenRouter: %s", data)
            return "Error en la llamada a OpenRouter: respuesta inesperada."

    except requests.exceptions.RequestException as e:
        logger.error("Error en la llamada a OpenRouter: %s", e)
        return "Error en la llamada a OpenRouter: No se pudo obtener el análisis."


# --- ElevenLabs API (Voz de Alerta) ---
def call_elevenlabs_alert(message, save_to_file=False):
    """
    Genera audio de alerta usando ElevenLabs y lo guarda localmente.
    Retorna la URL del archivo de audio para que el frontend lo reproduzca.
    """
    
    if not ELEVENLABS_CLIENT:
        logger.warning("ALERTA: Cliente ElevenLabs no inicializado. No se generará audio.")
        return None 
    
    try:
        logger.info("ALERTA: Generando audio de voz con ElevenLabs...")

        # Generar audio usando ElevenLabs (método correcto: text_to_speech)
        audio_iter = ELEVENLABS_CLIENT.text_to_speech.convert(
            text=message,
            voice_id="EXAVITQu4vr4xnSDxMaL",
            model_id="eleven_multilingual_v2",
            output_format="mp3_22050_32"
        )

        # Recolectar bytes en memoria
        try:
            audio_bytes = b"".join(audio_iter)
        except TypeError:
            # Si el iterador devuelve chunks que no son exactamente bytes, try to concatenate
            audio_bytes = b""
            for chunk in audio_iter:
                if isinstance(chunk, (bytes, bytearray)):
                    audio_bytes += bytes(chunk)
                else:
                    # fall back: if chunk is str, encode
                    audio_bytes += str(chunk).encode('utf-8')

        if save_to_file:
            # Generar nombre único para el archivo
            audio_filename = f"alert_{uuid.uuid4().hex[:8]}.mp3"
            audio_path = AUDIO_FOLDER / audio_filename
            with open(audio_path, 'wb') as f:
                f.write(audio_bytes)
            audio_url = f"/static/audio/{audio_filename}"
            logger.info("ALERTA: Audio guardado en %s", audio_url)
            return audio_url

        # Si no se guarda, devolver como data URL base64 para reproducción inmediata en frontend
        b64 = base64.b64encode(audio_bytes).decode('ascii')
        data_url = f"data:audio/mpeg;base64,{b64}"
        return data_url
        
    except Exception as e:
        logger.error("Error al generar audio con ElevenLabs: %s", e)
        logger.error("Detalles:", exc_info=True)
        return None


# ===================================================================
# 5. RUTAS WEB Y API (El Cerebro)
# ===================================================================

@app.route('/')
def index():
    """Ruta principal que sirve el dashboard."""
    return render_template('index.html')


@app.route('/api/optimize-route', methods=['POST'])
def optimize_route():
    """
    Recibe la solicitud del Frontend, llama a Wolfram para el cálculo,
    y orquesta las llamadas de ElevenLabs y Gemini.
    """
    # Modo mock para desarrollo: responde sin Wolfram si DEV_MOCK=1
    data = request.json or {}
    origen_list = data.get('origen')
    destino_list = data.get('destino')
    restricciones = data.get('restricciones', [])

    if DEV_MOCK:
        # Validación básica
        try:
            lat1, lon1 = float(origen_list[0]), float(origen_list[1])
            lat2, lon2 = float(destino_list[0]), float(destino_list[1])
        except Exception:
            return jsonify({"error": "Formato inválido en origen/destino para modo mock."}), 400

        mock_coords = [
            {"lat": lat1, "lon": lon1},
            {"lat": (lat1+lat2)/2, "lon": (lon1+lon2)/2},
            {"lat": lat2, "lon": lon2}
        ]
        mock_km = round(random.uniform(30, 600))
        return jsonify({
            "status": "success",
            "ruta_km": mock_km,
            "ruta_coordenadas": mock_coords,
            "is_critical_alert": (mock_km > 500 or len(restricciones) >= 3),
            "analisis_ia_texto": "Modo MOCK: análisis simulado.",
            "audio_alert_url": None,
            "analisis_simulacion": {"riesgo_alto": round(10 + len(restricciones) * 5 + mock_km / 100), "riesgo_exito": round(90 - len(restricciones) * 5 - mock_km / 100)}
        })

    try:
        # Validación básica de entrada
        def valid_coord(c):
            try:
                return isinstance(c, (list, tuple)) and len(c) == 2 and all(isinstance(float(x), float) for x in c)
            except Exception:
                return False

        if not valid_coord(origen_list) or not valid_coord(destino_list):
            return jsonify({"error": "Los campos 'origen' y 'destino' deben ser listas [lat, lon] con valores numéricos."}), 400
        
        # --- 5.1 LLAMADA AL MOTOR WOLFRAM (usando wolframscript) ---
        logger.info("Llamando a optimize_route_wolfram...")
        wolfram_result = optimize_route_wolfram(origen_list, destino_list, restricciones)
        
        if wolfram_result is None:
            return jsonify({"error": "Motor Wolfram no respondió. Contacte al Modelador."}), 503
        
        # --- 5.2 PROCESAMIENTO Y NORMALIZACIÓN DE RESULTADOS ---
        
        # Extracción de la distancia
        ruta_km = 0
        wolfram_result_dict = wolfram_result
        
        if isinstance(wolfram_result_dict, dict):
            if 'RutaTotalKM' in wolfram_result_dict:
                try:
                    ruta_km = float(wolfram_result_dict['RutaTotalKM'])
                except (ValueError, TypeError):
                    ruta_km = 0
        
        # 🚩 NORMALIZACIÓN DE COORDENADAS
        wolfram_coords = wolfram_result_dict.get('RutaOptimizada', [])
        ruta_coordenadas_normalizadas = []

        if isinstance(wolfram_coords, list):
            for p in wolfram_coords:
                if isinstance(p, (list, tuple)) and len(p) == 2:
                    try:
                        ruta_coordenadas_normalizadas.append({"lat": float(p[0]), "lon": float(p[1])})
                    except (ValueError, TypeError):
                        logger.warning("Advertencia: Coordenadas de Wolfram no son numéricas.")
                        pass
        
        # Prepara los datos estructurados para Gemini
        datos_para_gemini = {
            "RutaTotalKM": round(ruta_km, 2),
            "NumeroRestricciones": len(restricciones),
            "PuntoOrigen": origen_list,
            "PuntoDestino": destino_list,
            "RutaTienePuntosIntermedios": len(ruta_coordenadas_normalizadas) > 2,
        }
        wolfram_result_str = json.dumps(datos_para_gemini)

        # --- 5.3 LÓGICA DEL TRIGGER CRÍTICO (T-A5) ---
        is_critical = (ruta_km > 500 or len(restricciones) >= 3)

        # --- 5.4 LLAMADA A GEMINI (OpenRouter) ---
        gemini_analysis = call_gemini_analysis(wolfram_result_str)

        # --- 5.5 LLAMADA A ELEVENLABS ---
        audio_alert_url = None
        audio_alert_data = None
        if is_critical:
            alert_message = f"ALERTA CRÍTICA: La ruta óptima excede los {int(ruta_km)} kilómetros y presenta alto riesgo. Verifique el análisis de Gemini."
            # No guardar archivo en disco; obtener data URL para reproducción en frontend
            audio_alert_data = call_elevenlabs_alert(alert_message, save_to_file=False)
            
        # 5. Respuesta Final para el Frontend
        return jsonify({
            "status": "success",
            "ruta_km": int(ruta_km),
            "ruta_coordenadas": ruta_coordenadas_normalizadas,
            "is_critical_alert": is_critical,
            "analisis_ia_texto": gemini_analysis,
            "audio_alert_url": audio_alert_url,
            "audio_alert_data": audio_alert_data,
            "analisis_simulacion": {"riesgo_alto": round(10 + len(restricciones) * 5 + ruta_km / 100), "riesgo_exito": round(90 - len(restricciones) * 5 - ruta_km / 100)} 
        })

    except Exception as e:
        logger.exception("Error en el endpoint optimize-route: %s", e)
        return jsonify({"error": f"Error interno del servidor: {e}"}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health endpoint simple."""
    return jsonify({"status": "ok", "dev_mock": DEV_MOCK})


# ===================================================================
# 6. NUEVOS ENDPOINTS PARA OPTI-RUTA SKY (OpenSky Monitoring)
# ===================================================================

@app.route('/api/vuelos', methods=['GET'])
def get_vuelos():
    """
    Endpoint de monitoreo OpenSky.
    Retorna vuelos activos en CDMX y detecta conflictos.
    Integración con el frontend para monitoreo en tiempo real.
    """
    try:
        # Actualizar datos de vuelos
        flight_monitor.fetch_opensky_data()
        
        # Detectar conflictos
        conflicts, alerts = flight_monitor.detect_conflicts()
        
        return jsonify({
            "status": "ok",
            "vuelos": flight_monitor.flights,
            "conflictos": conflicts,
            "alerts": alerts,
            "total_vuelos": len(flight_monitor.flights),
            "total_conflictos": len(conflicts)
        })
    
    except Exception as e:
        logger.error(f"Error en endpoint vuelos: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/conflict-analysis', methods=['POST'])
def analyze_conflict():
    """
    Análisis detallado de conflicto específico usando Gemini.
    Input: dos vuelos con conflicto detectado.
    Output: recomendación de desvío y análisis de riesgo.
    """
    try:
        data = request.json or {}
        flight1 = data.get('flight1', {})
        flight2 = data.get('flight2', {})
        
        if not flight1 or not flight2:
            return jsonify({"error": "Vuelos requeridos"}), 400
        
        # Preparar contexto para Gemini
        context = {
            "vuelo1": {
                "callsign": flight1.get('callsign'),
                "alt": flight1.get('alt'),
                "heading": flight1.get('heading'),
                "velocity": flight1.get('velocity'),
                "origin": flight1.get('origin')
            },
            "vuelo2": {
                "callsign": flight2.get('callsign'),
                "alt": flight2.get('alt'),
                "heading": flight2.get('heading'),
                "velocity": flight2.get('velocity'),
                "origin": flight2.get('origin')
            }
        }
        
        # Llamar a Gemini para análisis
        prompt = (
            f"Eres un controlador aéreo experto. Analiza este conflicto de tráfico aéreo:\n\n"
            f"Vuelo 1 ({context['vuelo1']['callsign']}): Altitud {context['vuelo1']['alt']}ft, "
            f"Rumbo {context['vuelo1']['heading']}°, Velocidad {context['vuelo1']['velocity']}km/h\n"
            f"Vuelo 2 ({context['vuelo2']['callsign']}): Altitud {context['vuelo2']['alt']}ft, "
            f"Rumbo {context['vuelo2']['heading']}°, Velocidad {context['vuelo2']['velocity']}km/h\n\n"
            f"Proporciona:\n"
            f"1. RIESGO INMEDIATO: Evaluación rápida (Alto/Medio/Bajo)\n"
            f"2. ACCIÓN RECOMENDADA: Qué debe hacer cada vuelo\n"
            f"3. JUSTIFICACIÓN MATEMÁTICA: Por qué esta solución es óptima\n"
        )
        
        analysis = call_gemini_analysis(prompt)
        
        return jsonify({
            "status": "ok",
            "conflict_analysis": analysis,
            "context": context
        })
    
    except Exception as e:
        logger.error(f"Error en conflict-analysis: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/emergency-route', methods=['POST'])
def emergency_route():
    """
    Calcula ruta de emergencia rápida cuando hay conflicto.
    Similar a optimize-route pero con constraints críticos.
    """
    try:
        data = request.json or {}
        flight_position = data.get('flight_position')  # [lat, lon]
        destination = data.get('destination')  # [lat, lon]
        restricted_zones = data.get('restricted_zones', [])
        
        if not flight_position or not destination:
            return jsonify({"error": "flight_position y destination requeridos"}), 400
        
        # Usar el mismo solver que optimize-route
        result = optimize_route_wolfram(flight_position, destination, restricted_zones)
        
        if result is None:
            return jsonify({"error": "No se pudo calcular ruta de emergencia"}), 503
        
        # Generar alerta crítica de voz (no guardamos el audio, devolvemos data URL)
        alert_msg = f"Ruta de emergencia calculada: {result['RutaTotalKM']} kilómetros. Siga las coordenadas en pantalla."
        audio_data = call_elevenlabs_alert(alert_msg, save_to_file=False)
        
        return jsonify({
            "status": "success",
            "emergency_route": result['RutaOptimizada'],
            "total_km": result['RutaTotalKM'],
            "audio_alert": None,
            "audio_alert_data": audio_data,
            "timestamp": str(__import__('datetime').datetime.now())
        })
    
    except Exception as e:
        logger.error(f"Error en emergency-route: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Estadísticas del sistema para dashboard."""
    try:
        total_flights = len(flight_monitor.flights)
        cargo_flights = len([f for f in flight_monitor.flights if f['type'] == 'carga'])
        passenger_flights = total_flights - cargo_flights
        
        # Calcular altitud promedio
        avg_alt = sum(f['alt'] for f in flight_monitor.flights) / total_flights if total_flights > 0 else 0
        
        return jsonify({
            "status": "ok",
            "total_flights": total_flights,
            "cargo_flights": cargo_flights,
            "passenger_flights": passenger_flights,
            "average_altitude": round(avg_alt, 0),
            "conflict_zones": len(flight_monitor.conflict_zones),
            "active_monitoring": True
        })
    
    except Exception as e:
        logger.error(f"Error en statistics: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Ejecutar en la terminal: python app.py
    logger.info("🚀 OPTI-RUTA SKY iniciando...")
    logger.info(f"📍 Modo desarrollo: DEV_MOCK={DEV_MOCK}")
    logger.info("✈️ Sistema de monitoreo OpenSky activo")
    app.run(debug=True, port=5000)