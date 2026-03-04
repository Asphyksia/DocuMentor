---
name: dashboard
description: Interactive data visualization dashboard using Streamlit. Use when a user wants to see charts, graphs, visual analytics, data exploration, or asks to visualize data from their documents. Also use when suggesting visual representation would be more helpful than text.
---

# Dashboard

Interactive visual dashboard for document data, powered by Streamlit.

## Access

The dashboard runs at **http://localhost:8501** (configured in setup).

## When to Suggest the Dashboard

- User asks about data trends, comparisons, or statistics
- Response would benefit from charts or graphs
- User has uploaded Excel/CSV with numerical data
- User explicitly asks to "see" or "visualize" data

Suggest it naturally:
```
"He encontrado los datos. ¿Quieres verlos en el dashboard?
📊 http://localhost:8501"
```

## Updating Dashboard Data

When new documents are processed that contain tabular data, update the dashboard data:

```bash
python3 {baseDir}/scripts/update_dashboard.py
```

This script reads from `memory/documents/` and generates dashboard-ready data in `dashboard/data/`.

## Dashboard Features

The Streamlit app (`dashboard/app.py`) provides:

1. **Document Overview** — List of all processed documents with metadata
2. **Data Explorer** — Interactive tables with filtering and sorting
3. **Charts** — Bar, line, pie charts generated from tabular data
4. **Search** — Visual search interface (queries the same RAG backend)
5. **Export** — Download charts as PNG, data as CSV

## Inline Charts

For simple visualizations that don't need the full dashboard, generate inline charts:

```python
# Generate a quick chart and save as image
python3 {baseDir}/scripts/quick_chart.py --type bar --data <json_data> --output /tmp/chart.png
```

Then share the image directly in chat.

## Scripts

- `{baseDir}/scripts/update_dashboard.py` — Sync processed document data to dashboard
- `{baseDir}/scripts/quick_chart.py` — Generate inline charts for chat
