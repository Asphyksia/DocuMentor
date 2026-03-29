"use client";

import { useRef, useEffect, forwardRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Loader2,
  Bot,
  User,
  Plus,
  RefreshCw,
  AlertCircle,
  MessageSquare,
  Upload,
} from "lucide-react";
import clsx from "clsx";
import { Button } from "@/components/ui/button";
import DashboardRenderer from "../DashboardRenderer";
import type { ChatMessage } from "../hooks/useChatState";

export type { ChatMessage };

type Props = {
  messages: ChatMessage[];
  input: string;
  onInputChange: (val: string) => void;
  onSend: () => void;
  onClearHistory?: () => void;
  onRetry?: () => void;
  isQuerying: boolean;
  agentStatus?: string | null;
};

// ---------------------------------------------------------------------------
// Streaming cursor
// ---------------------------------------------------------------------------

function StreamingCursor() {
  return (
    <motion.span
      className="inline-block w-0.5 h-4 bg-primary ml-0.5 align-text-bottom"
      animate={{ opacity: [1, 0] }}
      transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
    />
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function ChatEmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="flex flex-col items-center justify-center h-full text-center px-6"
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 mb-4">
        <MessageSquare className="w-7 h-7 text-primary" />
      </div>
      <h3 className="text-lg font-semibold mb-1">DocuMentor</h3>
      <p className="text-sm text-muted-foreground max-w-xs mb-6">
        Upload a document and ask questions about it, or query your existing knowledge base.
      </p>
      <div className="flex flex-wrap gap-2 justify-center max-w-sm">
        {[
          "Summarize the latest report",
          "What are the key metrics?",
          "Compare Q1 and Q2 results",
        ].map((suggestion) => (
          <span
            key={suggestion}
            className="text-xs px-3 py-1.5 rounded-full bg-muted text-muted-foreground"
          >
            {suggestion}
          </span>
        ))}
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

const MessageBubble = forwardRef<
  HTMLDivElement,
  { msg: ChatMessage; onRetry?: () => void }
>(function MessageBubble({ msg, onRetry }, ref) {
  const isUser = msg.role === "user";

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={clsx("flex gap-3", isUser ? "justify-end" : "justify-start")}
    >
      {/* Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center flex-shrink-0 mt-1 shadow-lg shadow-primary/20">
          {msg.isError ? (
            <AlertCircle className="w-4 h-4 text-destructive-foreground" />
          ) : (
            <Bot className="w-4 h-4 text-primary-foreground" />
          )}
        </div>
      )}

      <div
        className={clsx(
          "max-w-[80%] flex flex-col gap-3",
          isUser ? "items-end" : "items-start"
        )}
      >
        {/* Text bubble */}
        <motion.div
          layout
          className={clsx(
            "rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
            isUser
              ? "bg-primary text-primary-foreground rounded-tr-md"
              : msg.isError
                ? "bg-destructive/10 text-destructive border border-destructive/20 rounded-tl-md"
                : "bg-card text-card-foreground rounded-tl-md border border-border"
          )}
        >
          {msg.isLoading ? (
            <div className="flex gap-1.5 items-center py-1 px-2">
              <motion.span
                className="w-2 h-2 bg-primary rounded-full"
                animate={{ scale: [1, 1.4, 1] }}
                transition={{ repeat: Infinity, duration: 0.8, delay: 0 }}
              />
              <motion.span
                className="w-2 h-2 bg-primary rounded-full"
                animate={{ scale: [1, 1.4, 1] }}
                transition={{ repeat: Infinity, duration: 0.8, delay: 0.2 }}
              />
              <motion.span
                className="w-2 h-2 bg-primary rounded-full"
                animate={{ scale: [1, 1.4, 1] }}
                transition={{ repeat: Infinity, duration: 0.8, delay: 0.4 }}
              />
            </div>
          ) : (
            <span className="whitespace-pre-wrap">
              {msg.content}
              {msg.isStreaming && <StreamingCursor />}
            </span>
          )}
        </motion.div>

        {/* Retry button on error */}
        {msg.isError && onRetry && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <Button
              variant="outline"
              size="sm"
              onClick={onRetry}
              className="gap-1.5 text-xs"
            >
              <RefreshCw className="w-3 h-3" />
              Retry
            </Button>
          </motion.div>
        )}

        {/* Inline dashboard */}
        {msg.dashboard && !msg.isLoading && !msg.isStreaming && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="w-full"
          >
            <DashboardRenderer data={msg.dashboard} filename={msg.filename} />
          </motion.div>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0 mt-1">
          <User className="w-4 h-4 text-muted-foreground" />
        </div>
      )}
    </motion.div>
  );
});

// ---------------------------------------------------------------------------
// Chat panel
// ---------------------------------------------------------------------------

export default function ChatPanel({
  messages,
  input,
  onInputChange,
  onSend,
  onClearHistory,
  onRetry,
  isQuerying,
  agentStatus,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  // Only show the welcome message = effectively empty
  const isEmpty = messages.length <= 1 && messages[0]?.id === "welcome";

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {isEmpty ? (
          <ChatEmptyState />
        ) : (
          <AnimatePresence mode="popLayout">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} onRetry={onRetry} />
            ))}
          </AnimatePresence>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Agent status indicator */}
      {agentStatus && (
        <div className="px-4 pb-1">
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-2 text-xs text-muted-foreground"
          >
            <Loader2 className="w-3 h-3 animate-spin text-primary" />
            <span>{agentStatus}</span>
          </motion.div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-border">
        <div className="flex gap-3 items-end">
          {/* New chat button */}
          {onClearHistory && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onClearHistory}
              disabled={isQuerying}
              title="New chat"
              className={clsx(
                "p-3 rounded-xl transition-all duration-200",
                isQuerying
                  ? "bg-muted text-muted-foreground/40 cursor-not-allowed"
                  : "bg-muted text-muted-foreground hover:text-foreground hover:bg-accent"
              )}
            >
              <Plus className="w-5 h-5" />
            </motion.button>
          )}

          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => onInputChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your documents..."
              disabled={isQuerying}
              rows={1}
              className={clsx(
                "w-full resize-none rounded-xl bg-muted border border-border px-4 py-3 pr-12",
                "text-sm text-foreground placeholder:text-muted-foreground",
                "focus:outline-none focus:ring-2 focus:ring-ring/50 focus:border-ring/50",
                "transition-all duration-200",
                "disabled:opacity-50"
              )}
              style={{ minHeight: "44px", maxHeight: "120px" }}
              onInput={(e) => {
                const el = e.target as HTMLTextAreaElement;
                el.style.height = "auto";
                el.style.height = Math.min(el.scrollHeight, 120) + "px";
              }}
            />
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onSend}
            disabled={!input.trim() || isQuerying}
            className={clsx(
              "p-3 rounded-xl transition-all duration-200 shadow-lg",
              input.trim() && !isQuerying
                ? "bg-primary hover:bg-primary/90 shadow-primary/25 text-primary-foreground"
                : "bg-muted text-muted-foreground/40 cursor-not-allowed shadow-none"
            )}
          >
            {isQuerying ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </motion.button>
        </div>
      </div>
    </div>
  );
}
