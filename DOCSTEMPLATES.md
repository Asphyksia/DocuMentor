# DOCSTEMPLATES.md — JSON Templates by File Extension

## MANDATORY Rules
- ALWAYS use `response_format: json_object`
- Maximum 4 elements in `views[]`
- Validate JSON before sending
- Use ONLY these templates
- `type` field must match exactly: `pdf | spreadsheet | docx | pptx | html | image | generic`

---

## PDF (.pdf)

```json
{
  "type": "pdf",
  "summary": "2-3 executive sentences",
  "entities": {
    "persons": ["array of strings"],
    "dates": ["YYYY-MM-DD"],
    "amounts": [{ "concept": "string", "value": number }]
  },
  "tables_detected": [
    {
      "title": "string",
      "headers": ["string"],
      "rows": [["string"]]
    }
  ],
  "key_text": "3 most relevant paragraphs",
  "views": [
    {
      "type": "kpi",
      "title": "string",
      "value": number,
      "unit": "% | € | units | string"
    },
    {
      "type": "table",
      "title": "string",
      "headers": ["string"],
      "rows": [["string"]]
    },
    {
      "type": "bar",
      "title": "string",
      "x_axis": "string",
      "y_axis": "string",
      "data": [{ "x": "string", "y": number }]
    },
    {
      "type": "line",
      "title": "string",
      "x_axis": "string",
      "y_axis": "string",
      "data": [{ "x": "string", "y": number }]
    }
  ]
}
```

---

## Spreadsheet (.xlsx, .csv)

```json
{
  "type": "spreadsheet",
  "sheets": [
    {
      "name": "string",
      "headers": ["string"],
      "rows": [["string"]],
      "numeric_columns": ["column1", "column2"]
    }
  ],
  "calculated_metrics": [
    { "name": "total",   "value": number },
    { "name": "average", "value": number },
    { "name": "maximum", "value": number },
    { "name": "minimum", "value": number }
  ],
  "views": [
    {
      "type": "bar",
      "title": "string",
      "x_axis": "string",
      "y_axis": "string",
      "data": [{ "x": "string", "y": number }]
    },
    {
      "type": "line",
      "title": "string",
      "x_axis": "string",
      "y_axis": "string",
      "data": [{ "x": "string", "y": number }]
    },
    {
      "type": "kpi",
      "title": "string",
      "value": number,
      "unit": "% | € | units | string"
    },
    {
      "type": "table",
      "title": "string",
      "headers": ["string"],
      "rows": [["string"]]
    }
  ]
}
```

---

## DOCX (.docx)

```json
{
  "type": "docx",
  "summary": "string",
  "sections": [
    {
      "title": "string",
      "content": "string"
    }
  ],
  "tables": [
    {
      "title": "string",
      "headers": ["string"],
      "rows": [["string"]]
    }
  ],
  "views": [
    {
      "type": "table",
      "title": "string",
      "headers": ["string"],
      "rows": [["string"]]
    },
    {
      "type": "kpi",
      "title": "string",
      "value": number,
      "unit": "% | € | units | string"
    },
    {
      "type": "text",
      "title": "string",
      "content": "string"
    }
  ]
}
```

---

## PowerPoint (.pptx)

```json
{
  "type": "pptx",
  "summary": "2-3 sentences describing the presentation",
  "slide_count": 0,
  "slides": [
    {
      "number": 1,
      "title": "string",
      "content": "string (bullet points or text)",
      "has_table": false,
      "has_chart": false
    }
  ],
  "tables": [
    {
      "title": "string (slide reference)",
      "headers": ["string"],
      "rows": [["string"]]
    }
  ],
  "views": [
    {
      "type": "kpi",
      "title": "string",
      "value": "number",
      "unit": "% | € | units | string"
    },
    {
      "type": "text",
      "title": "Presentation Outline",
      "content": "string (structured slide summary)"
    },
    {
      "type": "table",
      "title": "string",
      "headers": ["string"],
      "rows": [["string"]]
    },
    {
      "type": "pie",
      "title": "string",
      "data": [{ "label": "string", "value": "number" }]
    }
  ]
}
```

