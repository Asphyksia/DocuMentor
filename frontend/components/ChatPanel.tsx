"use client";

import { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Loader2, Bot, User, Plus } from "lucide-react";
import clsx from "clsx";
import DashboardRenderer from "../DashboardRenderer";
import type { ChatMessage } from "../hooks/useChatState";

export type { ChatMessage };

type Props = {
  messages: ChatMessage[];
  input: string;
  onInputChange: (val: string) => void;
  onSend: () => void;
  onClearHistory?: () => void;
  isQuerying: boolean;
  agentStatus?: string | null;
};

// ---------------------------------------------------------------------------
// Streaming cursor
// ---------------------------------------------------------------------------

function StreamingCursor() {
  return (
    <motion.span
      className="inline-block w-0.5 h-4 bg-blue-400 ml-0.5 align-text-bottom"
      animate={{ opacity: [1, 0] }}
      transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
    />
  );
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={clsx("flex gap-3", isUser ? "justify-end" : "justify-start")}
    >
      {/* Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0 mt-1 shadow-lg shadow-blue-500/20">
          <Bot className="w-4 h-4 text-white" />
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
              ? "bg-blue-600 text-white rounded-tr-md"
              : "bg-gray-800 text-gray-100 rounded-tl-md border border-gray-700/50"
          )}
        >
          {msg.isLoading ? (
            <div className="flex gap-1.5 items-center py-1 px-2">
              <motion.span
                className="w-2 h-2 bg-blue-400 rounded-full"
                animate={{ scale: [1, 1.4, 1] }}
                transition={{ repeat: Infinity, duration: 0.8, delay: 0 }}
              />
              <motion.span
                className="w-2 h-2 bg-blue-400 rounded-full"
                animate={{ scale: [1, 1.4, 1] }}
                transition={{ repeat: Infinity, duration: 0.8, delay: 0.2 }}
              />
              <motion.span
                className="w-2 h-2 bg-blue-400 rounded-full"
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

        {/* Inline dashboard */}
        {msg.dashboard && !msg.isLoading && !msg.isStreaming && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="w-full"
          >
            <DashboardRenderer
              data={msg.dashboard}
              filename={msg.filename}
            />
          </motion.div>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0 mt-1">
          <User className="w-4 h-4 text-gray-300" />
        </div>
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Chat panel
// ---------------------------------------------------------------------------

export default function ChatPanel({
  messages,
  input,
  onInputChange,
  onSend,
  onClearHistory,
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

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <AnimatePresence mode="popLayout">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} />
          ))}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      {/* Agent status indicator */}
      {agentStatus && (
        <div className="px-4 pb-1">
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-2 text-xs text-gray-400"
          >
            <Loader2 className="w-3 h-3 animate-spin text-blue-400" />
            <span>{agentStatus}</span>
          </motion.div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-gray-800">
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
                  ? "bg-gray-800 text-gray-600 cursor-not-allowed"
                  : "bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700"
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
                "w-full resize-none rounded-xl bg-gray-800 border border-gray-700 px-4 py-3 pr-12",
                "text-sm text-gray-100 placeholder:text-gray-500",
                "focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50",
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
                ? "bg-blue-600 hover:bg-blue-500 shadow-blue-500/25 text-white"
                : "bg-gray-800 text-gray-500 cursor-not-allowed shadow-none"
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
