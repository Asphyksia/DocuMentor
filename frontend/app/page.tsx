"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import clsx from "clsx";
import AppHeader, { type TabId } from "../components/AppHeader";
import DocSidebar from "../components/DocSidebar";
import ChatPanel from "../components/ChatPanel";
import UploadModal from "../components/UploadModal";
import SettingsPanel from "../components/SettingsPanel";
import DashboardRenderer from "../DashboardRenderer";
import LoginForm from "../components/LoginForm";
import ErrorBoundary from "../components/ErrorBoundary";
import { useBridge } from "../hooks/useBridge";
import { useAuth } from "../hooks/useAuth";
import { useChatState } from "../hooks/useChatState";
import { useDashboardState } from "../hooks/useDashboardState";
import { useDocumentsState, type DocItem } from "../hooks/useDocumentsState";
import { useUploadState } from "../hooks/useUploadState";
import type { InboundMessage, DashboardData } from "../types/bridge";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const DEFAULT_SPACE_ID = parseInt(
  process.env.NEXT_PUBLIC_DEFAULT_SPACE_ID ?? "1"
);

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Home() {
  // --- Auth ---
  const auth = useAuth();

  // --- Hooks ---
  const bridge = useBridge();
  const chat = useChatState();
  const dash = useDashboardState();
  const docs = useDocumentsState(DEFAULT_SPACE_ID);
  const upload = useUploadState();

  const [activeTab, setActiveTab] = useState<TabId>("chat");
  const [agentStatus, setAgentStatus] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // --- Auth gate ---
  if (auth.state === "checking") {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-muted-foreground text-sm"
        >
          Loading...
        </motion.div>
      </div>
    );
  }

  if (auth.state === "unauthenticated" && auth.authEnabled) {
    return <LoginForm onLogin={auth.login} error={auth.error} />;
  }

  // --- Bridge message dispatcher ---
  useEffect(() => {
    const unsub = bridge.subscribe((msg: InboundMessage) => {
      switch (msg.type) {
        case "status":
          upload.updateFromBridge(msg.payload.state, msg.payload.message ?? "");
          if (msg.payload.state === "ready") {
            chat.setIsQuerying(false);
          }
          break;

        case "stream": {
          const { delta, done } = msg.payload;
          if (delta) {
            chat.appendStreamDelta(delta);
          }
          if (done) {
            // Finalize and try to parse dashboard from accumulated text
            chat.finalizeStream();
            setAgentStatus(null);
          }
          break;
        }

        case "agent_status": {
          const { tool, status, preview } = msg.payload;
          if (status === "running") {
            const label = preview ? `${tool}: ${preview}` : tool;
            setAgentStatus(`Using ${label}…`);
          } else if (status === "complete") {
            setAgentStatus(null);
          } else if (status === "error") {
            setAgentStatus(null);
          }
          break;
        }

        case "thinking":
          // Phase 1: ignore thinking messages (optional debug)
          break;

        case "result": {
          const p = msg.payload;

          if (p.action === "upload" && p.dashboard) {
            const dashboard = p.dashboard as DashboardData;
            dash.updateDashboard(dashboard);
            chat.resolveAgent(
              `I've processed **${p.filename ?? "your file"}**. Here's what I found:`,
              dashboard,
              p.filename
            );
            if (p.doc_id) docs.setActiveDocId(p.doc_id);
            toast.success(`${p.filename ?? "File"} uploaded successfully`);
          }

          if (p.action === "query" && p.dashboard) {
            const dashboard = p.dashboard as DashboardData;
            dash.updateDashboard(dashboard);
            const fallbackText =
              p.response ??
              ("summary" in dashboard ? (dashboard as { summary?: string }).summary : undefined) ??
              ("content" in dashboard ? (dashboard as { content?: string }).content : undefined) ??
              "Here are the results:";
            // For summary-type responses, only show text in chat (no inline dashboard)
            // to avoid duplicating the same content as text + summary card.
            // Rich dashboards (tables, metrics) still show inline.
            const isSummaryOnly =
              "type" in dashboard && (dashboard as { type: string }).type === "summary";
            chat.resolveAgent(fallbackText, isSummaryOnly ? undefined : dashboard);
          }

          if (p.action === "extract" && p.dashboard) {
            dash.updateDashboard(p.dashboard as DashboardData);
          }

          if (p.action === "delete_document") {
            toast.success("Document deleted");
          }

          if (p.action === "delete_space") {
            toast.success("Space deleted");
          }
          break;
        }

        case "documents":
          docs.updateDocuments(msg.payload.documents ?? []);
          break;

        case "spaces":
          docs.updateSpaces(msg.payload.spaces ?? []);
          break;

        case "space_created":
          bridge.listSpaces();
          toast.success("Space created");
          break;

        case "error":
          chat.resolveAgentError(msg.payload.message);
          setAgentStatus(null);
          toast.error(msg.payload.message ?? "Something went wrong");
          break;
      }
    });
    return unsub;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Load initial data ---
  useEffect(() => {
    if (bridge.bridgeState === "connected") {
      bridge.listDocs(docs.activeSpaceId);
      bridge.listSpaces();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bridge.bridgeState, docs.activeSpaceId]);

  // --- Keyboard shortcuts ---
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const mod = e.ctrlKey || e.metaKey;

      // Ctrl+U — open upload modal
      if (mod && e.key === "u") {
        e.preventDefault();
        upload.openModal();
      }

      // Ctrl+N — new chat
      if (mod && e.key === "n" && !e.shiftKey) {
        e.preventDefault();
        chat.clearHistory();
        setAgentStatus(null);
        bridge.clearHistory();
      }

      // Escape — close upload modal
      if (e.key === "Escape" && upload.showModal) {
        upload.closeModal();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [chat, bridge, upload, setAgentStatus]);

  // --- Upload handler ---
  const handleUpload = useCallback(
    (file: File) => {
      chat.addUserMessage(`📎 ${file.name}`);
      chat.addLoadingAgent(file.name);
      setActiveTab("chat");
      bridge.uploadFile(file, docs.activeSpaceId);
    },
    [bridge, chat, docs.activeSpaceId]
  );

  // --- Query handler ---
  const handleSend = useCallback(() => {
    const text = chat.input.trim();
    if (!text || chat.isQuerying) return;

    chat.clearInput();
    chat.setIsQuerying(true);
    chat.addUserMessage(text);
    chat.addLoadingAgent();
    bridge.query(text, docs.activeSpaceId);
  }, [bridge, chat, docs.activeSpaceId]);

  // --- Clear history handler ---
  const handleClearHistory = useCallback(() => {
    chat.clearHistory();
    setAgentStatus(null);
    bridge.clearHistory();
  }, [chat, bridge]);

  // --- Retry handler ---
  const handleRetry = useCallback(() => {
    const query = chat.popErrorForRetry();
    if (!query) return;

    chat.setIsQuerying(true);
    chat.addUserMessage(query);
    chat.addLoadingAgent();
    bridge.query(query, docs.activeSpaceId);
  }, [chat, bridge, docs.activeSpaceId]);

  // --- Doc selection ---
  const handleSelectDoc = useCallback(
    (doc: DocItem) => {
      docs.setActiveDocId(doc.id);
      setActiveTab("dashboard");
    },
    [docs]
  );

  // --- Doc deletion ---
  const handleDeleteDoc = useCallback(
    (docId: number) => {
      bridge.deleteDocument(docId, docs.activeSpaceId);
      if (docs.activeDocId === docId) {
        docs.setActiveDocId(null);
      }
    },
    [bridge, docs]
  );

  // --- Tab content ---
  const renderTab = () => {
    switch (activeTab) {
      case "chat":
        return (
          <ChatPanel
            messages={chat.messages}
            input={chat.input}
            onInputChange={chat.setInput}
            onSend={handleSend}
            onClearHistory={handleClearHistory}
            onRetry={handleRetry}
            isQuerying={chat.isQuerying}
            agentStatus={agentStatus}
          />
        );
      case "dashboard":
        return (
          <div className="p-6 overflow-y-auto h-full">
            {dash.dashboard ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <DashboardRenderer data={dash.dashboard} />
              </motion.div>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                Upload or query a document to see the dashboard here.
              </div>
            )}
          </div>
        );
      case "settings":
        return (
          <SettingsPanel
            spaces={docs.spaces}
            activeSpaceId={docs.activeSpaceId}
            onChangeSpace={docs.setActiveSpaceId}
            onCreateSpace={(name, desc) => bridge.createSpace(name, desc)}
            onLogout={auth.authEnabled ? auth.logout : undefined}
          />
        );
    }
  };

  return (
    <ErrorBoundary>
      <div className="h-screen flex flex-col bg-background text-foreground overflow-hidden">
        <AppHeader
          activeTab={activeTab}
          onTabChange={setActiveTab}
          bridgeState={bridge.bridgeState}
          systemStatus={bridge.systemStatus}
          onToggleSidebar={() => setSidebarOpen((v) => !v)}
        />

        <div className="flex-1 flex overflow-hidden relative">
          {/* Mobile sidebar overlay */}
          {sidebarOpen && (
            <div
              className="fixed inset-0 bg-black/50 z-30 lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
          )}

          {/* Sidebar: hidden on mobile by default, always visible on desktop */}
          <div
            className={clsx(
              "absolute lg:relative z-40 lg:z-auto h-full transition-transform duration-200 lg:translate-x-0",
              sidebarOpen ? "translate-x-0" : "-translate-x-full"
            )}
          >
            <ErrorBoundary fallbackMessage="Error loading document sidebar">
              <DocSidebar
                documents={docs.documents}
                activeDocId={docs.activeDocId}
                onSelectDoc={(doc) => {
                  handleSelectDoc(doc);
                  setSidebarOpen(false);
                }}
                onDeleteDoc={handleDeleteDoc}
                onUploadClick={() => {
                  upload.openModal();
                  setSidebarOpen(false);
                }}
                isLoading={docs.docsLoading}
              />
            </ErrorBoundary>
          </div>

          <main className="flex-1 overflow-hidden">
            <ErrorBoundary fallbackMessage="Error rendering content">
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
            </ErrorBoundary>
          </main>
        </div>

        <UploadModal
          isOpen={upload.showModal}
          onClose={upload.closeModal}
          onUpload={handleUpload}
          status={upload.status}
          statusMessage={upload.message}
        />
      </div>
    </ErrorBoundary>
  );
}
