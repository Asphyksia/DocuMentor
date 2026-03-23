"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Types matching bridge.py protocol
// ---------------------------------------------------------------------------

export type BridgeState = "connecting" | "connected" | "disconnected";

export type SystemStatus = {
  state: "uploading" | "indexing" | "querying" | "ready" | "error";
  message: string;
};

export type InboundMessage = {
  type: "result" | "status" | "documents" | "spaces" | "space_created" | "error";
  payload: any;
};

export type OutboundMessage = {
  type: "upload" | "query" | "list_docs" | "list_spaces" | "create_space" | "extract" | "status";
  payload?: any;
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

const BRIDGE_URL = process.env.NEXT_PUBLIC_BRIDGE_URL ?? "ws://localhost:8001/ws";
const RECONNECT_DELAY = 3000;

export function useBridge() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout>();
  const [bridgeState, setBridgeState] = useState<BridgeState>("disconnected");
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({ state: "ready", message: "" });
  const listenersRef = useRef<Set<(msg: InboundMessage) => void>>(new Set());

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    setBridgeState("connecting");

    const ws = new WebSocket(BRIDGE_URL);

    ws.onopen = () => {
      setBridgeState("connected");
      // Request initial status
      ws.send(JSON.stringify({ type: "status" }));
    };

    ws.onmessage = (event) => {
      try {
        const msg: InboundMessage = JSON.parse(event.data);

        // Update system status automatically
        if (msg.type === "status") {
          setSystemStatus(msg.payload);
        }

        // Notify all listeners
        listenersRef.current.forEach((fn) => fn(msg));
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setBridgeState("disconnected");
      wsRef.current = null;
      // Auto-reconnect
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  // Send a message to the bridge
  const send = useCallback((msg: OutboundMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  // Subscribe to inbound messages
  const subscribe = useCallback((fn: (msg: InboundMessage) => void) => {
    listenersRef.current.add(fn);
    return () => { listenersRef.current.delete(fn); };
  }, []);

  // Convenience methods
  const uploadFile = useCallback(
    (file: File, searchSpaceId: number = 1) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(",")[1];
        send({
          type: "upload",
          payload: { filename: file.name, data: base64, search_space_id: searchSpaceId },
        });
      };
      reader.readAsDataURL(file);
    },
    [send]
  );

  const query = useCallback(
    (text: string, searchSpaceId: number = 1, threadId?: string) => {
      send({
        type: "query",
        payload: { query: text, search_space_id: searchSpaceId, thread_id: threadId },
      });
    },
    [send]
  );

  const listDocs = useCallback(
    (searchSpaceId: number = 1) => {
      send({ type: "list_docs", payload: { search_space_id: searchSpaceId } });
    },
    [send]
  );

  const listSpaces = useCallback(() => {
    send({ type: "list_spaces" });
  }, [send]);

  const createSpace = useCallback(
    (name: string, description?: string) => {
      send({ type: "create_space", payload: { name, description } });
    },
    [send]
  );

  return {
    bridgeState,
    systemStatus,
    send,
    subscribe,
    uploadFile,
    query,
    listDocs,
    listSpaces,
    createSpace,
  };
}
