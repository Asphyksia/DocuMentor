"use client";

import { useCallback, useRef, useState } from "react";
import type { DashboardData } from "../types/bridge";

export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: number;
  isLoading?: boolean;
  isStreaming?: boolean;
  dashboard?: DashboardData;
  filename?: string;
}

const WELCOME: ChatMessage = {
  id: "welcome",
  role: "agent",
  content:
    "Hello! I'm DocuMentor, your university document assistant. Upload a document or ask me anything about your indexed files.",
  timestamp: Date.now(),
};

export function useChatState() {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [isQuerying, setIsQuerying] = useState(false);
  const streamingContentRef = useRef("");

  const addUserMessage = useCallback((content: string): string => {
    const id = Date.now().toString();
    setMessages((prev) => [
      ...prev,
      { id, role: "user", content, timestamp: Date.now() },
    ]);
    return id;
  }, []);

  const addLoadingAgent = useCallback((filename?: string): string => {
    const id = (Date.now() + 1).toString();
    streamingContentRef.current = "";
    setMessages((prev) => [
      ...prev,
      { id, role: "agent", content: "", isLoading: true, filename, timestamp: Date.now() },
    ]);
    return id;
  }, []);

  const appendStreamDelta = useCallback((delta: string) => {
    streamingContentRef.current += delta;
    const accumulated = streamingContentRef.current;
    setMessages((prev) => {
      const lastAgentIdx = findLastAgentIndex(prev);
      if (lastAgentIdx === -1) return prev;
      const updated = [...prev];
      updated[lastAgentIdx] = {
        ...updated[lastAgentIdx],
        isLoading: false,
        isStreaming: true,
        content: accumulated,
      };
      return updated;
    });
  }, []);

  const finalizeStream = useCallback(() => {
    streamingContentRef.current = "";
    setMessages((prev) => {
      const lastAgentIdx = findLastAgentIndex(prev);
      if (lastAgentIdx === -1) return prev;
      const updated = [...prev];
      updated[lastAgentIdx] = {
        ...updated[lastAgentIdx],
        isStreaming: false,
        isLoading: false,
      };
      return updated;
    });
    setIsQuerying(false);
  }, []);

  const resolveAgent = useCallback(
    (content: string, dashboard?: DashboardData, filename?: string) => {
      streamingContentRef.current = "";
      setMessages((prev) => {
        // First try to find a loading/streaming message to resolve
        const pendingIdx = prev.findIndex(
          (m) => m.role === "agent" && (m.isLoading || m.isStreaming)
        );
        if (pendingIdx !== -1) {
          const updated = [...prev];
          updated[pendingIdx] = {
            ...updated[pendingIdx],
            isLoading: false,
            isStreaming: false,
            content,
            dashboard,
            filename: filename ?? updated[pendingIdx].filename,
          };
          return updated;
        }
        // No pending message — attach dashboard to the last agent message
        // (happens when streaming already finalized the text)
        if (dashboard) {
          for (let i = prev.length - 1; i >= 0; i--) {
            if (prev[i].role === "agent" && !prev[i].dashboard) {
              const updated = [...prev];
              updated[i] = { ...updated[i], dashboard };
              return updated;
            }
          }
        }
        return prev;
      });
    },
    []
  );

  const resolveAgentError = useCallback((errorMessage: string) => {
    streamingContentRef.current = "";
    setMessages((prev) =>
      prev.map((m) =>
        (m.isLoading || m.isStreaming) && m.role === "agent"
          ? { ...m, isLoading: false, isStreaming: false, content: `Something went wrong: ${errorMessage}` }
          : m
      )
    );
    setIsQuerying(false);
  }, []);

  const clearHistory = useCallback(() => {
    streamingContentRef.current = "";
    setMessages([WELCOME]);
    setInput("");
    setIsQuerying(false);
  }, []);

  const clearInput = useCallback(() => setInput(""), []);

  return {
    messages,
    input,
    setInput,
    isQuerying,
    setIsQuerying,
    addUserMessage,
    addLoadingAgent,
    appendStreamDelta,
    finalizeStream,
    resolveAgent,
    resolveAgentError,
    clearHistory,
    clearInput,
  };
}

// Helper: find the index of the last agent message (loading or streaming)
function findLastAgentIndex(messages: ChatMessage[]): number {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === "agent" && (messages[i].isLoading || messages[i].isStreaming)) {
      return i;
    }
  }
  return -1;
}
