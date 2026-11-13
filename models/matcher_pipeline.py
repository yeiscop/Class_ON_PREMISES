import sqlite3
import numpy as np
import ollama
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# 1. Load Data
df_articles = pd.read_excel("data\summary.xlsx")
df_evaluators = pd.read_excel("data\evaluators.xlsx")


# 2. Build Rich Text Descriptions
def build_article_text(row):
  return (
      f"Título: {row['Título']}. "
      f"Palabras clave: {row['Palabras clave']}. "
      f"Resumen: {str(row['Resumen'])[:600]}"
  )


def build_evaluator_text(row):
  area = row["Area_interés"] if pd.notna(row["Area_interés"]) else ""
  titulo = row["Título_académico"] if pd.notna(row["Título_académico"]) else ""
  inst = row["Institución"] if pd.notna(row["Institución"]) else ""
  desc = f"Área de interés: {area}. Título académico: {titulo}. Institución: {inst}."
  return (
      desc
      if desc.strip() != "Área de interés: . Título académico: . Institución: ."
      else "Sin información detallada de área"
  )


df_articles["full_text"] = df_articles.apply(build_article_text, axis=1)
df_evaluators["full_text"] = df_evaluators.apply(build_evaluator_text, axis=1)


# 3. Generate Local Embeddings with Ollama
def get_embedding(text, model="nomic-embed-text"):
  res = ollama.embeddings(model=model, prompt=text)
  return res["embedding"]


print("Computing article embeddings...")
art_embeddings = np.array(
    [get_embedding(t) for t in df_articles["full_text"].tolist()]
)

print("Computing evaluator embeddings...")
eval_embeddings = np.array(
    [get_embedding(t) for t in df_evaluators["full_text"].tolist()]
)

# 4. Calculate Semantic Similarity Matrix
sim_matrix = cosine_similarity(art_embeddings, eval_embeddings)


# 5. Rerank Top Candidates with Mistral / Phi
def choose_best_evaluator(
    article_title, article_keywords, candidates_info, llm_model="mistral"
):
  prompt = f"""Eres un editor académico. Debes seleccionar al evaluador más idóneo para revisar este artículo.

ARTÍCULO:
- Título: {article_title}
- Palabras clave: {article_keywords}

CANDIDATOS POTENCIALES:
{candidates_info}

INSTRUCCIONES:
1. Analiza el área temática del artículo y compárala con el área de cada evaluador.
2. Devuelve tu respuesta EXACTAMENTE en este formato:
ID_EVALUADOR: <número del Id_Usuario elegido>
PUNTAJE: <puntuación de 0 a 100>
JUSTIFICACION: <explicación breve de 1 o 2 líneas en español>
"""
  response = ollama.chat(
      model=llm_model, messages=[{"role": "user", "content": prompt}]
  )
  return response["message"]["content"]


assignments = []
print("Evaluating matches with LLM...")

for art_idx, art_row in df_articles.iterrows():
  # Extract top 3 candidates based on cosine similarity
  top_eval_indices = np.argsort(sim_matrix[art_idx])[::-1][:3]

  candidates_text = ""
  for rank, e_idx in enumerate(top_eval_indices, 1):
    ev = df_evaluators.iloc[e_idx]
    candidates_text += f"{rank}. [ID: {ev['Id_Usuario']}] Área: {ev['Area_interés']} | Título: {ev['Título_académico']} | Institución: {ev['Institución']}\n"

  # Ask LLM to determine the single best reviewer
  decision = choose_best_evaluator(
      art_row["Título"], art_row["Palabras clave"], candidates_text, "mistral"
  )

  assignments.append({
      "IdArticulo": art_row["IdArticulo"],
      "Titulo_Articulo": art_row["Título"],
      "Top_Candidate_Id": df_evaluators.iloc[top_eval_indices[0]]["Id_Usuario"],
      "Similarity_Score": round(float(sim_matrix[art_idx][top_eval_indices[0]]), 4),
      "LLM_Decision": decision,
  })

df_results = pd.DataFrame(assignments)

# 6. Save to SQLite Database and Excel
conn = sqlite3.connect("editorial_assignments.db")

df_articles[
    ["IdArticulo", "Título", "Palabras clave", "Resumen"]
].to_sql("articulos", conn, if_exists="replace", index=False)

df_evaluators[[
    "Id_Usuario",
    "País",
    "Institución",
    "Internacionalización",
    "Título_académico",
    "Area_interés",
]].to_sql("evaluadores", conn, if_exists="replace", index=False)

df_results.to_sql("asignaciones", conn, if_exists="replace", index=False)
conn.close()

df_results.to_excel("asignaciones_finales.xlsx", index=False)
print("Process completed! Results saved to SQLite and Excel.")