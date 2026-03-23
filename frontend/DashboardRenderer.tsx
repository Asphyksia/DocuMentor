"use client";

import { cn } from "./lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "./components/ui/table";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

// ---------------------------------------------------------------------------
// Chart colors
// ---------------------------------------------------------------------------
const COLORS = ["#3b82f6","#06b6d4","#6366f1","#8b5cf6","#d946ef","#f43f5e","#f59e0b","#10b981"];
const chartTheme = {
  grid: "#1f2937", axis: "#6b7280", tooltip: { bg: "#111827", border: "#374151" },
};

// ---------------------------------------------------------------------------
// View types
// ---------------------------------------------------------------------------
type KpiView = { type: "kpi"; title: string; value: number; unit?: string };
type TableView = { type: "table"; title: string; headers: string[]; rows: string[][] };
type BarView = { type: "bar"; title: string; x_axis: string; y_axis: string; data: { x: string; y: number }[] };
type LineView = { type: "line"; title: string; x_axis: string; y_axis: string; data: { x: string; y: number }[] };
type TextView = { type: "text"; title: string; content: string };
type PieView = { type: "pie"; title: string; data: { label: string; value: number }[] };
type AreaView = { type: "area"; title: string; x_axis: string; y_axis: string; data: { x: string; y: number }[] };
type MetricDeltaView = { type: "metric_delta"; title: string; value: number; previous: number; unit?: string; trend?: "up" | "down" | "flat" };
type AnyView = KpiView | TableView | BarView | LineView | TextView | PieView | AreaView | MetricDeltaView;

// Document types
type PdfData = { type: "pdf"; summary: string; entities?: { persons?: string[]; dates?: string[]; amounts?: { concept: string; value: number }[] }; tables_detected?: { title: string; headers: string[]; rows: string[][] }[]; key_text?: string; views: AnyView[] };
type SpreadsheetData = { type: "spreadsheet"; sheets?: { name: string; headers: string[]; rows: string[][] }[]; calculated_metrics?: { name: string; value: number }[]; views: AnyView[] };
type DocxData = { type: "docx"; summary: string; sections?: { title: string; content: string }[]; tables?: { title: string; headers: string[]; rows: string[][] }[]; views: AnyView[] };
type PptxData = { type: "pptx"; summary: string; slide_count?: number; slides?: { number: number; title: string; content: string; has_table?: boolean; has_chart?: boolean }[]; tables?: { title: string; headers: string[]; rows: string[][] }[]; views: AnyView[] };
type HtmlData = { type: "html"; summary: string; page_title?: string; headings?: string[]; tables?: { title: string; headers: string[]; rows: string[][] }[]; links_count?: number; views: AnyView[] };
type ImageData = { type: "image"; summary: string; ocr_text?: string; detected_elements?: { tables?: { title: string; headers: string[]; rows: string[][] }[]; forms?: { field: string; value: string }[]; amounts?: { concept: string; value: number }[] }; views: AnyView[] };
type GenericData = { type: "generic"; summary: string; extracted_data?: string; views: AnyView[] };
type SummaryData = { type: "summary"; content: string; query: string };
type DashboardData = PdfData | SpreadsheetData | DocxData | PptxData | HtmlData | ImageData | GenericData | SummaryData;

// ---------------------------------------------------------------------------
// View renderers
// ---------------------------------------------------------------------------
function KpiCard({ view }: { view: KpiView }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-sm text-muted-foreground">{view.title}</p>
        <p className="text-2xl font-bold mt-1">
          {typeof view.value === "number" ? view.value.toLocaleString() : String(view.value)}
          {view.unit && <span className="text-base font-normal text-muted-foreground ml-1">{view.unit}</span>}
        </p>
      </CardContent>
    </Card>
  );
}

