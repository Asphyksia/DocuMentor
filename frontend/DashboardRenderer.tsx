"use client";

/**
 * DocuMentor — DashboardRenderer
 * Renders structured JSON from Hermes/SurfSense into visual components.
 *
 * Supported types: pdf | spreadsheet | docx | pptx | html | image | generic | summary
 * View types:      kpi | table | bar | line | text | pie | area | metric_delta
 *
 * Dependencies:
 *   npm install @tremor/react recharts lucide-react
 */

import {
  BarChart,
  Card,
  LineChart,
  AreaChart,
  DonutChart,
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
  Divider,
} from "@tremor/react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

// ---------------------------------------------------------------------------
// View types (matching DOCSTEMPLATES.md)
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

type PieView = {
  type: "pie";
  title: string;
  data: { label: string; value: number }[];
};

type AreaView = {
  type: "area";
  title: string;
  x_axis: string;
  y_axis: string;
  data: { x: string; y: number }[];
};

type MetricDeltaView = {
  type: "metric_delta";
  title: string;
  value: number;
  previous: number;
  unit?: string;
  trend?: "up" | "down" | "flat";
};

type AnyView = KpiView | TableView | BarView | LineView | TextView | PieView | AreaView | MetricDeltaView;

// ---------------------------------------------------------------------------
// Document types
// ---------------------------------------------------------------------------

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

type PptxData = {
  type: "pptx";
  summary: string;
  slide_count?: number;
  slides?: { number: number; title: string; content: string; has_table?: boolean; has_chart?: boolean }[];
  tables?: { title: string; headers: string[]; rows: string[][] }[];
  views: AnyView[];
};

type HtmlData = {
  type: "html";
  summary: string;
  page_title?: string;
  headings?: string[];
  tables?: { title: string; headers: string[]; rows: string[][] }[];
  links_count?: number;
  views: AnyView[];
};

