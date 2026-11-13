import os
import sys
import dash
from dash import html, dcc, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd

# -------------------------------------------------------------
# Asegurar resolución de módulos locales (query.py)
# -------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import query

# -------------------------------------------------------------
# Inicialización de la Aplicación Dash
# -------------------------------------------------------------
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True
)
app.title = "Editorial Reviewer Matcher"

# -------------------------------------------------------------
# Componente: Tarjetas de Métricas
# -------------------------------------------------------------
def get_metrics_cards(df):
    if df.empty:
        return dbc.Alert("No hay datos disponibles en la base de datos.", color="warning")
    
    total_art = len(df)
    
    # Manejar cálculo de promedio si la columna Similitud existe
    if "Similitud" in df.columns and pd.to_numeric(df["Similitud"], errors="coerce").notnull().any():
        avg_sim = pd.to_numeric(df["Similitud"], errors="coerce").mean() * 100
        sim_text = f"{avg_sim:.1f}%"
    else:
        sim_text = "N/A"
        
    unique_evals = df["Id_Evaluador"].nunique() if "Id_Evaluador" in df.columns else 0

    return dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Total Artículos Asignados", className="card-subtitle text-muted"),
                html.H3(f"{total_art}", className="card-title text-primary mt-2")
            ])
        ], color="light", className="shadow-sm"), width=12, md=4),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Similitud Semántica Media", className="card-subtitle text-muted"),
                html.H3(sim_text, className="card-title text-success mt-2")
            ])
        ], color="light", className="shadow-sm"), width=12, md=4),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Evaluadores Únicos Seleccionados", className="card-subtitle text-muted"),
                html.H3(f"{unique_evals}", className="card-title text-info mt-2")
            ])
        ], color="light", className="shadow-sm"), width=12, md=4),
    ], className="mb-4")

# -------------------------------------------------------------
# Carga inicial de datos para dropdown y tabla
# -------------------------------------------------------------
try:
    df_initial = query.get_all_assignments()
except Exception:
    df_initial = pd.DataFrame()

article_options = []
if not df_initial.empty:
    for _, row in df_initial.iterrows():
        art_id = str(row.get("IdArticulo", ""))
        title = str(row.get("Titulo_Articulo", row.get("Título", "Sin título")))
        article_options.append({
            "label": f"ID {art_id} - {title[:65]}...",
            "value": art_id
        })

default_dropdown_val = article_options[0]["value"] if article_options else None

# -------------------------------------------------------------
# Estructura del Layout (UI)
# -------------------------------------------------------------
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("📚 Sistema de Asignación Editorial de Pares Evaluadores", className="mt-4 text-primary font-weight-bold"),
            html.P("Emparejamiento semántico y re-ranking asistido por modelos locales Ollama (Mistral / Phi3)", className="text-muted"),
            html.Hr()
        ])
    ]),

    # Contenedor de Métricas Superiores
    html.Div(id="metrics-container", children=get_metrics_cards(df_initial)),

    # Navegación por pestañas
    dbc.Tabs([
        # TAB 1: Tabla de Resultados
        dbc.Tab(label="📋 Tabla General de Asignaciones", children=[
            html.Div([
                html.H5("Artículos y Evaluadores Emparejados", className="mt-3 mb-3 text-secondary"),
                dash_table.DataTable(
                    id="table-assignments",
                    columns=[
                        {"name": "Id Artículo", "id": "IdArticulo"},
                        {"name": "Título del Artículo", "id": "Titulo_Articulo"},
                        {"name": "Id Evaluador", "id": "Id_Evaluador"},
                        {"name": "Área de Interés", "id": "Area_Evaluador"},
                        {"name": "Institución", "id": "Institucion_Evaluador"},
                        {"name": "Similitud Semántica", "id": "Similitud"}
                    ],
                    data=df_initial.to_dict("records"),
                    page_size=10,
                    style_table={"overflowX": "auto"},
                    style_header={
                        "backgroundColor": "#2c3e50",
                        "color": "white",
                        "fontWeight": "bold",
                        "textAlign": "center"
                    },
                    style_cell={
                        "textAlign": "left",
                        "padding": "10px",
                        "whiteSpace": "normal",
                        "fontSize": "14px"
                    },
                    filter_action="native",
                    sort_action="native"
                )
            ], className="p-3 bg-white border rounded shadow-sm mt-3")
        ]),

        # TAB 2: Detalle y Justificación del LLM
        dbc.Tab(label="🔍 Detalle & Dictamen LLM", children=[
            html.Div([
                html.H5("Inspeccionar Artículo", className="mt-3 mb-2 text-secondary"),
                dcc.Dropdown(
                    id="dropdown-articles",
                    options=article_options,
                    value=default_dropdown_val,
                    placeholder="Seleccione un artículo para consultar su justificación...",
                    className="mb-3"
                ),
                html.Div(id="article-detail-card")
            ], className="p-3 bg-white border rounded shadow-sm mt-3")
        ]),

        # TAB 3: Consola SQL
        dbc.Tab(label="💾 Consola SQLite Interactiva", children=[
            html.Div([
                html.H5("Ejecutar Consulta Directa sobre SQLite", className="mt-3 mb-2 text-secondary"),
                dbc.Textarea(
                    id="sql-input",
                    value="SELECT IdArticulo, Id_Evaluador, Similitud FROM (SELECT asig.IdArticulo, ev.Id_Usuario AS Id_Evaluador, asig.Similarity_Score AS Similitud FROM asignaciones asig LEFT JOIN evaluadores ev ON asig.Top_Candidate_Id = ev.Id_Usuario) LIMIT 10;",
                    style={"height": 110, "fontFamily": "monospace"}
                ),
                dbc.Button("Ejecutar Consulta", id="btn-run-sql", color="primary", className="mt-2 mb-3"),
                html.Div(id="sql-output-container")
            ], className="p-3 bg-white border rounded shadow-sm mt-3")
        ])
    ], className="mt-2")
], fluid=True, className="p-4")

