"use client";

import { useCallback, useState } from "react";
import type { DashboardData } from "../types/bridge";

export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: number;
  isLoading?: boolean;
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
    setMessages((prev) => [
      ...prev,
      { id, role: "agent", content: "", isLoading: true, filename, timestamp: Date.now() },
    ]);
    return id;
  }, []);

  const resolveAgent = useCallback(
    (content: string, dashboard?: DashboardData, filename?: string) => {
      setMessages((prev) =>
        prev.map((m) =>
          m.isLoading && m.role === "agent"
            ? { ...m, isLoading: false, content, dashboard, filename: filename ?? m.filename }
            : m
        )
      );
    },
    []
  );

  const resolveAgentError = useCallback((errorMessage: string) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.isLoading && m.role === "agent"
          ? { ...m, isLoading: false, content: `Something went wrong: ${errorMessage}` }
          : m
      )
    );
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
    resolveAgent,
    resolveAgentError,
    clearInput,
  };
}
