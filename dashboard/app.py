#!/usr/bin/env python3
"""
DocuMentor Dashboard
Interactive visualization, search, and AI chat over processed documents.
"""

import json
import subprocess
import requests
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import Counter

# ── Config ──────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
WORKSPACE = Path(__file__).parent.parent / "workspace"
SEARCH_SCRIPT = WORKSPACE / "skills" / "rag-search" / "scripts" / "search.py"

# Default LLM settings (can be overridden via env vars or sidebar)
DEFAULT_MODEL = "moonshotai/kimi-k2.5"
DEFAULT_BASE_URL = "https://relay.opengpu.network/v2/openai/v1"
DEFAULT_SYSTEM_PROMPT = (
    "Eres DocuMentor, un asistente de inteligencia documental. "
    "Respondes preguntas basándote EXCLUSIVAMENTE en los fragmentos de documentos proporcionados. "
    "Si la información no está en los fragmentos, dilo claramente. "
    "Siempre cita las fuentes (nombre del archivo y página si está disponible). "
    "Responde en español, de forma clara y concisa."
)

st.set_page_config(
    page_title="📄 DocuMentor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Helpers ─────────────────────────────────────────────
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

def load_api_key() -> str:
    """Try to load API key from OpenClaw config or env var."""
    import os
    key = os.environ.get("OPENGPU_API_KEY", "")
    if key:
        return key
    # Try reading from OpenClaw config
    for config_path in [
        Path.home() / ".openclaw" / "config.yaml",
        Path.home() / ".openclaw" / "config.json",
        Path("/etc/openclaw/config.yaml"),
    ]:
        if config_path.exists():
            try:
                content = config_path.read_text()
                if config_path.suffix == ".json":
                    config = json.loads(content)
                else:
                    # Simple YAML extraction — look for apiKey near relaygpu
                    for line in content.split("\n"):
                        if "apiKey" in line and "relay" in content:
                            parts = line.split(":", 1)
                            if len(parts) == 2:
                                candidate = parts[1].strip().strip('"').strip("'")
                                if candidate and candidate != "":
                                    return candidate
                    return ""
                # JSON config: extract from providers
                providers = config.get("models", {}).get("providers", [])
                for p in providers:
                    if "relaygpu" in p.get("id", "") or "opengpu" in p.get("baseUrl", ""):
                        return p.get("apiKey", "")
            except Exception:
                pass
    return ""

def run_search(query: str, top_k: int = 5) -> dict:
    """Run ChromaDB search via the rag-search script."""
    try:
        result = subprocess.run(
            ["python3", str(SEARCH_SCRIPT), query, "--top-k", str(top_k)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr.strip() or "Search failed", "results": []}
    except FileNotFoundError:
        return {"error": "search.py no encontrado. ¿Se ha configurado el RAG?", "results": []}
    except subprocess.TimeoutExpired:
        return {"error": "Búsqueda cancelada por timeout (30s)", "results": []}
    except json.JSONDecodeError:
        return {"error": "Respuesta inválida del motor de búsqueda", "results": []}
    except Exception as e:
        return {"error": str(e), "results": []}

def build_rag_context(query: str, top_k: int = 5) -> tuple[str, list[dict]]:
    """Search documents and build context string for the LLM."""
    response = run_search(query, top_k)
    if response.get("error") or not response.get("results"):
        return "", []

    chunks = response["results"]
    context_parts = []
    for i, r in enumerate(chunks, 1):
        source = r.get("source", "?")
        page = r.get("page")
        page_str = f", página {page}" if page else ""
        text = r.get("text", "")
        context_parts.append(
            f"[Fragmento {i} — {source}{page_str} (relevancia: {r.get('score', 0):.0%})]\n{text}"
        )

    return "\n\n---\n\n".join(context_parts), chunks

def stream_chat_response(messages: list, api_key: str, model: str, base_url: str,
                         use_streaming: bool = True):
    """
    Call the LLM API. Yields (kind, text) tuples:
      kind = "thinking" | "content"
    Supports streaming and non-streaming modes.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "stream": use_streaming,
    }

    url = f"{base_url.rstrip('/')}/chat/completions"

    if not use_streaming:
        # ── Non-streaming ──
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})

        # Check for reasoning/thinking content
        thinking = msg.get("reasoning_content") or msg.get("thinking") or ""
        content = msg.get("content", "")

        if thinking:
            yield ("thinking", thinking)
        if content:
            yield ("content", content)
        return

    # ── Streaming (SSE) ──
    resp = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)
    resp.raise_for_status()

    current_kind = None

    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        data_str = line[6:]
        if data_str.strip() == "[DONE]":
            break

        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        delta = chunk.get("choices", [{}])[0].get("delta", {})

        # Check for reasoning/thinking tokens
        reasoning = delta.get("reasoning_content") or delta.get("thinking") or ""
        content = delta.get("content") or ""

        if reasoning:
            if current_kind != "thinking":
                current_kind = "thinking"
            yield ("thinking", reasoning)

        if content:
            if current_kind != "content":
                current_kind = "content"
            yield ("content", content)


# ── Load data ───────────────────────────────────────────
documents = load_documents()
tables = load_tables()

# ── Session state init ──────────────────────────────────
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_sources" not in st.session_state:
    st.session_state.chat_sources = {}  # msg_index -> [sources]

# ── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.title("📄 DocuMentor")
    st.markdown("---")

    # Key metrics
    total_chunks = sum(d.get("summary", {}).get("chunks", 0) for d in documents)
    total_chars = sum(d.get("summary", {}).get("total_chars", 0) for d in documents)
    total_table_rows = sum(len(t.get("rows", [])) for t in tables)

    col1, col2 = st.columns(2)
    col1.metric("📁 Documentos", len(documents))
    col2.metric("🧩 Chunks", total_chunks)

    col3, col4 = st.columns(2)
    col3.metric("📊 Tablas", len(tables))
    col4.metric("📏 Filas", total_table_rows)

    # Format breakdown
    if documents:
        st.markdown("---")
        st.markdown("### 📂 Por formato")
        format_counts = Counter(d.get("format", "?").upper() for d in documents)
        for fmt, count in format_counts.most_common():
            st.text(f"  {fmt}: {count}")

        # Last processed
        st.markdown("---")
        dates = [d.get("extracted_at", "") for d in documents if d.get("extracted_at")]
        if dates:
            latest = max(dates)[:16].replace("T", " ")
            st.caption(f"🕐 Último: {latest}")

        # Document list
        st.markdown("### 📁 Documentos")
        for doc in documents:
            fmt = doc.get("format", "?").upper()
            name = doc.get("filename", "?")
            chunks = doc.get("summary", {}).get("chunks", 0)
            st.text(f"  {fmt} · {name} ({chunks}ch)")

    # ── Chat settings ───────────────────────────────────
    st.markdown("---")
    st.markdown("### ⚙️ Chat")

    api_key = load_api_key()
    chat_api_key = st.text_input(
        "API Key",
        value=api_key,
        type="password",
        help="OpenGPU Relay API key. Se auto-detecta del config de OpenClaw."
    )

    chat_model = st.text_input("Modelo", value=DEFAULT_MODEL)
    chat_streaming = st.toggle("Streaming", value=True, help="Ver la respuesta token a token")
    chat_show_thinking = st.toggle("Mostrar razonamiento", value=True,
                                   help="Ver el proceso de razonamiento del modelo (si lo soporta)")
    chat_top_k = st.slider("Contexto (chunks)", min_value=1, max_value=15, value=5,
                           help="Número de fragmentos de documentos a usar como contexto")

    if st.button("🗑️ Limpiar chat"):
        st.session_state.chat_messages = []
        st.session_state.chat_sources = {}
        st.rerun()

    st.markdown("---")
    st.caption("DocuMentor · Powered by OpenClaw + OpenGPU")

# ── Main Content ────────────────────────────────────────
# Tabs — Chat is always available (even without documents)
tab_chat, tab_overview, tab_explorer, tab_search, tab_charts = st.tabs(
    ["💬 Chat", "📋 Resumen", "🔍 Explorador", "🔎 Búsqueda", "📊 Gráficos"]
)

# ── Tab: Chat ───────────────────────────────────────────
with tab_chat:
    st.header("💬 Chat con tus documentos")

    if not chat_api_key:
        st.warning(
            "⚠️ No se ha detectado una API key.\n\n"
            "Configúrala en la barra lateral (⚙️ Chat) o como variable de entorno `OPENGPU_API_KEY`."
        )

    if not documents:
        st.info(
            "📭 No hay documentos procesados todavía. "
            "Puedes chatear, pero las respuestas no tendrán contexto documental."
        )

    # Display chat history
    for i, msg in enumerate(st.session_state.chat_messages):
        role = msg["role"]
        with st.chat_message(role):
            # Show thinking if present and enabled
            if role == "assistant" and msg.get("thinking") and chat_show_thinking:
                with st.expander("🧠 Razonamiento", expanded=False):
                    st.markdown(msg["thinking"])

            st.markdown(msg["content"])

            # Show sources
            if role == "assistant" and i in st.session_state.chat_sources:
                sources = st.session_state.chat_sources[i]
                if sources:
                    with st.expander(f"📄 Fuentes ({len(sources)})", expanded=False):
                        for s in sources:
                            score = s.get("score", 0)
                            source_name = s.get("source", "?")
                            page = s.get("page")
                            page_str = f", pág. {page}" if page else ""
                            if score >= 0.7:
                                icon = "🟢"
                            elif score >= 0.4:
                                icon = "🟡"
                            else:
                                icon = "🔴"
                            st.caption(f"{icon} {source_name}{page_str} — {score:.0%}")

    # Chat input
    if user_input := st.chat_input("Pregunta sobre tus documentos...", disabled=not chat_api_key):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Search for context
        rag_context = ""
        sources = []
        if documents:
            with st.spinner("🔍 Buscando contexto en documentos..."):
                rag_context, sources = build_rag_context(user_input, chat_top_k)

        # Build messages for API
        api_messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]

        # Add RAG context as system message if available
        if rag_context:
            api_messages.append({
                "role": "system",
                "content": (
                    "A continuación se muestran los fragmentos más relevantes encontrados "
                    "en los documentos del usuario. Basa tu respuesta en estos fragmentos:\n\n"
                    f"{rag_context}"
                )
            })

        # Add conversation history (last 10 exchanges max)
        history = st.session_state.chat_messages[-20:]  # last 20 messages = ~10 exchanges
        for msg in history:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        # Stream response
        with st.chat_message("assistant"):
            thinking_text = ""
            content_text = ""
            thinking_placeholder = None
            thinking_expander = None
            content_placeholder = st.empty()

            try:
                for kind, text in stream_chat_response(
                    api_messages, chat_api_key, chat_model,
                    DEFAULT_BASE_URL, chat_streaming
                ):
                    if kind == "thinking":
                        thinking_text += text
                        if chat_show_thinking:
                            if thinking_expander is None:
                                thinking_expander = st.expander("🧠 Razonamiento", expanded=True)
                                thinking_placeholder = thinking_expander.empty()
                            thinking_placeholder.markdown(thinking_text + "▌")
                    elif kind == "content":
                        # Collapse thinking expander once content starts
                        if thinking_placeholder is not None and thinking_text:
                            thinking_placeholder.markdown(thinking_text)
                        content_text += text
                        content_placeholder.markdown(content_text + "▌")

                # Final render (remove cursor)
                if thinking_placeholder and thinking_text:
                    thinking_placeholder.markdown(thinking_text)
                content_placeholder.markdown(content_text)

                # Show sources
                if sources:
                    with st.expander(f"📄 Fuentes ({len(sources)})", expanded=False):
                        for s in sources:
                            score = s.get("score", 0)
                            source_name = s.get("source", "?")
                            page = s.get("page")
                            page_str = f", pág. {page}" if page else ""
                            if score >= 0.7:
                                icon = "🟢"
                            elif score >= 0.4:
                                icon = "🟡"
                            else:
                                icon = "🔴"
                            st.caption(f"{icon} {source_name}{page_str} — {score:.0%}")

            except requests.exceptions.ConnectionError:
                content_text = "❌ No se pudo conectar con el servidor de LLM. Verifica la API key y la URL."
                content_placeholder.error(content_text)
            except requests.exceptions.HTTPError as e:
                content_text = f"❌ Error del servidor: {e}"
                content_placeholder.error(content_text)
            except Exception as e:
                content_text = f"❌ Error inesperado: {e}"
                content_placeholder.error(content_text)

            # Save to session state
            assistant_msg = {"role": "assistant", "content": content_text}
            if thinking_text:
                assistant_msg["thinking"] = thinking_text
            st.session_state.chat_messages.append(assistant_msg)

            # Save sources reference
            msg_idx = len(st.session_state.chat_messages) - 1
            if sources:
                st.session_state.chat_sources[msg_idx] = sources

# ── Tab: Overview ───────────────────────────────────────
with tab_overview:
    if not documents:
        st.info("👋 No hay documentos procesados todavía. Sube un documento a través del chat.")
        st.stop()

    st.header("📋 Resumen de Documentos")

    cols = st.columns(4)
    cols[0].metric("Total documentos", len(documents))
    cols[1].metric("Total chunks", total_chunks)
    cols[2].metric("Total filas de datos", total_table_rows)
    formats = set(d.get("format", "?") for d in documents)
    cols[3].metric("Formatos", ", ".join(f.upper() for f in formats))

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

            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Descargar CSV",
                csv_data,
                file_name=f"export_{table.get('source', 'data')}.csv",
                mime="text/csv"
            )

# ── Tab: Search ─────────────────────────────────────────
with tab_search:
    st.header("🔎 Búsqueda en Documentos")
    st.markdown("Busca información en todos los documentos procesados usando búsqueda semántica.")

    col_input, col_k = st.columns([4, 1])
    with col_input:
        query = st.text_input(
            "¿Qué quieres buscar?",
            placeholder="Ej: ¿Cuántos estudiantes se matricularon en 2024?",
            label_visibility="collapsed"
        )
    with col_k:
        top_k = st.number_input("Resultados", min_value=1, max_value=20, value=5, label_visibility="collapsed")

    if st.button("🔎 Buscar", type="primary", disabled=not query):
        with st.spinner("Buscando en documentos..."):
            response = run_search(query, top_k)

        if response.get("error"):
            st.error(f"⚠️ {response['error']}")
        elif not response.get("results"):
            st.warning(
                "No se encontraron resultados relevantes.\n\n"
                "Intenta reformular tu pregunta o usa palabras clave diferentes."
            )
        else:
            results = response["results"]
            st.success(f"✅ {len(results)} resultado(s) encontrado(s)")

            for i, r in enumerate(results, 1):
                score = r.get("score", 0)
                source = r.get("source", "?")
                page = r.get("page")
                text = r.get("text", "")

                if score >= 0.7:
                    score_color = "🟢"
                elif score >= 0.4:
                    score_color = "🟡"
                else:
                    score_color = "🔴"

                page_info = f" · pág. {page}" if page else ""
                with st.expander(f"{score_color} **{source}**{page_info} — relevancia {score:.0%}", expanded=(i <= 3)):
                    st.markdown(text)
                    st.caption(f"Fuente: {source}{page_info} | Score: {score:.4f}")

    with st.expander("💡 Consejos de búsqueda"):
        st.markdown("""
        - **Preguntas naturales** funcionan mejor: "¿Cuál fue el presupuesto de 2024?"
        - **Sé específico**: "matrícula ingeniería 2024" > "datos"
        - **Prueba sinónimos** si no encuentras resultados
        - Los resultados con **relevancia verde** (🟢 >70%) son los más fiables
        - Resultados **amarillos** (🟡 40-70%) pueden ser relevantes con contexto
        - Resultados **rojos** (🔴 <40%) probablemente no son lo que buscas
        """)

# ── Tab: Charts ─────────────────────────────────────────
with tab_charts:
    st.header("📊 Gráficos")

    if not tables:
        st.info("No hay datos tabulares para graficar. Sube un Excel o CSV.")
    else:
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
