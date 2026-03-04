#!/usr/bin/env python3
"""
Document Intelligence Dashboard
Interactive visualization of processed documents.
"""

import json
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

# ── Config ──────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
st.set_page_config(
    page_title="📄 Document Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Load Data ───────────────────────────────────────────
@st.cache_data(ttl=30)
def load_documents():
    path = DATA_DIR / "documents.json"
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

@st.cache_data(ttl=30)
def load_tables():
    path = DATA_DIR / "tables.json"
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# ── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.title("📄 Document Intelligence")
    st.markdown("---")

    documents = load_documents()
    tables = load_tables()

    st.metric("Documentos", len(documents))
    st.metric("Tablas", len(tables))

    if documents:
        st.markdown("### 📁 Documentos")
        for doc in documents:
            fmt = doc.get("format", "?").upper()
            name = doc.get("filename", "?")
            st.text(f"  {fmt} · {name}")

    st.markdown("---")
    st.caption("Powered by OpenClaw + OpenGPU")

# ── Main Content ────────────────────────────────────────
if not documents:
    st.title("📄 Document Intelligence Dashboard")
    st.info(
        "👋 No hay documentos procesados todavía.\n\n"
        "Sube un documento a través del chat y aparecerá aquí automáticamente."
    )
    st.stop()

# Tabs
tab_overview, tab_explorer, tab_charts = st.tabs(["📋 Resumen", "🔍 Explorador", "📊 Gráficos"])

# ── Tab: Overview ───────────────────────────────────────
with tab_overview:
    st.header("📋 Resumen de Documentos")

    cols = st.columns(3)
    cols[0].metric("Total documentos", len(documents))
    total_tables = sum(len(t.get("rows", [])) for t in tables)
    cols[1].metric("Total filas de datos", total_tables)
    formats = set(d.get("format", "?") for d in documents)
    cols[2].metric("Formatos", ", ".join(f.upper() for f in formats))

    st.markdown("### Documentos procesados")
    df_docs = pd.DataFrame([{
        "Archivo": d.get("filename", "?"),
        "Formato": d.get("format", "?").upper(),
        "Chunks": d.get("summary", {}).get("chunks", 0),
        "Tablas": d.get("summary", {}).get("tables", 0),
        "Caracteres": d.get("summary", {}).get("total_chars", 0),
        "Procesado": d.get("extracted_at", "")[:19].replace("T", " ")
    } for d in documents])
    st.dataframe(df_docs, use_container_width=True, hide_index=True)

# ── Tab: Data Explorer ──────────────────────────────────
with tab_explorer:
    st.header("🔍 Explorador de Datos")

    if not tables:
        st.info("No hay tablas de datos disponibles.")
    else:
        # Select table
        table_names = [
            f"{t.get('source', '?')} — {t.get('row_count', 0)} filas"
            for t in tables
        ]
        selected_idx = st.selectbox(
            "Selecciona una tabla:",
            range(len(tables)),
            format_func=lambda i: table_names[i]
        )

        table = tables[selected_idx]
        if table.get("rows"):
            df = pd.DataFrame(table["rows"])
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Download
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Descargar CSV",
                csv_data,
                file_name=f"export_{table.get('source', 'data')}.csv",
                mime="text/csv"
            )

# ── Tab: Charts ─────────────────────────────────────────
with tab_charts:
    st.header("📊 Gráficos")

    if not tables:
        st.info("No hay datos tabulares para graficar. Sube un Excel o CSV.")
    else:
        # Select table and columns
        table_names = [
            f"{t.get('source', '?')} — {t.get('row_count', 0)} filas"
            for t in tables
        ]
        selected_idx = st.selectbox(
            "Tabla:",
            range(len(tables)),
            format_func=lambda i: table_names[i],
            key="chart_table"
        )

        table = tables[selected_idx]
        if table.get("rows"):
            df = pd.DataFrame(table["rows"])
            headers = list(df.columns)

            col1, col2 = st.columns(2)
            with col1:
                chart_type = st.selectbox("Tipo de gráfico", ["Barras", "Líneas", "Área"])
            with col2:
                y_col = st.selectbox("Columna de valores", headers)

            x_col = st.selectbox("Eje X / Categoría", headers)

            # Try to convert to numeric
            try:
                df[y_col] = pd.to_numeric(df[y_col], errors='coerce')
                chart_data = df[[x_col, y_col]].dropna().set_index(x_col)

                if chart_type == "Barras":
                    st.bar_chart(chart_data)
                elif chart_type == "Líneas":
                    st.line_chart(chart_data)
                elif chart_type == "Área":
                    st.area_chart(chart_data)

            except Exception as e:
                st.warning(f"No se pudo graficar: {e}")
                st.info("Selecciona una columna con valores numéricos.")
