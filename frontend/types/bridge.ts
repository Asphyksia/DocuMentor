/**
 * Bridge Protocol Types
 * ---------------------
 * Discriminated unions for all WebSocket messages between
 * the frontend and the bridge server.
 *
 * These types are the single source of truth for the protocol.
 * If you add a message type to bridge.py, add it here too.
 */

// ===========================================================================
// Outbound (Client → Server)
// ===========================================================================

export type OutboundMessage =
  | { type: "status" }
  | { type: "query"; payload: QueryPayload }
  | { type: "upload"; payload: UploadPayload }
  | { type: "list_docs"; payload: ListDocsPayload }
  | { type: "list_spaces" }
  | { type: "create_space"; payload: CreateSpacePayload }
  | { type: "extract"; payload: ExtractPayload }
  | { type: "delete_document"; payload: DeleteDocumentPayload }
  | { type: "delete_space"; payload: DeleteSpacePayload }
  | { type: "search_documents"; payload: SearchDocumentsPayload }
  | { type: "clear" };

export interface QueryPayload {
  query: string;
  search_space_id: number;
  thread_id?: string;
}

export interface UploadPayload {
  filename: string;
  data: string; // base64
  search_space_id: number;
}

export interface ListDocsPayload {
  search_space_id: number;
}

export interface CreateSpacePayload {
  name: string;
  description?: string;
}

export interface ExtractPayload {
  doc_id: number;
  search_space_id: number;
}

export interface DeleteDocumentPayload {
  document_id: number;
  search_space_id?: number;
}

export interface DeleteSpacePayload {
  search_space_id: number;
}

export interface SearchDocumentsPayload {
  title: string;
  search_space_id?: number;
}

// ===========================================================================
// Inbound (Server → Client)
// ===========================================================================

export type InboundMessage =
  | StatusMessage
  | ResultMessage
  | DocumentsMessage
  | SpacesMessage
  | SpaceCreatedMessage
  | ErrorMessage
  | StreamMessage
  | AgentStatusMessage
  | ThinkingMessage;

export interface StatusMessage {
  type: "status";
  payload: {
    state: ConnectionState;
    message: string;
    mcp?: boolean;
  };
}

export type ConnectionState =
  | "ready"
  | "uploading"
  | "indexing"
  | "querying"
  | "error";

export interface ResultMessage {
  type: "result";
  payload: {
    action: "upload" | "query" | "extract" | "delete_document" | "delete_space";
    filename?: string;
    doc_id?: number;
    document_id?: number;
    search_space_id?: number;
    query?: string;
    thread_id?: string;
    response?: string;
    dashboard?: DashboardData;
    result?: Record<string, unknown>;
  };
}

export interface DocumentsMessage {
  type: "documents";
  payload: {
    type?: string;
    search_space_id?: number;
    total?: number;
    documents?: DocumentItem[];
    query?: string;
  };
}

export interface DocumentItem {
  id: number;
  title: string;
  type?: string;
  status?: string;
  created_at?: string;
}

export interface SpacesMessage {
  type: "spaces";
  payload: {
    type?: string;
    spaces?: SpaceItem[];
  };
}

export interface SpaceItem {
  id: number;
  name: string;
  description?: string;
}

export interface SpaceCreatedMessage {
  type: "space_created";
  payload: {
    type?: string;
    id: number;
    name: string;
  };
}

export interface ErrorMessage {
  type: "error";
  payload: {
    code?: string;
    message: string;
    tool?: string;
  };
}

// Streaming text token from Hermes
export interface StreamMessage {
  type: "stream";
  payload: {
    delta: string;
    done?: boolean;
  };
}

// Agent tool execution status
export interface AgentStatusMessage {
  type: "agent_status";
  payload: {
    tool: string;
    status: "running" | "complete" | "error";
    preview?: string;
  };
}

// Agent thinking/reasoning (optional debug)
export interface ThinkingMessage {
  type: "thinking";
  payload: {
    text: string;
  };
}

// ===========================================================================
// Dashboard data types
// ===========================================================================

export type DashboardData =
  | PdfData
  | SpreadsheetData
  | DocxData
  | PptxData
  | HtmlData
  | ImageData
  | GenericData
  | SummaryData;

// --- Views ---

export type ViewData =
  | KpiView
  | TableView
  | BarView
  | LineView
  | TextView
  | PieView
  | AreaView
  | MetricDeltaView;

export interface KpiView {
  type: "kpi";
  title: string;
  value: number;
  unit?: string;
}

export interface TableView {
  type: "table";
  title: string;
  headers: string[];
  rows: string[][];
}

export interface BarView {
  type: "bar";
  title: string;
  x_axis: string;
  y_axis: string;
  data: Array<{ x: string; y: number }>;
}

export interface LineView {
  type: "line";
  title: string;
  x_axis: string;
  y_axis: string;
  data: Array<{ x: string; y: number }>;
}

export interface TextView {
  type: "text";
  title: string;
  content: string;
}

export interface PieView {
  type: "pie";
  title: string;
  data: Array<{ label: string; value: number }>;
}

export interface AreaView {
  type: "area";
  title: string;
  x_axis: string;
  y_axis: string;
  data: Array<{ x: string; y: number }>;
}

export interface MetricDeltaView {
  type: "metric_delta";
  title: string;
  value: number;
  previous: number;
  unit?: string;
  trend?: "up" | "down" | "flat";
}

// --- Document types ---

interface BaseDocData {
  views: ViewData[];
}

export interface PdfData extends BaseDocData {
  type: "pdf";
  summary: string;
  entities?: {
    persons?: string[];
    dates?: string[];
    amounts?: Array<{ concept: string; value: number }>;
  };
  tables_detected?: Array<{ title: string; headers: string[]; rows: string[][] }>;
  key_text?: string;
}

export interface SpreadsheetData extends BaseDocData {
  type: "spreadsheet";
  sheets?: Array<{ name: string; headers: string[]; rows: string[][] }>;
  calculated_metrics?: Array<{ name: string; value: number }>;
}

export interface DocxData extends BaseDocData {
  type: "docx";
  summary: string;
  sections?: Array<{ title: string; content: string }>;
  tables?: Array<{ title: string; headers: string[]; rows: string[][] }>;
}

export interface PptxData extends BaseDocData {
  type: "pptx";
  summary: string;
  slide_count?: number;
  slides?: Array<{
    number: number;
    title: string;
    content: string;
    has_table?: boolean;
    has_chart?: boolean;
  }>;
  tables?: Array<{ title: string; headers: string[]; rows: string[][] }>;
}

export interface HtmlData extends BaseDocData {
  type: "html";
  summary: string;
  page_title?: string;
  headings?: string[];
  tables?: Array<{ title: string; headers: string[]; rows: string[][] }>;
  links_count?: number;
}

export interface ImageData extends BaseDocData {
  type: "image";
  summary: string;
  ocr_text?: string;
  detected_elements?: {
    tables?: Array<{ title: string; headers: string[]; rows: string[][] }>;
    forms?: Array<{ field: string; value: string }>;
    amounts?: Array<{ concept: string; value: number }>;
  };
}

export interface GenericData extends BaseDocData {
  type: "generic";
  summary: string;
  extracted_data?: string;
}

export interface SummaryData {
  type: "summary";
  content: string;
  query: string;
}
