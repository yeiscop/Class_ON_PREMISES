import os
import sys
import webbrowser
import threading

import matcher
import query
import app as dash_app

DB_PATH = "editorial_assignments.db"

def open_browser():
    """Abre el navegador web en el puerto de Dash."""
    webbrowser.open_new("http://127.0.0.1:8050/")

def run_full_pipeline(sample_limit=5):
    print("=" * 70)
    print("🚀 INICIANDO ORQUESTADOR MAESTRO (DASHBOARD CON DASH)")
    print("=" * 70)

    # 1. Ejecutar Matcher
    print("\n[PASO 1/3] Ejecutando matcher.py con Ollama...")
    df_result = matcher.run_matching_pipeline(
        summary_path="summary.xlsx",
        evaluators_path="evaluators.xlsx",
        embed_model="nomic-embed-text",
        llm_model="mistral",
        sample_limit=sample_limit
    )
    print(f"✔ Matcher completado: {len(df_result)} registros procesados.")

    # 2. Validar Base de Datos con query.py
    print("\n[PASO 2/3] Validando base de datos SQLite...")
    stats = query.validate_and_summary()
    print(f"✔ Base de datos '{DB_PATH}' verificada:")
    print(f"   • Artículos: {stats['articulos']}")
    print(f"   • Evaluadores: {stats['evaluadores']}")
    print(f"   • Asignaciones: {stats['asignaciones']}")

    # 3. Lanzar Servidor Dash
    print("\n[PASO 3/3] Iniciando servidor web Dash en http://127.0.0.1:8050/ ...")
    print("=" * 70)
    
    # Abrir navegador tras 1.5 segundos para dar tiempo al arranque del servidor
    threading.Timer(1.5, open_browser).start()
    
    # Ejecuta el servidor Dash
    dash_app.app.run(debug=False, port=8050)

if __name__ == "__main__":
    run_full_pipeline(sample_limit=5)