type ImageData = {
  type: "image";
  summary: string;
  ocr_text?: string;
  detected_elements?: {
    tables?: { title: string; headers: string[]; rows: string[][] }[];
    forms?: { field: string; value: string }[];
    amounts?: { concept: string; value: number }[];
  };
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

type DashboardData = PdfData | SpreadsheetData | DocxData | PptxData | HtmlData | ImageData | GenericData | SummaryData;

// ---------------------------------------------------------------------------
// View renderers
// ---------------------------------------------------------------------------

function KpiCard({ view }: { view: KpiView }) {
  return (
    <Card className="p-4">
      <Text className="text-sm text-gray-500">{view.title}</Text>
      <Metric className="mt-1">
        {typeof view.value === "number" ? view.value.toLocaleString() : String(view.value)}
        {view.unit && <span className="text-lg font-normal text-gray-400 ml-1">{view.unit}</span>}
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
  const chartData = view.data.map((d) => ({ name: d.x, [view.y_axis]: d.y }));
  return (
    <Card className="p-4">
      <Title className="mb-3">{view.title}</Title>
      <BarChart data={chartData} index="name" categories={[view.y_axis]} colors={["blue"]} yAxisWidth={48} className="h-48" />
    </Card>
  );
}

function LineCard({ view }: { view: LineView }) {
  const chartData = view.data.map((d) => ({ name: d.x, [view.y_axis]: d.y }));
  return (
    <Card className="p-4">
      <Title className="mb-3">{view.title}</Title>
      <LineChart data={chartData} index="name" categories={[view.y_axis]} colors={["indigo"]} yAxisWidth={48} className="h-48" />
    </Card>
  );
}

function TextCard({ view }: { view: TextView }) {
  return (
    <Card className="p-4">
      <Title className="mb-2">{view.title}</Title>
      <Text className="whitespace-pre-wrap text-sm leading-relaxed">{view.content}</Text>
    </Card>
  );
}

function PieCard({ view }: { view: PieView }) {
  const chartData = view.data.map((d) => ({ name: d.label, value: d.value }));
  const colors = ["blue", "cyan", "indigo", "violet", "fuchsia", "rose", "amber", "emerald"];
  return (
    <Card className="p-4">
      <Title className="mb-3">{view.title}</Title>
      <DonutChart
        data={chartData}
        category="value"
        index="name"
        colors={colors.slice(0, chartData.length)}
        className="h-48"
        showAnimation
      />
    </Card>
  );
}

function AreaCard({ view }: { view: AreaView }) {
  const chartData = view.data.map((d) => ({ name: d.x, [view.y_axis]: d.y }));
  return (
    <Card className="p-4">
      <Title className="mb-3">{view.title}</Title>
      <AreaChart data={chartData} index="name" categories={[view.y_axis]} colors={["cyan"]} yAxisWidth={48} className="h-48" />
    </Card>
  );
}

function MetricDeltaCard({ view }: { view: MetricDeltaView }) {
  const delta = view.previous !== 0 ? ((view.value - view.previous) / view.previous) * 100 : 0;
  const trend = view.trend || (delta > 0 ? "up" : delta < 0 ? "down" : "flat");
  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const trendColor = trend === "up" ? "text-green-400" : trend === "down" ? "text-red-400" : "text-gray-400";
  const bgColor = trend === "up" ? "bg-green-500/10" : trend === "down" ? "bg-red-500/10" : "bg-gray-500/10";

  return (
    <Card className="p-4">
      <Text className="text-sm text-gray-500">{view.title}</Text>
      <div className="flex items-end gap-3 mt-1">
        <Metric>
          {view.value.toLocaleString()}
          {view.unit && <span className="text-lg font-normal text-gray-400 ml-1">{view.unit}</span>}
        </Metric>
        <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${bgColor} ${trendColor}`}>
          <TrendIcon className="w-3 h-3" />
          <span>{Math.abs(delta).toFixed(1)}%</span>
        </div>
      </div>
      <Text className="text-xs text-gray-500 mt-1">
        vs. previous: {view.previous.toLocaleString()}{view.unit ? ` ${view.unit}` : ""}
      </Text>
    </Card>
  );
}

function ViewRenderer({ view }: { view: AnyView }) {
  switch (view.type) {
    case "kpi": return <KpiCard view={view} />;
    case "table": return <TableCard view={view} />;
    case "bar": return <BarCard view={view} />;
    case "line": return <LineCard view={view} />;
    case "text": return <TextCard view={view} />;
    case "pie": return <PieCard view={view} />;
    case "area": return <AreaCard view={view} />;
    case "metric_delta": return <MetricDeltaCard view={view} />;
    default: return null;
  }
}

// ---------------------------------------------------------------------------
// KPIs + MetricDeltas in a row
// ---------------------------------------------------------------------------

function KpiRow({ views }: { views: (KpiView | MetricDeltaView)[] }) {
  if (!views.length) return null;
  return (
    <Grid numItemsSm={2} numItemsLg={4} className="gap-4 mb-4">
      {views.map((v, i) => (
        v.type === "metric_delta" ? <MetricDeltaCard key={i} view={v} /> : <KpiCard key={i} view={v} />
      ))}
    </Grid>
  );
}

// ---------------------------------------------------------------------------
// Type badge config
// ---------------------------------------------------------------------------

const TYPE_COLORS: Record<string, string> = {
  pdf: "red", spreadsheet: "green", docx: "blue", pptx: "orange",
  html: "purple", image: "yellow", generic: "gray", summary: "cyan",
};

const TYPE_LABELS: Record<string, string> = {
  pdf: "PDF", spreadsheet: "Spreadsheet", docx: "Word", pptx: "PowerPoint",
  html: "HTML", image: "Image / Scan", generic: "Document", summary: "Summary",
};

// ---------------------------------------------------------------------------
// Per-type layouts
// ---------------------------------------------------------------------------

function PdfLayout({ data }: { data: PdfData }) {
  const kpis = data.views.filter((v) => v.type === "kpi" || v.type === "metric_delta") as (KpiView | MetricDeltaView)[];
  const others = data.views.filter((v) => v.type !== "kpi" && v.type !== "metric_delta");
  return (
    <div className="space-y-4">
      <Card className="p-4 bg-gray-800/50 border-gray-700/50">
        <Text className="text-sm leading-relaxed">{data.summary}</Text>
      </Card>
      {data.entities && (
        <div className="flex flex-wrap gap-2">
          {data.entities.persons?.map((p, i) => <Badge key={`p${i}`} color="blue">{p}</Badge>)}
          {data.entities.dates?.map((d, i) => <Badge key={`d${i}`} color="green">{d}</Badge>)}
          {data.entities.amounts?.map((a, i) => <Badge key={`a${i}`} color="amber">{a.concept}: {a.value.toLocaleString()}</Badge>)}
        </div>
      )}
      <KpiRow views={kpis} />
      <div className="space-y-4">{others.map((v, i) => <ViewRenderer key={i} view={v} />)}</div>
      {data.key_text && (
        <Card className="p-4">
          <Title className="mb-2 text-sm font-semibold text-gray-400">Key Extracts</Title>
          <Text className="text-sm leading-relaxed whitespace-pre-wrap">{data.key_text}</Text>
        </Card>
      )}
    </div>
  );
}

function SpreadsheetLayout({ data }: { data: SpreadsheetData }) {
  const kpis = data.views.filter((v) => v.type === "kpi" || v.type === "metric_delta") as (KpiView | MetricDeltaView)[];
  const others = data.views.filter((v) => v.type !== "kpi" && v.type !== "metric_delta");
  return (
    <div className="space-y-4">
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
      <KpiRow views={kpis} />
      <div className="space-y-4">{others.map((v, i) => <ViewRenderer key={i} view={v} />)}</div>
      {data.sheets?.map((sheet, si) => (
        <Card key={si} className="p-4">
          <Title className="mb-3">{sheet.name}</Title>
          <Table>
            <TableHead>
              <TableRow>{sheet.headers.map((h, i) => <TableHeaderCell key={i}>{h}</TableHeaderCell>)}</TableRow>
            </TableHead>
            <TableBody>
              {sheet.rows.slice(0, 20).map((row, ri) => (
                <TableRow key={ri}>{row.map((cell, ci) => <TableCell key={ci}>{cell}</TableCell>)}</TableRow>
              ))}
            </TableBody>
          </Table>
          {sheet.rows.length > 20 && <Text className="text-xs text-gray-500 mt-2">Showing 20 of {sheet.rows.length} rows</Text>}
        </Card>
      ))}
    </div>
  );
}

function DocxLayout({ data }: { data: DocxData }) {
  const kpis = data.views.filter((v) => v.type === "kpi" || v.type === "metric_delta") as (KpiView | MetricDeltaView)[];
  const others = data.views.filter((v) => v.type !== "kpi" && v.type !== "metric_delta");
  return (
    <div className="space-y-4">
      <Card className="p-4 bg-gray-800/50 border-gray-700/50"><Text className="text-sm leading-relaxed">{data.summary}</Text></Card>
      <KpiRow views={kpis} />
      <div className="space-y-4">{others.map((v, i) => <ViewRenderer key={i} view={v} />)}</div>
      {data.sections && data.sections.length > 0 && (
        <Card className="p-4">
          <Title className="mb-3">Document Sections</Title>
          <div className="space-y-4">
            {data.sections.map((s, i) => (
              <div key={i}>
                {i > 0 && <Divider />}
                <Text className="font-semibold text-sm mb-1">{s.title}</Text>
                <Text className="text-sm text-gray-400 leading-relaxed">{s.content}</Text>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function PptxLayout({ data }: { data: PptxData }) {
  const kpis = data.views.filter((v) => v.type === "kpi" || v.type === "metric_delta") as (KpiView | MetricDeltaView)[];
  const others = data.views.filter((v) => v.type !== "kpi" && v.type !== "metric_delta");
  return (
    <div className="space-y-4">
      <Card className="p-4 bg-gray-800/50 border-gray-700/50">
        <div className="flex items-center gap-3 mb-2">
          <Text className="text-sm leading-relaxed flex-1">{data.summary}</Text>
          {data.slide_count && <Badge color="orange">{data.slide_count} slides</Badge>}
        </div>
      </Card>
      <KpiRow views={kpis} />
      <div className="space-y-4">{others.map((v, i) => <ViewRenderer key={i} view={v} />)}</div>
      {data.slides && data.slides.length > 0 && (
        <Card className="p-4">
          <Title className="mb-3">Slide Overview</Title>
          <div className="space-y-3">
            {data.slides.map((s, i) => (
              <div key={i} className="flex gap-3 items-start">
                <div className="w-8 h-8 rounded-lg bg-orange-500/10 text-orange-400 flex items-center justify-center text-xs font-bold flex-shrink-0">
                  {s.number}
                </div>
                <div className="flex-1 min-w-0">
                  <Text className="font-semibold text-sm">{s.title}</Text>
                  <Text className="text-xs text-gray-500 mt-0.5 line-clamp-2">{s.content}</Text>
                  <div className="flex gap-1 mt-1">
                    {s.has_table && <Badge size="xs" color="green">table</Badge>}
                    {s.has_chart && <Badge size="xs" color="blue">chart</Badge>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function HtmlLayout({ data }: { data: HtmlData }) {
  const kpis = data.views.filter((v) => v.type === "kpi" || v.type === "metric_delta") as (KpiView | MetricDeltaView)[];
  const others = data.views.filter((v) => v.type !== "kpi" && v.type !== "metric_delta");
  return (
    <div className="space-y-4">
      <Card className="p-4 bg-gray-800/50 border-gray-700/50">
        {data.page_title && <Title className="mb-2 text-sm">{data.page_title}</Title>}
        <Text className="text-sm leading-relaxed">{data.summary}</Text>
        <div className="flex gap-2 mt-2">
          {data.links_count !== undefined && <Badge color="purple">{data.links_count} links</Badge>}
          {data.headings && <Badge color="indigo">{data.headings.length} sections</Badge>}
        </div>
      </Card>
      <KpiRow views={kpis} />
      <div className="space-y-4">{others.map((v, i) => <ViewRenderer key={i} view={v} />)}</div>
    </div>
  );
}

function ImageLayout({ data }: { data: ImageData }) {
  const kpis = data.views.filter((v) => v.type === "kpi" || v.type === "metric_delta") as (KpiView | MetricDeltaView)[];
  const others = data.views.filter((v) => v.type !== "kpi" && v.type !== "metric_delta");
  return (
    <div className="space-y-4">
      <Card className="p-4 bg-gray-800/50 border-gray-700/50">
        <Text className="text-sm leading-relaxed">{data.summary}</Text>
      </Card>
      {data.ocr_text && (
        <Card className="p-4">
          <Title className="mb-2 text-sm">Extracted Text (OCR)</Title>
          <Text className="text-sm whitespace-pre-wrap font-mono text-gray-400 leading-relaxed">{data.ocr_text}</Text>
        </Card>
      )}
      {data.detected_elements?.forms && data.detected_elements.forms.length > 0 && (
        <Card className="p-4">
          <Title className="mb-3 text-sm">Form Fields</Title>
          <Table>
            <TableHead><TableRow><TableHeaderCell>Field</TableHeaderCell><TableHeaderCell>Value</TableHeaderCell></TableRow></TableHead>
            <TableBody>
              {data.detected_elements.forms.map((f, i) => (
                <TableRow key={i}><TableCell>{f.field}</TableCell><TableCell>{f.value}</TableCell></TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
      <KpiRow views={kpis} />
      <div className="space-y-4">{others.map((v, i) => <ViewRenderer key={i} view={v} />)}</div>
    </div>
  );
}

function GenericLayout({ data }: { data: GenericData }) {
  return (
    <div className="space-y-4">
      <Card className="p-4 bg-gray-800/50 border-gray-700/50"><Text className="text-sm leading-relaxed">{data.summary}</Text></Card>
      {data.views.map((v, i) => <ViewRenderer key={i} view={v} />)}
      {data.extracted_data && (
        <Card className="p-4">
          <Title className="mb-2 text-sm">Extracted Data</Title>
          <Text className="text-sm whitespace-pre-wrap font-mono text-gray-400">{data.extracted_data}</Text>
        </Card>
      )}
    </div>
  );
}

function SummaryLayout({ data }: { data: SummaryData }) {
  return (
    <Card className="p-4">
      <Text className="text-xs text-gray-500 mb-2">Query: {data.query}</Text>
      <Text className="text-sm leading-relaxed whitespace-pre-wrap">{data.content}</Text>
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

export default function DashboardRenderer({ data, isLoading = false, filename }: DashboardRendererProps) {
  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-24 bg-gray-800 rounded-xl" />
        <Grid numItemsSm={2} numItemsLg={4} className="gap-4">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-20 bg-gray-800 rounded-xl" />)}
        </Grid>
        <div className="h-48 bg-gray-800 rounded-xl" />
      </div>
    );
  }

  if (!data) {
    return <Card className="p-8 text-center"><Text className="text-gray-500">No data to display</Text></Card>;
  }

  const badgeColor = TYPE_COLORS[data.type] ?? "gray";
  const typeLabel = TYPE_LABELS[data.type] ?? data.type;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Badge color={badgeColor as any}>{typeLabel}</Badge>
        {filename && <Text className="text-sm text-gray-500 truncate">{filename}</Text>}
      </div>
      {data.type === "pdf" && <PdfLayout data={data} />}
      {data.type === "spreadsheet" && <SpreadsheetLayout data={data} />}
      {data.type === "docx" && <DocxLayout data={data} />}
      {data.type === "pptx" && <PptxLayout data={data} />}
      {data.type === "html" && <HtmlLayout data={data} />}
      {data.type === "image" && <ImageLayout data={data} />}
      {data.type === "generic" && <GenericLayout data={data} />}
      {data.type === "summary" && <SummaryLayout data={data} />}
    </div>
  );
}