---

## HTML (.html, .htm)

```json
{
  "type": "html",
  "summary": "2-3 sentences describing the page content",
  "page_title": "string (from <title> tag)",
  "headings": ["string (h1-h3 headings found)"],
  "tables": [
    {
      "title": "string",
      "headers": ["string"],
      "rows": [["string"]]
    }
  ],
  "links_count": 0,
  "views": [
    {
      "type": "text",
      "title": "Page Summary",
      "content": "string"
    },
    {
      "type": "table",
      "title": "string",
      "headers": ["string"],
      "rows": [["string"]]
    },
    {
      "type": "kpi",
      "title": "string",
      "value": "number",
      "unit": "% | € | units | string"
    },
    {
      "type": "bar",
      "title": "string",
      "x_axis": "string",
      "y_axis": "string",
      "data": [{ "x": "string", "y": "number" }]
    }
  ]
}
```

---

## Image (.png, .jpg, .jpeg, .tiff, .bmp)

```json
{
  "type": "image",
  "summary": "2-3 sentences describing what the image contains",
  "ocr_text": "string (extracted text via OCR, if any)",
  "detected_elements": {
    "tables": [
      {
        "title": "string",
        "headers": ["string"],
        "rows": [["string"]]
      }
    ],
    "forms": [
      {
        "field": "string",
        "value": "string"
      }
    ],
    "amounts": [{ "concept": "string", "value": "number" }]
  },
  "views": [
    {
      "type": "text",
      "title": "Extracted Text",
      "content": "string"
    },
    {
      "type": "table",
      "title": "string",
      "headers": ["string"],
      "rows": [["string"]]
    },
    {
      "type": "kpi",
      "title": "string",
      "value": "number",
      "unit": "% | € | units | string"
    }
  ]
}
```

---

## GENERIC (any other format)

```json
{
  "type": "generic",
  "summary": "string",
  "extracted_data": "string",
  "views": [
    {
      "type": "kpi",
      "title": "string",
      "value": number,
      "unit": "% | € | units | string"
    },
    {
      "type": "text",
      "title": "string",
      "content": "string"
    }
  ]
}
```

---

## View types reference

| type           | Required fields                              | Use when                                          |
|----------------|----------------------------------------------|---------------------------------------------------|
| `kpi`          | title, value, unit?                          | Single metric highlight                           |
| `table`        | title, headers, rows                         | Tabular data                                      |
| `bar`          | title, x_axis, y_axis, data[]                | Comparisons between categories                    |
| `line`         | title, x_axis, y_axis, data[]                | Trends over time                                  |
| `text`         | title, content                               | Summaries, long text sections                     |
| `pie`          | title, data[{label, value}]                  | Distribution / composition (budget, percentages)  |
| `area`         | title, x_axis, y_axis, data[]                | Cumulative trends (enrollment over years)         |
| `metric_delta` | title, value, previous, unit?, trend?        | Year-over-year comparison (↑12% enrollment)       |

### New view schemas

**Pie chart:**
```json
{
  "type": "pie",
  "title": "Budget by Department",
  "data": [
    { "label": "Engineering", "value": 450000 },
    { "label": "Sciences", "value": 320000 },
    { "label": "Arts", "value": 180000 }
  ]
}
```

**Area chart:**
```json
{
  "type": "area",
  "title": "Cumulative Enrollment",
  "x_axis": "Year",
  "y_axis": "Students",
  "data": [
    { "x": "2020", "y": 1200 },
    { "x": "2021", "y": 1450 },
    { "x": "2022", "y": 1800 }
  ]
}
```

**Metric with delta:**
```json
{
  "type": "metric_delta",
  "title": "Total Enrollment",
  "value": 2450,
  "previous": 2180,
  "unit": "students",
  "trend": "up"
}
```
The `trend` field is auto-calculated if omitted (value > previous = "up"). The renderer shows the percentage change and an arrow indicator.