function TableCard({ view }: { view: TableView }) {
  return (
    <Card>
      <CardHeader className="pb-3"><CardTitle className="text-sm">{view.title}</CardTitle></CardHeader>
      <CardContent className="px-0 pb-0">
        <Table>
          <TableHeader>
            <TableRow>{view.headers.map((h, i) => <TableHead key={i}>{h}</TableHead>)}</TableRow>
          </TableHeader>
          <TableBody>
            {view.rows.map((row, ri) => (
              <TableRow key={ri}>{row.map((cell, ci) => <TableCell key={ci}>{cell}</TableCell>)}</TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function BarCard({ view }: { view: BarView }) {
  const data = view.data.map(d => ({ name: d.x, [view.y_axis]: d.y }));
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">{view.title}</CardTitle></CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis dataKey="name" tick={{ fill: chartTheme.axis, fontSize: 12 }} />
            <YAxis tick={{ fill: chartTheme.axis, fontSize: 12 }} />
            <Tooltip contentStyle={{ backgroundColor: chartTheme.tooltip.bg, border: `1px solid ${chartTheme.tooltip.border}`, borderRadius: 8, color: "#f3f4f6" }} />
            <Bar dataKey={view.y_axis} fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function LineCard({ view }: { view: LineView }) {
  const data = view.data.map(d => ({ name: d.x, [view.y_axis]: d.y }));
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">{view.title}</CardTitle></CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis dataKey="name" tick={{ fill: chartTheme.axis, fontSize: 12 }} />
            <YAxis tick={{ fill: chartTheme.axis, fontSize: 12 }} />
            <Tooltip contentStyle={{ backgroundColor: chartTheme.tooltip.bg, border: `1px solid ${chartTheme.tooltip.border}`, borderRadius: 8, color: "#f3f4f6" }} />
            <Line type="monotone" dataKey={view.y_axis} stroke="#6366f1" strokeWidth={2} dot={{ fill: "#6366f1" }} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function TextCard({ view }: { view: TextView }) {
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">{view.title}</CardTitle></CardHeader>
      <CardContent><p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">{view.content}</p></CardContent>
    </Card>
  );
}

function PieCard({ view }: { view: PieView }) {
  const data = view.data.map(d => ({ name: d.label, value: d.value }));
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">{view.title}</CardTitle></CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={data} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" nameKey="name" paddingAngle={2}>
              {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={{ backgroundColor: chartTheme.tooltip.bg, border: `1px solid ${chartTheme.tooltip.border}`, borderRadius: 8, color: "#f3f4f6" }} />
            <Legend wrapperStyle={{ fontSize: 12, color: chartTheme.axis }} />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function AreaCard({ view }: { view: AreaView }) {
  const data = view.data.map(d => ({ name: d.x, [view.y_axis]: d.y }));
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">{view.title}</CardTitle></CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis dataKey="name" tick={{ fill: chartTheme.axis, fontSize: 12 }} />
            <YAxis tick={{ fill: chartTheme.axis, fontSize: 12 }} />
            <Tooltip contentStyle={{ backgroundColor: chartTheme.tooltip.bg, border: `1px solid ${chartTheme.tooltip.border}`, borderRadius: 8, color: "#f3f4f6" }} />
            <Area type="monotone" dataKey={view.y_axis} stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.15} />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function MetricDeltaCard({ view }: { view: MetricDeltaView }) {
  const delta = view.previous !== 0 ? ((view.value - view.previous) / view.previous) * 100 : 0;
  const trend = view.trend || (delta > 0 ? "up" : delta < 0 ? "down" : "flat");
  const Icon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-sm text-muted-foreground">{view.title}</p>
        <div className="flex items-end gap-3 mt-1">
          <p className="text-2xl font-bold">
            {view.value.toLocaleString()}
            {view.unit && <span className="text-base font-normal text-muted-foreground ml-1">{view.unit}</span>}
          </p>
          <span className={cn("flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
            trend === "up" && "bg-green-500/10 text-green-400",
            trend === "down" && "bg-red-500/10 text-red-400",
            trend === "flat" && "bg-gray-500/10 text-gray-400"
          )}>
            <Icon className="w-3 h-3" />{Math.abs(delta).toFixed(1)}%
          </span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">vs. previous: {view.previous.toLocaleString()}{view.unit ? ` ${view.unit}` : ""}</p>
      </CardContent>
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

function KpiRow({ views }: { views: (KpiView | MetricDeltaView)[] }) {
  if (!views.length) return null;
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
      {views.map((v, i) => v.type === "metric_delta" ? <MetricDeltaCard key={i} view={v} /> : <KpiCard key={i} view={v} />)}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Type config
// ---------------------------------------------------------------------------
const TYPE_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  pdf: "destructive", spreadsheet: "default", docx: "default", pptx: "secondary",
  html: "secondary", image: "outline", generic: "outline", summary: "default",
};
const TYPE_LABELS: Record<string, string> = {
  pdf: "PDF", spreadsheet: "Spreadsheet", docx: "Word", pptx: "PowerPoint",
  html: "HTML", image: "Image / Scan", generic: "Document", summary: "Summary",
};

// ---------------------------------------------------------------------------
// Per-type layouts
// ---------------------------------------------------------------------------
function SummaryCard({ text }: { text: string }) {
  return <Card className="bg-muted/50"><CardContent className="p-4"><p className="text-sm leading-relaxed">{text}</p></CardContent></Card>;
}

function splitViews(views: AnyView[]) {
  const kpis = views.filter(v => v.type === "kpi" || v.type === "metric_delta") as (KpiView | MetricDeltaView)[];
  const others = views.filter(v => v.type !== "kpi" && v.type !== "metric_delta");
  return { kpis, others };
}

function PdfLayout({ data }: { data: PdfData }) {
  const { kpis, others } = splitViews(data.views);
  return (
    <div className="space-y-4">
      <SummaryCard text={data.summary} />
      {data.entities && (
        <div className="flex flex-wrap gap-2">
          {data.entities.persons?.map((p, i) => <Badge key={`p${i}`} variant="default">{p}</Badge>)}
          {data.entities.dates?.map((d, i) => <Badge key={`d${i}`} variant="secondary">{d}</Badge>)}
          {data.entities.amounts?.map((a, i) => <Badge key={`a${i}`} variant="outline">{a.concept}: {a.value.toLocaleString()}</Badge>)}
        </div>
      )}
      <KpiRow views={kpis} />
      <div className="space-y-4">{others.map((v, i) => <ViewRenderer key={i} view={v} />)}</div>
      {data.key_text && <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Key Extracts</CardTitle></CardHeader><CardContent><p className="text-sm leading-relaxed whitespace-pre-wrap">{data.key_text}</p></CardContent></Card>}
    </div>
  );
}

function SpreadsheetLayout({ data }: { data: SpreadsheetData }) {
  const { kpis, others } = splitViews(data.views);
  return (
    <div className="space-y-4">
      {data.calculated_metrics && data.calculated_metrics.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {data.calculated_metrics.map((m, i) => <Card key={i}><CardContent className="p-4"><p className="text-sm text-muted-foreground capitalize">{m.name}</p><p className="text-2xl font-bold mt-1">{m.value.toLocaleString()}</p></CardContent></Card>)}
        </div>
      )}
      <KpiRow views={kpis} />
      <div className="space-y-4">{others.map((v, i) => <ViewRenderer key={i} view={v} />)}</div>
      {data.sheets?.map((sheet, si) => (
        <Card key={si}>
          <CardHeader className="pb-3"><CardTitle className="text-sm">{sheet.name}</CardTitle></CardHeader>
          <CardContent className="px-0 pb-0">
            <Table>
              <TableHeader><TableRow>{sheet.headers.map((h, i) => <TableHead key={i}>{h}</TableHead>)}</TableRow></TableHeader>
              <TableBody>{sheet.rows.slice(0, 20).map((row, ri) => <TableRow key={ri}>{row.map((cell, ci) => <TableCell key={ci}>{cell}</TableCell>)}</TableRow>)}</TableBody>
            </Table>
            {sheet.rows.length > 20 && <p className="text-xs text-muted-foreground px-4 py-2">Showing 20 of {sheet.rows.length} rows</p>}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function DocxLayout({ data }: { data: DocxData }) {
  const { kpis, others } = splitViews(data.views);
  return (
    <div className="space-y-4">
      <SummaryCard text={data.summary} />
      <KpiRow views={kpis} />
      <div className="space-y-4">{others.map((v, i) => <ViewRenderer key={i} view={v} />)}</div>
      {data.sections && data.sections.length > 0 && (
        <Card><CardHeader className="pb-3"><CardTitle className="text-sm">Document Sections</CardTitle></CardHeader><CardContent className="space-y-4">
          {data.sections.map((s, i) => <div key={i}>{i > 0 && <hr className="border-border my-4" />}<p className="font-semibold text-sm mb-1">{s.title}</p><p className="text-sm text-muted-foreground leading-relaxed">{s.content}</p></div>)}
        </CardContent></Card>
      )}
    </div>
  );
}

function PptxLayout({ data }: { data: PptxData }) {
  const { kpis, others } = splitViews(data.views);
  return (
    <div className="space-y-4">
      <Card className="bg-muted/50"><CardContent className="p-4 flex items-center gap-3"><p className="text-sm leading-relaxed flex-1">{data.summary}</p>{data.slide_count && <Badge variant="secondary">{data.slide_count} slides</Badge>}</CardContent></Card>
      <KpiRow views={kpis} />
      <div className="space-y-4">{others.map((v, i) => <ViewRenderer key={i} view={v} />)}</div>
      {data.slides && data.slides.length > 0 && (
        <Card><CardHeader className="pb-3"><CardTitle className="text-sm">Slide Overview</CardTitle></CardHeader><CardContent className="space-y-3">
          {data.slides.map((s, i) => (
            <div key={i} className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-lg bg-orange-500/10 text-orange-400 flex items-center justify-center text-xs font-bold flex-shrink-0">{s.number}</div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm">{s.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{s.content}</p>
                <div className="flex gap-1 mt-1">{s.has_table && <Badge variant="secondary" className="text-[10px] px-1.5 py-0">table</Badge>}{s.has_chart && <Badge variant="default" className="text-[10px] px-1.5 py-0">chart</Badge>}</div>
              </div>
            </div>
          ))}
        </CardContent></Card>
      )}
    </div>
  );
}

function HtmlLayout({ data }: { data: HtmlData }) {
  const { kpis, others } = splitViews(data.views);
  return (
    <div className="space-y-4">
      <Card className="bg-muted/50"><CardContent className="p-4">
        {data.page_title && <p className="font-semibold text-sm mb-2">{data.page_title}</p>}
        <p className="text-sm leading-relaxed">{data.summary}</p>
        <div className="flex gap-2 mt-2">{data.links_count !== undefined && <Badge variant="secondary">{data.links_count} links</Badge>}{data.headings && <Badge variant="outline">{data.headings.length} sections</Badge>}</div>
      </CardContent></Card>
      <KpiRow views={kpis} />
      <div className="space-y-4">{others.map((v, i) => <ViewRenderer key={i} view={v} />)}</div>
    </div>
  );
}

function ImageLayout({ data }: { data: ImageData }) {
  const { kpis, others } = splitViews(data.views);
  return (
    <div className="space-y-4">
      <SummaryCard text={data.summary} />
      {data.ocr_text && <Card><CardHeader className="pb-2"><CardTitle className="text-sm">Extracted Text (OCR)</CardTitle></CardHeader><CardContent><p className="text-sm whitespace-pre-wrap font-mono text-muted-foreground leading-relaxed">{data.ocr_text}</p></CardContent></Card>}
      {data.detected_elements?.forms && data.detected_elements.forms.length > 0 && (
        <Card><CardHeader className="pb-3"><CardTitle className="text-sm">Form Fields</CardTitle></CardHeader><CardContent className="px-0 pb-0">
          <Table><TableHeader><TableRow><TableHead>Field</TableHead><TableHead>Value</TableHead></TableRow></TableHeader>
          <TableBody>{data.detected_elements.forms.map((f, i) => <TableRow key={i}><TableCell>{f.field}</TableCell><TableCell>{f.value}</TableCell></TableRow>)}</TableBody></Table>
        </CardContent></Card>
      )}
      <KpiRow views={kpis} />
      <div className="space-y-4">{others.map((v, i) => <ViewRenderer key={i} view={v} />)}</div>
    </div>
  );
}

function GenericLayout({ data }: { data: GenericData }) {
  return (
    <div className="space-y-4">
      <SummaryCard text={data.summary} />
      {data.views.map((v, i) => <ViewRenderer key={i} view={v} />)}
      {data.extracted_data && <Card><CardHeader className="pb-2"><CardTitle className="text-sm">Extracted Data</CardTitle></CardHeader><CardContent><p className="text-sm whitespace-pre-wrap font-mono text-muted-foreground">{data.extracted_data}</p></CardContent></Card>}
    </div>
  );
}

function SummaryLayout({ data }: { data: SummaryData }) {
  return <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground mb-2">Query: {data.query}</p><p className="text-sm leading-relaxed whitespace-pre-wrap">{data.content}</p></CardContent></Card>;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
interface DashboardRendererProps { data: DashboardData | null; isLoading?: boolean; filename?: string }

export default function DashboardRenderer({ data, isLoading = false, filename }: DashboardRendererProps) {
  if (isLoading) return (
    <div className="space-y-4 animate-pulse">
      <div className="h-24 bg-muted rounded-xl" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">{[1,2,3,4].map(i => <div key={i} className="h-20 bg-muted rounded-xl" />)}</div>
      <div className="h-48 bg-muted rounded-xl" />
    </div>
  );
  if (!data) return <Card className="p-8 text-center"><p className="text-muted-foreground">No data to display</p></Card>;
  const variant = TYPE_COLORS[data.type] ?? "outline";
  const label = TYPE_LABELS[data.type] ?? data.type;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3"><Badge variant={variant}>{label}</Badge>{filename && <p className="text-sm text-muted-foreground truncate">{filename}</p>}</div>
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
