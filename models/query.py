import os
import sqlite3
import pandas as pd

# Busca la base de datos tanto en la carpeta actual como en la carpeta superior (raíz)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

if os.path.exists(os.path.join(PARENT_DIR, "editorial_assignments.db")):
    DB_PATH = os.path.join(PARENT_DIR, "editorial_assignments.db")
else:
    DB_PATH = os.path.join(BASE_DIR, "editorial_assignments.db")

def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Base de datos {DB_PATH} no encontrada.")
    return sqlite3.connect(DB_PATH)

def validate_and_summary():
    """Valida las tablas creadas y devuelve estadísticas básicas."""
    conn = get_db_connection()
    cur = conn.cursor()
    stats = {}
    for table in ["articulos", "evaluadores", "asignaciones"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = cur.fetchone()[0]
    conn.close()
    return stats

def get_all_assignments():
    """Consulta todas las asignaciones cruzando artículos y evaluadores."""
    conn = get_db_connection()
    
    # Comprobar nombres de columnas disponibles en 'asignaciones'
    cols_df = pd.read_sql_query("PRAGMA table_info(asignaciones);", conn)
    col_names = cols_df["name"].tolist()
    
    eval_id_col = "Id_Evaluador_Asignado" if "Id_Evaluador_Asignado" in col_names else "Top_Candidate_Id"
    sim_col = "Semantic_Similarity" if "Semantic_Similarity" in col_names else "Similarity_Score"
    rep_col = "LLM_Report" if "LLM_Report" in col_names else "LLM_Decision"

    query_str = f"""
    SELECT 
        asig.IdArticulo,
        a.Título AS Titulo_Articulo,
        ev.Id_Usuario AS Id_Evaluador,
        ev.Area_interés AS Area_Evaluador,
        ev.Institución AS Institucion_Evaluador,
        asig.{sim_col} AS Similitud,
        asig.{rep_col} AS LLM_Report
    FROM asignaciones asig
    LEFT JOIN articulos a ON asig.IdArticulo = a.IdArticulo
    LEFT JOIN evaluadores ev ON asig.{eval_id_col} = ev.Id_Usuario;
    """
    df = pd.read_sql_query(query_str, conn)
    conn.close()
    return df

def get_assignment_by_article_id(article_id):
    """Consulta la ficha de un artículo por su ID."""
    df = get_all_assignments()
    match = df[df["IdArticulo"] == article_id]
    return match.iloc[0] if not match.empty else None

def execute_custom_query(sql_query):
    """Ejecuta cualquier sentencia SQL personalizada."""
    conn = get_db_connection()
    df = pd.read_sql_query(sql_query, conn)
    conn.close()
    return df