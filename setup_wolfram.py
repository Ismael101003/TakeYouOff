# ARCHIVO: setup_wolfram.py
# TAREA A2: Prueba de conexión con wolframclient

from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wl
import time
import os


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