# 📄 DocuMentor

Sistema de inteligencia documental con IA. Sube documentos, haz preguntas en lenguaje natural y visualiza los datos en un dashboard interactivo.

> **Un comando. Sin Docker. Sin complicaciones.**

## Qué hace

- **📝 Procesa documentos**: PDF, Excel, Word, CSV
- **🔍 Búsqueda semántica**: Preguntas en lenguaje natural sobre tus documentos
- **📊 Dashboard visual**: Gráficos, tablas y exploración interactiva
- **🤖 IA adaptable**: Se configura según tus preferencias en el primer uso
- **🔒 Privacidad**: Todo local, tus datos nunca salen de tu máquina

## Instalar

### Opción 1: Un solo comando (recomendado)

```bash
curl -fsSL https://raw.githubusercontent.com/Asphyksia/DocuMentor/main/install.sh | bash
```

El instalador:
1. Instala OpenClaw si no lo tienes
2. Descarga el workspace personalizado
3. Configura los modelos de IA (API key + canal)
4. Instala dependencias Python
5. Inicia el sistema

### Opción 2: Manual

```bash
# 1. Instalar OpenClaw
curl -fsSL https://openclaw.ai/install.sh | bash

# 2. Clonar este repo
git clone https://github.com/Asphyksia/DocuMentor.git
cd DocuMentor

# 3. Ejecutar setup
./install.sh
```

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
├── install.sh                  # Instalador todo-en-uno
├── workspace/
│   ├── SOUL.md                 # Personalidad + onboarding
│   ├── AGENTS.md               # Reglas operativas
│   ├── USER.md                 # Se llena en onboarding
│   ├── TOOLS.md                # Config de herramientas
│   ├── HEARTBEAT.md
│   ├── skills/
│   │   ├── doc-ingest/         # Procesamiento de documentos
│   │   ├── rag-search/         # Búsqueda semántica (QMD/dotMD)
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
- GPU NVIDIA (opcional, mejora la búsqueda semántica)

## Links

- [OpenClaw Docs](https://docs.openclaw.ai)
- [OpenGPU Relay](https://relaygpu.com)
- [Comunidad Discord](https://discord.gg/clawd)

## Licencia

MIT

---

**DocuMentor — Inteligencia documental accesible para todos** 📄
