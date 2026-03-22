"use client";

/**
 * UniDash — DashboardRenderer
 * Renders structured JSON from Hermes/SurfSense into visual components.
 *
 * Supported types: pdf | spreadsheet | docx | generic
 * View types:      kpi | table | bar | line | text
 *
 * Dependencies:
 *   npm install @tremor/react recharts
 */

import {
  BarChart,
  Card,
  LineChart,
  Metric,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
  Text,
  Title,
  Badge,
  Grid,
  Col,
  Divider,
  List,
  ListItem,
} from "@tremor/react";

// ---------------------------------------------------------------------------
// Types (matching DOCSTEMPLATES.md)
// ---------------------------------------------------------------------------

type KpiView = {
  type: "kpi";
  title: string;
  value: number;
  unit?: string;
};

type TableView = {
  type: "table";
  title: string;
  headers: string[];
  rows: string[][];
};

type BarView = {
  type: "bar";
  title: string;
  x_axis: string;
  y_axis: string;
  data: { x: string; y: number }[];
};

type LineView = {
  type: "line";
  title: string;
  x_axis: string;
  y_axis: string;
  data: { x: string; y: number }[];
};

type TextView = {
  type: "text";
  title: string;
  content: string;
};

type AnyView = KpiView | TableView | BarView | LineView | TextView;

type PdfData = {
  type: "pdf";
  summary: string;
  entities?: {
    persons?: string[];
    dates?: string[];
    amounts?: { concept: string; value: number }[];
  };
  tables_detected?: { title: string; headers: string[]; rows: string[][] }[];
  key_text?: string;
  views: AnyView[];
};

type SpreadsheetData = {
  type: "spreadsheet";
  sheets?: { name: string; headers: string[]; rows: string[][] }[];
  calculated_metrics?: { name: string; value: number }[];
  views: AnyView[];
};

type DocxData = {
  type: "docx";
  summary: string;
  sections?: { title: string; content: string }[];
  tables?: { title: string; headers: string[]; rows: string[][] }[];
  views: AnyView[];
};

type GenericData = {
  type: "generic";
  summary: string;
  extracted_data?: string;
  views: AnyView[];
};

type SummaryData = {
  type: "summary";
  content: string;
  query: string;
};

type DashboardData = PdfData | SpreadsheetData | DocxData | GenericData | SummaryData;

// ---------------------------------------------------------------------------
// View renderers
// ---------------------------------------------------------------------------

function KpiCard({ view }: { view: KpiView }) {
  return (
    <Card className="p-4">
      <Text className="text-sm text-gray-500">{view.title}</Text>
      <Metric className="mt-1">
        {typeof view.value === "number"
          ? view.value.toLocaleString()
          : String(view.value)}
        {view.unit && (
          <span className="text-lg font-normal text-gray-400 ml-1">
            {view.unit}
          </span>
        )}
      </Metric>
    </Card>
  );
}

