from flask import Flask, jsonify, render_template, request
from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wl

import os
import requests 
import random   
import json     
import logging
from threading import Lock

try:
    from flask_cors import CORS
    _HAS_CORS = True
except Exception:
    _HAS_CORS = False

from elevenlabs import ElevenLabs


# Asegúrate de haber instalado: pip install google-genai
from google import genai
# -----------------------------------------------------------

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================================================================
# 1. CONFIGURACIÓN DE LLAVES Y KERNEL (Variables de Entorno)
# ===================================================================

# A. Wolfram Kernel Path (La ruta que encontraste y te funcionó)
KERNEL_PATH = os.environ.get("WOLFRAM_KERNEL_PATH", r"C:\Program Files\Wolfram Research\Wolfram\14.3\WolframKernel.exe")

# B. APIs Externas (Se recuperan de las variables de entorno)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
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
    for i in range(len(tour)):
        current = tour[i]
        next_point = tour[(i + 1) % len(tour)]
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
                    total_distance = total_distance - curr_dist + new_dist
                    improved = True
                    break
            if improved:
                break
    
    # Convertir índices a coordenadas reales
    ruta_optimizada = [points[i] for i in tour]
    
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
# 3. CONEXIÓN AL CLIENTE ELEVENLABS
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

    # Prompt mejorado para forzar una salida estructurada y de valor (XAI)
    prompt_text = (
        f"Eres un analista de seguridad aérea y modelador de riesgos. Analiza los siguientes datos numéricos de cálculo de ruta geodésica (Wolfram): {route_data_str}. "
        "Tu tarea es generar un informe contextual y accionable. "
        "1. RESUMEN CRÍTICO (Tono urgente, máximo 3 oraciones): Identifica la principal causa de riesgo (ej: 'ruta excesivamente larga' o 'múltiples restricciones'). "
        "2. RECOMENDACIONES DE MITIGACIÓN (Lista de 3 puntos): Ofrece acciones concretas y verificables para el piloto que minimicen el riesgo. "
        "Formatea tu respuesta en un solo bloque de texto claro."
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
def call_elevenlabs_alert(message):
    """Genera audio de la alerta y devuelve la URL del archivo (simulado)."""
    
    if not ELEVENLABS_CLIENT:
        logger.warning("ALERTA: Cliente ElevenLabs no inicializado. Usando texto.")
        return None 
    
    try:
        logger.info("ALERTA: Generando audio de voz")
        # ⚠️ Uso del cliente (método moderno para generar audio)
        # audio = ELEVENLABS_CLIENT.audio.generate(
        #     text=message,
        #     voice="Bella", 
        #     model="eleven_multilingual_v2"
        # )
        
        return "/static/alert.mp3" # Placeholder para el frontend
        
    except Exception as e:
        logger.error("Error ElevenLabs en generación: %s", e)
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
        audio_url = None
        if is_critical:
            alert_message = f"ALERTA CRÍTICA: La ruta óptima excede los {int(ruta_km)} kilómetros y presenta alto riesgo. Verifique el análisis de Gemini."
            audio_url = call_elevenlabs_alert(alert_message)
            
        # 5. Respuesta Final para el Frontend
        return jsonify({
            "status": "success",
            "ruta_km": int(ruta_km),
            "ruta_coordenadas": ruta_coordenadas_normalizadas,
            "is_critical_alert": is_critical,
            "analisis_ia_texto": gemini_analysis,
            "audio_alert_url": audio_url,
            "analisis_simulacion": {"riesgo_alto": round(10 + len(restricciones) * 5 + ruta_km / 100), "riesgo_exito": round(90 - len(restricciones) * 5 - ruta_km / 100)} 
        })

    except Exception as e:
        logger.exception("Error en el endpoint optimize-route: %s", e)
        return jsonify({"error": f"Error interno del servidor: {e}"}), 500

if __name__ == '__main__':
    # Ejecutar en la terminal: python app.py
    app.run(debug=True, port=5000)


@app.route('/health', methods=['GET'])
def health():
    """Health endpoint simple."""
    return jsonify({"status": "ok", "dev_mock": DEV_MOCK})