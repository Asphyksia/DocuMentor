"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import AppHeader, { type TabId } from "../components/AppHeader";
import DocSidebar, { type DocItem } from "../components/DocSidebar";
import ChatPanel, { type ChatMessage } from "../components/ChatPanel";
import UploadModal from "../components/UploadModal";
import SettingsPanel from "../components/SettingsPanel";
import DashboardRenderer from "../DashboardRenderer";
import { useBridge, type InboundMessage, type SystemStatus } from "../hooks/useBridge";

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULT_SPACE_ID = parseInt(
  process.env.NEXT_PUBLIC_DEFAULT_SPACE_ID ?? "1"
);

const WELCOME: ChatMessage = {
  id: "welcome",
  role: "agent",
  content:
    "Hello! I'm DocuMentor, your university document assistant. Upload a document or ask me anything about your indexed files.",
  timestamp: Date.now(),
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Home() {
  // Bridge
  const {
    bridgeState,
    systemStatus,
    subscribe,
    uploadFile,
    query,
    listDocs,
    listSpaces,
    createSpace,
  } = useBridge();

  // UI state
  const [activeTab, setActiveTab] = useState<TabId>("chat");
  const [showUpload, setShowUpload] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<SystemStatus["state"]>("ready");
  const [uploadMessage, setUploadMessage] = useState("");

  // Data state
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [isQuerying, setIsQuerying] = useState(false);
  const [documents, setDocuments] = useState<DocItem[]>([]);
  const [activeDocId, setActiveDocId] = useState<number | null>(null);
  const [spaces, setSpaces] = useState<{ id: number; name: string; description?: string }[]>([]);
  const [activeSpaceId, setActiveSpaceId] = useState(DEFAULT_SPACE_ID);
  const [lastDashboard, setLastDashboard] = useState<any>(null);
  const [docsLoading, setDocsLoading] = useState(true);

  // ---- Bridge message handler ----
  useEffect(() => {
    const unsub = subscribe((msg: InboundMessage) => {
      switch (msg.type) {
        case "status":
          setUploadStatus(msg.payload.state);
          setUploadMessage(msg.payload.message ?? "");
          if (msg.payload.state === "ready") {
            setIsQuerying(false);
          }
          break;

        case "result": {
          const { action, dashboard, filename, query: q, doc_id } = msg.payload;

          if (action === "upload" && dashboard) {
            setLastDashboard(dashboard);
            setMessages((prev) =>
              prev.map((m) =>
                m.isLoading && m.role === "agent"
                  ? {
                      ...m,
                      isLoading: false,
                      content: `I've processed **${filename}**. Here's what I found:`,
                      dashboard,
                      filename,
                    }
                  : m
              )
            );
            if (doc_id) setActiveDocId(doc_id);
          }

          if (action === "query" && dashboard) {
            setLastDashboard(dashboard);
            const summary = dashboard?.summary ?? dashboard?.content ?? "Here are the results:";
            setMessages((prev) =>
              prev.map((m) =>
                m.isLoading && m.role === "agent"
                  ? { ...m, isLoading: false, content: summary, dashboard }
                  : m
              )
            );
          }

          if (action === "extract" && dashboard) {
            setLastDashboard(dashboard);
          }
          break;
        }

        case "documents":
          setDocuments(msg.payload.documents ?? []);
          setDocsLoading(false);
          break;

        case "spaces":
          setSpaces(msg.payload.spaces ?? []);
          break;

        case "space_created":
          listSpaces();
          break;

        case "error":
          setMessages((prev) =>
            prev.map((m) =>
              m.isLoading && m.role === "agent"
                ? {
                    ...m,
                    isLoading: false,
                    content: `Something went wrong: ${msg.payload.message}`,
                  }
                : m
            )
          );
          setIsQuerying(false);
          break;
      }
    });
    return unsub;
  }, [subscribe, listSpaces]);

  // ---- Load initial data when connected ----
  useEffect(() => {
    if (bridgeState === "connected") {
      listDocs(activeSpaceId);
      listSpaces();
    }
  }, [bridgeState, activeSpaceId, listDocs, listSpaces]);

  // ---- Upload handler ----
  const handleUpload = useCallback(
    (file: File) => {
      const userMsg: ChatMessage = {
        id: Date.now().toString(),
        role: "user",
        content: `📎 ${file.name}`,
        timestamp: Date.now(),
      };
      const agentMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: "",
        isLoading: true,
        filename: file.name,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMsg, agentMsg]);
      setActiveTab("chat");
      uploadFile(file, activeSpaceId);
    },
    [uploadFile, activeSpaceId]
  );

  // ---- Query handler ----
  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || isQuerying) return;

    setInput("");
    setIsQuerying(true);

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    const agentMsg: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: "agent",
      content: "",
      isLoading: true,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg, agentMsg]);
    query(text, activeSpaceId);
  }, [input, isQuerying, query, activeSpaceId]);

  // ---- Doc selection ----
  const handleSelectDoc = useCallback((doc: DocItem) => {
    setActiveDocId(doc.id);
    setActiveTab("dashboard");
  }, []);

  // ---- Tab content ----
  const renderTab = () => {
    switch (activeTab) {
      case "chat":
        return (
          <ChatPanel
            messages={messages}
            input={input}
            onInputChange={setInput}
            onSend={handleSend}
            isQuerying={isQuerying}
          />
        );
      case "dashboard":
        return (
          <div className="p-6 overflow-y-auto h-full">
            {lastDashboard ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <DashboardRenderer data={lastDashboard} />
              </motion.div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                Upload or query a document to see the dashboard here.
              </div>
            )}
          </div>
        );
      case "settings":
        return (
          <SettingsPanel
            spaces={spaces}
            activeSpaceId={activeSpaceId}
            onChangeSpace={setActiveSpaceId}
            onCreateSpace={(name, desc) => createSpace(name, desc)}
          />
        );
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100 overflow-hidden">
      {/* Header */}
      <AppHeader
        activeTab={activeTab}
        onTabChange={setActiveTab}
        bridgeState={bridgeState}
        systemStatus={systemStatus}
      />

      {/* Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <DocSidebar
          documents={documents}
          activeDocId={activeDocId}
          onSelectDoc={handleSelectDoc}
          onUploadClick={() => setShowUpload(true)}
          isLoading={docsLoading}
        />

        {/* Main content */}
        <main className="flex-1 overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              {renderTab()}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Upload modal */}
      <UploadModal
        isOpen={showUpload}
        onClose={() => {
          setShowUpload(false);
          setUploadStatus("ready");
          setUploadMessage("");
        }}
        onUpload={(file) => {
          handleUpload(file);
          // Keep modal open to show progress
        }}
        status={uploadStatus === "ready" ? "idle" : uploadStatus as any}
        statusMessage={uploadMessage}
      />
    </div>
  );
}
