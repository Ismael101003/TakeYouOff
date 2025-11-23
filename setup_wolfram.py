# ARCHIVO: setup_wolfram.py
# TAREA A2: Prueba de conexión con wolframclient

from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wl
import time
import os

# ===================================================================================
# PASO CRÍTICO 1: ESPECIFICAR LA RUTA DEL KERNEL
# 
# ⚠️ ADVERTENCIA: DEBES REEMPLAZAR ESTA RUTA por la ubicación exacta de tu 
# archivo 'WolframKernel.exe' (Windows) o 'WolframKernel' (Mac/Linux). 
# Usa el prefijo 'r' para manejar las barras inversas en Windows (r"C:\...").
# ===================================================================================
# Ejemplo Típico (Windows):
# KERNEL_PATH = r"C:\Program Files\Wolfram Research\Mathematica\13.2\WolframKernel.exe"
# Ejemplo Típico (Mac):
# KERNEL_PATH = "/Applications/Mathematica.app/Contents/MacOS/WolframKernel"

# DEBES DESCOMENTAR LA LÍNEA CON TU RUTA REAL:
# KERNEL_PATH = r"TU_RUTA_COMPLETA_AL_WOLFRAM_KERNEL_AQUÍ" 
KERNEL_PATH = r"C:\Program Files\Wolfram Research\Wolfram\14.3\WolframKernel.exe"

try:
    # 1. Conexión al Kernel Local (Usando la ruta explícita)
    session = WolframLanguageSession(kernel=KERNEL_PATH) 
    print("STATUS: Conexión con Wolfram Language establecida.")

    # 2. DATOS DE PRUEBA (Simulación de un conflicto en el aire)
    # Formato: [latitud, longitud]
    ORIGEN = [19.43, -99.13] 
    DESTINO = [20.00, -99.90]
    RESTRICCIONES_ZONA = [[19.6, -99.2], [19.8, -99.5]] 
    
    print("STATUS: Enviando datos de conflicto a OptimizeRoute...")
    
    # 3. LLAMADA A LA FUNCIÓN DEFINIDA EN EL NOTEBOOK DE WOLFRAM (Persona B)
    resultado_wolfram = session.evaluate(
        wl.OptimizeRoute(ORIGEN, DESTINO, RESTRICCIONES_ZONA)
    )

    # 4. IMPRESIÓN Y CIERRE
    print("\n--- ¡ÉXITO! RESULTADO DE OPTIMIZACIÓN EN PYTHON ---")
    print(resultado_wolfram)
    
    # Esto libera el Kernel
    session.terminate() 

except Exception as e:
    print(f"\nERROR CRÍTICO EN LA CONEXIÓN (Persona A):")
    print("Asegúrate de haber reemplazado KERNEL_PATH con la ruta correcta.")
    print("Asegúrate de que el código de Wolfram (Persona B) haya sido ejecutado en el notebook.")
    print(f"Error: {e}")