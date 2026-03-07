# 📄 DocuMentor

Sistema de inteligencia documental con IA. Sube documentos, haz preguntas en lenguaje natural y visualiza los datos en un dashboard interactivo.

> **Un comando. Sin Docker. Sin complicaciones.**

## Qué hace

- **📝 Procesa documentos**: PDF, Excel, Word, CSV
- **🔍 Búsqueda semántica**: Preguntas en lenguaje natural sobre tus documentos (ChromaDB)
- **📊 Dashboard visual**: Chat con IA, gráficos, tablas y exploración interactiva
- **🤖 IA adaptable**: Se configura según tus preferencias en el primer uso
- **🛡️ Seguridad**: Protección contra prompt injection (600+ patrones)
- **🔒 Privacidad**: Todo local, tus datos nunca salen de tu máquina

## Instalar

### Un solo comando

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/Asphyksia/DocuMentor/main/install.sh -o /tmp/dm-install.sh && bash /tmp/dm-install.sh
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/Asphyksia/DocuMentor/main/install.ps1 -OutFile $env:TEMP\dm-install.ps1; & $env:TEMP\dm-install.ps1
```

El instalador hace **solo dos cosas**:
1. Instala OpenClaw si no lo tienes (usa el instalador oficial)
2. Copia el workspace de DocuMentor

Las dependencias Python (ChromaDB, Streamlit, etc.) las instala el propio bot en la primera conversación, de forma transparente.

## Desinstalar

**Linux / macOS:**
```bash
bash ~/DocuMentor/uninstall.sh
```

**Windows (PowerShell):**
```powershell
& "$env:USERPROFILE\DocuMentor\uninstall.ps1"
```

El desinstalador pregunta qué quieres eliminar: solo DocuMentor, la config de OpenClaw, o OpenClaw completo.

## Después de instalar

1. **Añade tu ID de usuario** a `allowFrom` en `~/.openclaw/openclaw.json`
2. **Reinicia**: `openclaw gateway restart`
3. **Habla con el bot** por Telegram/WhatsApp/Discord
4. **El bot te guiará** — te preguntará tu nombre, preferencias y te enseñará a subir documentos

## Dashboard

```bash
cd ~/DocuMentor
streamlit run dashboard/app.py
```

Accede en: **http://localhost:8501**

### Tabs

| Tab | Qué hace |
|-----|----------|
| **💬 Chat** | Chat con IA sobre tus documentos. Busca contexto en ChromaDB automáticamente, responde con citas. Soporta streaming y visualización del razonamiento del modelo. |
| **📋 Resumen** | Vista general: documentos procesados, métricas, formatos, chunks. |
| **🔍 Explorador** | Navega y descarga tablas extraídas de Excel/CSV. |
| **🔎 Búsqueda** | Búsqueda semántica directa en ChromaDB con relevancia por colores. |
| **📊 Gráficos** | Barras, líneas y áreas sobre cualquier columna numérica. |

### Chat: Configuración

La API key de OpenGPU se auto-detecta del config de OpenClaw. También puedes:
- Cambiar el modelo desde la sidebar
- Activar/desactivar streaming (respuesta token a token)
- Mostrar/ocultar el razonamiento del modelo
- Ajustar cuántos fragmentos de contexto usar (1-15)

## Modelos de IA

Usa [OpenGPU Relay](https://relaygpu.com) — modelos premium a precios reducidos:

| Modelo | Uso ideal | Coste aprox. |
|--------|-----------|-------------|
| **Kimi K2.5** (default) | Uso diario, multilingüe, razonamiento | ~$0.55/1M tokens |
| **DeepSeek V3.1** | Alternativa económica | ~$0.55/1M tokens |
| **Claude Sonnet 4-6** | Análisis profundo | ~$3/1M tokens |

Estimación: **~€5-15/mes** para uso moderado (500 consultas/día).

## Estructura

```
DocuMentor/
├── install.sh                  # Instalador (Linux/macOS)
├── install.ps1                 # Instalador (Windows)
├── workspace/
│   ├── SOUL.md                 # Personalidad + onboarding
│   ├── AGENTS.md               # Reglas operativas
│   ├── USER.md                 # Se llena en onboarding
│   ├── TOOLS.md                # Config de herramientas
│   ├── HEARTBEAT.md
│   ├── skills/
│   │   ├── doc-ingest/         # Procesamiento de documentos
│   │   ├── rag-search/         # Búsqueda semántica (ChromaDB)
│   │   ├── prompt-guard/       # Seguridad anti prompt-injection
│   │   └── dashboard/          # Visualización de datos
│   ├── memory/                 # Config de usuario + datos
│   └── documents/              # Documentos subidos
├── dashboard/
│   ├── app.py                  # Streamlit dashboard
│   └── requirements.txt
└── README.md
```

## Actualizar

```bash
# Actualizar OpenClaw (el motor)
openclaw update

# Actualizar el workspace (este repo)
cd ~/DocuMentor
git pull
./install.sh
```

Tu configuración y documentos no se pierden al actualizar.

## Privacidad

- Los documentos se almacenan **localmente**
- Solo se envía texto al LLM para inferencia, sin almacenamiento
- Los embeddings se generan en local (con GPU si disponible)
- **Tú controlas tus datos**

## Requisitos

- Node.js 22+ (el instalador lo maneja)
- Python 3.10+
- GPU NVIDIA (opcional, acelera los embeddings de búsqueda)

## Links

- [OpenClaw Docs](https://docs.openclaw.ai)
- [OpenGPU Relay](https://relaygpu.com)
- [Comunidad Discord](https://discord.gg/clawd)

## Licencia

MIT

---

**DocuMentor — Inteligencia documental accesible para todos** 📄
