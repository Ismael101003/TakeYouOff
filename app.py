from flask import Flask, jsonify, render_template, request
from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wl

import os
import requests 
import random   
import json     

from elevenlabs import ElevenLabs


# Asegúrate de haber instalado: pip install google-genai
from google import genai
# -----------------------------------------------------------

app = Flask(__name__)

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


# ===================================================================
# 2. CONEXIÓN AL MOTOR DE WOLFRAM
# ===================================================================

WOLFRAM_SESSION = None
try:
    WOLFRAM_SESSION = WolframLanguageSession(kernel=KERNEL_PATH)
    print("SERVERS: Wolfram Kernel Conectado.")
except Exception as e:
    print(f"ERROR: No se pudo conectar a Wolfram Kernel. Las matemáticas fallarán. {e}")


# ===================================================================
# 3. CONEXIÓN AL CLIENTE ELEVENLABS
# ===================================================================

ELEVENLABS_CLIENT = None
if ELEVENLABS_API_KEY:
    try:
        # Inicializa el cliente ElevenLabs
        ELEVENLABS_CLIENT = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        print("SERVERS: ElevenLabs Client Inicializado.")
    except Exception as e:
        print(f"ERROR: Falló al inicializar ElevenLabs. {e}")




# --- Gemini API vía OpenRouter (Explicabilidad de IA) ---
def call_gemini_analysis(route_data_str):
    """Genera un análisis contextual sobre el riesgo de la ruta vía OpenRouter."""
    
    if not OPENROUTER_API_KEY:
        return "OpenRouter Desconectado. (Clave API no configurada)"

    prompt_text = (
        f"Actúa como analista de seguridad aérea. Analiza el siguiente resultado del cálculo de ruta (Wolfram): {route_data_str}. "
        "Genera un resumen en 50 palabras sobre el riesgo de la ruta optimizada y las precauciones necesarias. Usa un tono urgente."
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

        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        response.raise_for_status() 
        
        return response.json()['choices'][0]['message']['content']
        
    except requests.exceptions.RequestException as e:
        print(f"Error en la llamada a OpenRouter: {e}")
        return "Error en la llamada a OpenRouter: No se pudo obtener el análisis."


# --- ElevenLabs API (Voz de Alerta) ---
def call_elevenlabs_alert(message):
    """Genera audio de la alerta y devuelve la URL del archivo (simulado)."""
    
    if not ELEVENLABS_CLIENT:
        print("ALERTA: Cliente ElevenLabs no inicializado. Usando texto.")
        return None 
    
    try:
        print(f"ALERTA: GENERANDO AUDIO DE VOZ: {message}")
        
        # ⚠️ Uso del cliente (método moderno para generar audio)
        audio = ELEVENLABS_CLIENT.audio.generate(
            text=message,
            voice="Bella", 
            model="eleven_multilingual_v2"
        )
        
        # En un hackathon, guardarías esto en la carpeta 'static'.
        # Aquí, simplemente confirmamos la generación.
        
        return "/static/alert.mp3" # Placeholder para el frontend
        
    except Exception as e:
        print(f"Error ElevenLabs en generación: {e}")
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
    if WOLFRAM_SESSION is None:
        return jsonify({"error": "Motor Wolfram Desconectado. Contacte al Modelador."}), 503

    try:
        data = request.json
        origen = data.get('origen')
        destino = data.get('destino')
        restricciones = data.get('restricciones', [])
        
        # --- 5.1 LLAMADA AL MOTOR WOLFRAM ---
        # Ejecuta la función definida por la Persona B
        wolfram_result = WOLFRAM_SESSION.evaluate(
             wl.OptimizeRoute(origen, destino, restricciones)
        )
        
        # Intenta extraer datos y convertir el resultado a string para Gemini
        wolfram_result_str = str(wolfram_result)
        
        # Intentamos obtener RutaTotalKM, asumiendo que es un valor numérico
        ruta_km = 0
        if isinstance(wolfram_result, dict) and 'RutaTotalKM' in wolfram_result:
            try:
                # El resultado de Wolfram puede ser un WLSymbol, lo convertimos a str para analizar
                ruta_km = float(str(wolfram_result['RutaTotalKM']))
            except (ValueError, TypeError):
                ruta_km = 0

        # --- 5.2 LÓGICA DEL TRIGGER CRÍTICO (T-A5) ---
        # La alerta se activa si la ruta optimizada es demasiado larga (> 500km)
        is_critical = (ruta_km > 500 or len(restricciones) >= 3)

        # --- 5.3 LLAMADA A GEMINI (OpenRouter) ---
        gemini_analysis = call_gemini_analysis(wolfram_result_str)

        # --- 5.4 LLAMADA A ELEVENLABS ---
        audio_url = None
        if is_critical:
            alert_message = f"ALERTA CRÍTICA: La ruta óptima excede los {int(ruta_km)} kilómetros y presenta alto riesgo. Verifique el análisis de Gemini."
            audio_url = call_elevenlabs_alert(alert_message)
            
        # 5. Respuesta Final para el Frontend
        return jsonify({
            "status": "success",
            "ruta_km": int(ruta_km),
            # Manejamos la conversión de la salida de Wolfram (puedes necesitar ajustar el formato de las coordenadas)
            "ruta_coordenadas": wolfram_result.get('RutaOptimizada', []), 
            "is_critical_alert": is_critical,
            "analisis_ia_texto": gemini_analysis,
            "audio_alert_url": audio_url,
            # Simulamos datos de riesgo para la gráfica
            "analisis_simulacion": {"riesgo_alto": 10 + len(restricciones) * 5, "riesgo_exito": 90 - len(restricciones) * 5} 
        })

    except Exception as e:
        print(f"Error en el endpoint optimize-route: {e}")
        return jsonify({"error": f"Error interno del servidor: {e}"}), 500

if __name__ == '__main__':
    # Ejecutar en la terminal: python app.py
    app.run(debug=True, port=5000)