# -------------------------------------------------------------
# Callbacks (Interactividad)
# -------------------------------------------------------------

@app.callback(
    Output("article-detail-card", "children"),
    Input("dropdown-articles", "value")
)
def update_article_detail(selected_id):
    if not selected_id:
        return dbc.Alert("Seleccione un artículo en el menú desplegable.", color="info")
    
    rec = query.get_assignment_by_article_id(str(selected_id))
    
    if rec is None or (isinstance(rec, pd.DataFrame) and rec.empty):
        return dbc.Alert(f"No se encontró información para el artículo con ID: {selected_id}", color="warning")

    # Mapeo de campos tolerante a nombres de columnas
    titulo = rec.get("Titulo_Articulo", rec.get("Título", "Sin título"))
    palabras = rec.get("Palabras_Clave", rec.get("Palabras clave", "No especificadas"))
    id_eval = rec.get("Id_Evaluador", rec.get("Top_Candidate_Id", "N/A"))
    institucion = rec.get("Institucion_Evaluador", rec.get("Institución", "No registrada"))
    area = rec.get("Area_Evaluador", rec.get("Area_interés", "Sin área especificada"))
    similitud = rec.get("Similitud", rec.get("Similarity_Score", "N/A"))
    reporte = rec.get("LLM_Report", rec.get("LLM_Decision", "Sin justificación registrada."))

    # Formateo si similitud es float
    if isinstance(similitud, (int, float)):
        similitud = f"{similitud * 100:.2f}%"

    return dbc.Card([
        dbc.CardHeader(html.H5(f"Artículo ID: {rec.get('IdArticulo', selected_id)} — {titulo}", className="m-0")),
        dbc.CardBody([
            html.P([html.Strong("Palabras Clave: "), str(palabras)]),
            html.Hr(),
            html.H6("Evaluador Seleccionado:", className="text-primary font-weight-bold"),
            dbc.Row([
                dbc.Col([
                    html.P([html.Strong("ID Evaluador: "), str(id_eval)]),
                    html.P([html.Strong("Institución: "), str(institucion)])
                ], md=6),
                dbc.Col([
                    html.P([html.Strong("Área de Conocimiento: "), str(area)]),
                    html.P([html.Strong("Similitud Calculada: "), str(similitud)])
                ], md=6),
            ]),
            html.Hr(),
            html.H6("Dictamen y Justificación del Modelo LLM:", className="text-info font-weight-bold"),
            html.Pre(
                str(reporte), 
                style={
                    "backgroundColor": "#f8f9fa", 
                    "padding": "15px", 
                    "borderRadius": "6px", 
                    "border": "1px solid #dee2e6",
                    "whiteSpace": "pre-wrap",
                    "fontFamily": "Consolas, monospace",
                    "fontSize": "13px"
                }
            )
        ])
    ], className="border-primary shadow-sm")

@app.callback(
    Output("sql-output-container", "children"),
    Input("btn-run-sql", "n_clicks"),
    State("sql-input", "value"),
    prevent_initial_call=True
)
def execute_sql(n_clicks, sql_text):
    if not sql_text or not sql_text.strip():
        return dbc.Alert("Por favor ingrese una sentencia SQL.", color="warning")
    try:
        df_sql = query.execute_custom_query(sql_text)
        if df_sql.empty:
            return dbc.Alert("La consulta se ejecutó con éxito pero no devolvió filas.", color="info")
        return dash_table.DataTable(
            columns=[{"name": col, "id": col} for col in df_sql.columns],
            data=df_sql.to_dict("records"),
            page_size=10,
            style_table={"overflowX": "auto"},
            style_header={"backgroundColor": "#34495e", "color": "white", "fontWeight": "bold"},
            style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"}
        )
    except Exception as err:
        return dbc.Alert(f"Error al ejecutar SQL: {str(err)}", color="danger")

# -------------------------------------------------------------
# Ejecución del Servidor
# -------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=8050)