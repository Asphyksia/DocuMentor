# DOCSTEMPLATES.md — JSON Templates by File Extension

## MANDATORY Rules
- ALWAYS use `response_format: json_object`
- Maximum 4 elements in `views[]`
- Validate JSON before sending
- Use ONLY these templates
- `type` field must match exactly: `pdf | spreadsheet | docx | generic`

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

| type    | Required fields                          | Use when                              |
|---------|------------------------------------------|---------------------------------------|
| `kpi`   | title, value, unit?                      | Single metric highlight               |
| `table` | title, headers, rows                     | Tabular data                          |
| `bar`   | title, x_axis, y_axis, data[]            | Comparisons between categories        |
| `line`  | title, x_axis, y_axis, data[]            | Trends over time                      |
| `text`  | title, content                           | Summaries, long text sections         |