function TableCard({ view }: { view: TableView }) {
  return (
    <Card className="p-4">
      <Title className="mb-3">{view.title}</Title>
      <Table>
        <TableHead>
          <TableRow>
            {view.headers.map((h, i) => (
              <TableHeaderCell key={i}>{h}</TableHeaderCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {view.rows.map((row, ri) => (
            <TableRow key={ri}>
              {row.map((cell, ci) => (
                <TableCell key={ci}>{cell}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

function BarCard({ view }: { view: BarView }) {
  const chartData = view.data.map((d) => ({
    name: d.x,
    [view.y_axis]: d.y,
  }));
  return (
    <Card className="p-4">
      <Title className="mb-3">{view.title}</Title>
      <BarChart
        data={chartData}
        index="name"
        categories={[view.y_axis]}
        colors={["blue"]}
        yAxisWidth={48}
        className="h-48"
      />
    </Card>
  );
}

function LineCard({ view }: { view: LineView }) {
  const chartData = view.data.map((d) => ({
    name: d.x,
    [view.y_axis]: d.y,
  }));
  return (
    <Card className="p-4">
      <Title className="mb-3">{view.title}</Title>
      <LineChart
        data={chartData}
        index="name"
        categories={[view.y_axis]}
        colors={["indigo"]}
        yAxisWidth={48}
        className="h-48"
      />
    </Card>
  );
}

function TextCard({ view }: { view: TextView }) {
  return (
    <Card className="p-4">
      <Title className="mb-2">{view.title}</Title>
      <Text className="whitespace-pre-wrap text-sm leading-relaxed">
        {view.content}
      </Text>
    </Card>
  );
}

function ViewRenderer({ view }: { view: AnyView }) {
  switch (view.type) {
    case "kpi":
      return <KpiCard view={view} />;
    case "table":
      return <TableCard view={view} />;
    case "bar":
      return <BarCard view={view} />;
    case "line":
      return <LineCard view={view} />;
    case "text":
      return <TextCard view={view} />;
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Section: KPIs in a row
// ---------------------------------------------------------------------------

function KpiRow({ views }: { views: KpiView[] }) {
  if (!views.length) return null;
  return (
    <Grid numItemsSm={2} numItemsLg={4} className="gap-4 mb-4">
      {views.map((v, i) => (
        <KpiCard key={i} view={v} />
      ))}
    </Grid>
  );
}

// ---------------------------------------------------------------------------
// Type badge
// ---------------------------------------------------------------------------

const TYPE_COLORS: Record<string, string> = {
  pdf: "red",
  spreadsheet: "green",
  docx: "blue",
  generic: "gray",
  summary: "yellow",
};

const TYPE_LABELS: Record<string, string> = {
  pdf: "PDF",
  spreadsheet: "Spreadsheet",
  docx: "Word Document",
  generic: "Document",
  summary: "Summary",
};

// ---------------------------------------------------------------------------
// Per-type layouts
// ---------------------------------------------------------------------------

function PdfLayout({ data }: { data: PdfData }) {
  const kpis = data.views.filter((v) => v.type === "kpi") as KpiView[];
  const others = data.views.filter((v) => v.type !== "kpi");

  return (
    <div className="space-y-4">
      {/* Summary */}
      <Card className="p-4 bg-gray-50">
        <Text className="text-sm leading-relaxed">{data.summary}</Text>
      </Card>

      {/* Entities */}
      {data.entities && (
        <div className="flex flex-wrap gap-2">
          {data.entities.persons?.map((p, i) => (
            <Badge key={i} color="blue">{p}</Badge>
          ))}
          {data.entities.dates?.map((d, i) => (
            <Badge key={i} color="green">{d}</Badge>
          ))}
          {data.entities.amounts?.map((a, i) => (
            <Badge key={i} color="amber">
              {a.concept}: {a.value.toLocaleString()}
            </Badge>
          ))}
        </div>
      )}

      {/* KPIs */}
      <KpiRow views={kpis} />

      {/* Other views */}
      <div className="space-y-4">
        {others.map((v, i) => (
          <ViewRenderer key={i} view={v} />
        ))}
      </div>

      {/* Key text */}
      {data.key_text && (
        <Card className="p-4">
          <Title className="mb-2 text-sm font-semibold text-gray-600">
            Key Extracts
          </Title>
          <Text className="text-sm leading-relaxed whitespace-pre-wrap">
            {data.key_text}
          </Text>
        </Card>
      )}
    </div>
  );
}

function SpreadsheetLayout({ data }: { data: SpreadsheetData }) {
  const kpis = data.views.filter((v) => v.type === "kpi") as KpiView[];
  const others = data.views.filter((v) => v.type !== "kpi");

  return (
    <div className="space-y-4">
      {/* Calculated metrics as KPIs */}
      {data.calculated_metrics && data.calculated_metrics.length > 0 && (
        <Grid numItemsSm={2} numItemsLg={4} className="gap-4">
          {data.calculated_metrics.map((m, i) => (
            <Card key={i} className="p-4">
              <Text className="text-sm text-gray-500 capitalize">{m.name}</Text>
              <Metric className="mt-1">{m.value.toLocaleString()}</Metric>
            </Card>
          ))}
        </Grid>
      )}

      {/* Views KPIs */}
      <KpiRow views={kpis} />

      {/* Charts and tables */}
      <div className="space-y-4">
        {others.map((v, i) => (
          <ViewRenderer key={i} view={v} />
        ))}
      </div>

      {/* Raw sheet data */}
      {data.sheets?.map((sheet, si) => (
        <Card key={si} className="p-4">
          <Title className="mb-3">{sheet.name}</Title>
          <Table>
            <TableHead>
              <TableRow>
                {sheet.headers.map((h, i) => (
                  <TableHeaderCell key={i}>{h}</TableHeaderCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {sheet.rows.slice(0, 20).map((row, ri) => (
                <TableRow key={ri}>
                  {row.map((cell, ci) => (
                    <TableCell key={ci}>{cell}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {sheet.rows.length > 20 && (
            <Text className="text-xs text-gray-400 mt-2">
              Showing 20 of {sheet.rows.length} rows
            </Text>
          )}
        </Card>
      ))}
    </div>
  );
}

function DocxLayout({ data }: { data: DocxData }) {
  const kpis = data.views.filter((v) => v.type === "kpi") as KpiView[];
  const others = data.views.filter((v) => v.type !== "kpi");

  return (
    <div className="space-y-4">
      <Card className="p-4 bg-gray-50">
        <Text className="text-sm leading-relaxed">{data.summary}</Text>
      </Card>

      <KpiRow views={kpis} />

      <div className="space-y-4">
        {others.map((v, i) => (
          <ViewRenderer key={i} view={v} />
        ))}
      </div>

      {data.sections && data.sections.length > 0 && (
        <Card className="p-4">
          <Title className="mb-3">Document Sections</Title>
          <div className="space-y-4">
            {data.sections.map((s, i) => (
              <div key={i}>
                {i > 0 && <Divider />}
                <Text className="font-semibold text-sm mb-1">{s.title}</Text>
                <Text className="text-sm text-gray-600 leading-relaxed">
                  {s.content}
                </Text>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function GenericLayout({ data }: { data: GenericData }) {
  return (
    <div className="space-y-4">
      <Card className="p-4 bg-gray-50">
        <Text className="text-sm leading-relaxed">{data.summary}</Text>
      </Card>

      {data.views.map((v, i) => (
        <ViewRenderer key={i} view={v} />
      ))}

      {data.extracted_data && (
        <Card className="p-4">
          <Title className="mb-2 text-sm">Extracted Data</Title>
          <Text className="text-sm whitespace-pre-wrap font-mono text-gray-600">
            {data.extracted_data}
          </Text>
        </Card>
      )}
    </div>
  );
}

function SummaryLayout({ data }: { data: SummaryData }) {
  return (
    <Card className="p-4">
      <Text className="text-xs text-gray-400 mb-2">Query: {data.query}</Text>
      <Text className="text-sm leading-relaxed whitespace-pre-wrap">
        {data.content}
      </Text>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface DashboardRendererProps {
  data: DashboardData | null;
  isLoading?: boolean;
  filename?: string;
}

export default function DashboardRenderer({
  data,
  isLoading = false,
  filename,
}: DashboardRendererProps) {
  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-24 bg-gray-100 rounded-xl" />
        <Grid numItemsSm={2} numItemsLg={4} className="gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 bg-gray-100 rounded-xl" />
          ))}
        </Grid>
        <div className="h-48 bg-gray-100 rounded-xl" />
      </div>
    );
  }

  if (!data) {
    return (
      <Card className="p-8 text-center">
        <Text className="text-gray-400">No data to display</Text>
      </Card>
    );
  }

  const badgeColor = TYPE_COLORS[data.type] ?? "gray";
  const typeLabel = TYPE_LABELS[data.type] ?? data.type;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Badge color={badgeColor as any}>{typeLabel}</Badge>
        {filename && (
          <Text className="text-sm text-gray-500 truncate">{filename}</Text>
        )}
      </div>

      {/* Content */}
      {data.type === "pdf" && <PdfLayout data={data} />}
      {data.type === "spreadsheet" && <SpreadsheetLayout data={data} />}
      {data.type === "docx" && <DocxLayout data={data} />}
      {data.type === "generic" && <GenericLayout data={data} />}
      {data.type === "summary" && <SummaryLayout data={data} />}
    </div>
  );
}
