"use client";

import { useState, useRef } from "react";
import {
  Card,
  Text,
  Title,
  Button,
  TextInput,
  Badge,
  Divider,
} from "@tremor/react";
import { Upload, Send, FileText, Loader2, AlertCircle } from "lucide-react";
import DashboardRenderer from "../DashboardRenderer";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Message = {
  id: string;
  role: "user" | "agent";
  content: string;
  dashboard?: object | null;
  filename?: string;
  isLoading?: boolean;
};

type UploadStatus = "idle" | "uploading" | "indexing" | "ready" | "error";

// ---------------------------------------------------------------------------
// MCP API helpers
// ---------------------------------------------------------------------------

const MCP_BASE = process.env.NEXT_PUBLIC_MCP_URL ?? "http://localhost:8000";
const DEFAULT_SPACE_ID = parseInt(
  process.env.NEXT_PUBLIC_DEFAULT_SPACE_ID ?? "1"
);

async function mcpCall(tool: string, args: Record<string, unknown>) {
  const res = await fetch(`${MCP_BASE}/mcp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: { name: tool, arguments: args },
    }),
  });
  if (!res.ok) throw new Error(`MCP error: ${res.status}`);
  const data = await res.json();
  if (data.error) throw new Error(data.error.message);
  return JSON.parse(data.result.content[0].text);
}

// ---------------------------------------------------------------------------
// File upload zone
// ---------------------------------------------------------------------------

function UploadZone({
  onUpload,
  status,
}: {
  onUpload: (file: File) => void;
  status: UploadStatus;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  };

  const isActive = status === "uploading" || status === "indexing";

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => !isActive && inputRef.current?.click()}
      className={`
        border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
        ${isActive ? "border-blue-400 bg-blue-50 cursor-wait" : "border-gray-300 hover:border-blue-400 hover:bg-blue-50"}
        ${status === "ready" ? "border-green-400 bg-green-50" : ""}
        ${status === "error" ? "border-red-400 bg-red-50" : ""}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".pdf,.xlsx,.xls,.csv,.docx,.doc,.txt,.md"
        onChange={handleChange}
      />

      <div className="flex flex-col items-center gap-2">
        {isActive ? (
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        ) : status === "error" ? (
          <AlertCircle className="w-8 h-8 text-red-500" />
        ) : (
          <Upload className="w-8 h-8 text-gray-400" />
        )}

        <Text className="font-medium">
          {status === "uploading" && "Uploading..."}
          {status === "indexing" && "Indexing document..."}
          {status === "ready" && "Document ready ✓ — upload another"}
          {status === "error" && "Upload failed — try again"}
          {status === "idle" && "Drop a file here or click to upload"}
        </Text>
        <Text className="text-xs text-gray-400">
          PDF · Excel · CSV · Word · TXT
        </Text>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chat message bubble
// ---------------------------------------------------------------------------

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} gap-3`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 mt-1">
          <FileText className="w-4 h-4 text-white" />
        </div>
      )}

      <div className={`max-w-[80%] space-y-3 ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-blue-600 text-white rounded-tr-sm"
              : "bg-white border border-gray-200 text-gray-800 rounded-tl-sm"
          }`}
        >
          {message.isLoading ? (
            <div className="flex gap-1 items-center py-1">
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
            </div>
          ) : (
            message.content
          )}
        </div>

        {message.dashboard && !message.isLoading && (
          <div className="w-full">
            <DashboardRenderer
              data={message.dashboard as any}
              filename={message.filename}
            />
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "agent",
      content:
        "Hello! I'm DocuMentor. Upload a document or ask me anything about your indexed files.",
    },
  ]);
  const [input, setInput] = useState("");
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [isQuerying, setIsQuerying] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () =>
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);

  // ---- Upload handler ----
  const handleUpload = async (file: File) => {
    setUploadStatus("uploading");

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: `📎 ${file.name}`,
    };
    const agentMsg: Message = {
      id: (Date.now() + 1).toString(),
      role: "agent",
      content: "",
      isLoading: true,
      filename: file.name,
    };
    setMessages((prev) => [...prev, userMsg, agentMsg]);
    scrollToBottom();

    try {
      // Save file temporarily via a server action / API route
      const formData = new FormData();
      formData.append("file", file);
      const saveRes = await fetch("/api/upload-temp", {
        method: "POST",
        body: formData,
      });
      if (!saveRes.ok) throw new Error("Failed to save file");
      const { path: tempPath } = await saveRes.json();

      setUploadStatus("indexing");

      // Upload to SurfSense via MCP
      const uploadResult = await mcpCall("surfsense_upload", {
        file_path: tempPath,
        search_space_id: DEFAULT_SPACE_ID,
      });

      // Wait for indexing then extract
      await new Promise((r) => setTimeout(r, 3000));
      const docId = uploadResult.document_ids?.[0];
      let dashboard = null;

      if (docId) {
        const extracted = await mcpCall("surfsense_extract_tables", {
          doc_id: docId,
          search_space_id: DEFAULT_SPACE_ID,
        });
        dashboard = extracted.dashboard;
      }

      setUploadStatus("ready");
      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentMsg.id
            ? {
                ...m,
                isLoading: false,
                content: `I've processed **${file.name}**. Here's what I found:`,
                dashboard,
              }
            : m
        )
      );
    } catch (err) {
      setUploadStatus("error");
      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentMsg.id
            ? {
                ...m,
                isLoading: false,
                content: `Sorry, I couldn't process ${file.name}. Please try again.`,
              }
            : m
        )
      );
    }
    scrollToBottom();
  };

  // ---- Query handler ----
  const handleQuery = async () => {
    const query = input.trim();
    if (!query || isQuerying) return;

    setInput("");
    setIsQuerying(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: query,
    };
    const agentMsg: Message = {
      id: (Date.now() + 1).toString(),
      role: "agent",
      content: "",
      isLoading: true,
    };
    setMessages((prev) => [...prev, userMsg, agentMsg]);
    scrollToBottom();

    try {
      const result = await mcpCall("surfsense_query", {
        query,
        search_space_id: DEFAULT_SPACE_ID,
      });

      const dashboard = result.dashboard;
      const summary =
        dashboard?.summary ??
        dashboard?.content ??
        "Here are the results:";

      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentMsg.id
            ? { ...m, isLoading: false, content: summary, dashboard }
            : m
        )
      );
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentMsg.id
            ? {
                ...m,
                isLoading: false,
                content: "Something went wrong. Please try again.",
              }
            : m
        )
      );
    }

    setIsQuerying(false);
    scrollToBottom();
  };

  return (
    <div className="min-h-screen flex flex-col max-w-4xl mx-auto px-4 py-6 gap-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Title>DocuMentor</Title>
          <Text className="text-gray-500 text-sm">
            Document intelligence · Powered by RelayGPU
          </Text>
        </div>
        <Badge color="green">Online</Badge>
      </div>

      <Divider />

      {/* Upload zone */}
      <UploadZone onUpload={handleUpload} status={uploadStatus} />

      {/* Chat */}
      <Card className="flex-1 flex flex-col gap-4 p-4 min-h-[400px]">
        <div className="flex-1 space-y-4 overflow-y-auto pr-1">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>

        <Divider className="my-0" />

        {/* Input */}
        <div className="flex gap-2">
          <TextInput
            placeholder="Ask about your documents..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleQuery()}
            disabled={isQuerying}
            className="flex-1"
          />
          <Button
            onClick={handleQuery}
            disabled={!input.trim() || isQuerying}
            icon={isQuerying ? Loader2 : Send}
          >
            {isQuerying ? "Thinking..." : "Ask"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
