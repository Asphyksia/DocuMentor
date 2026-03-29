"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  OutboundMessage,
  InboundMessage,
  ConnectionState,
} from "../types/bridge";
import { getAuthenticatedWsUrl } from "./useAuth";

// ---------------------------------------------------------------------------
// Public types (re-exported for convenience)
// ---------------------------------------------------------------------------

export type BridgeState = "connecting" | "connected" | "disconnected";

export type SystemStatus = {
  state: ConnectionState;
  message: string;
};

export type { InboundMessage, OutboundMessage };

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const BRIDGE_URL =
  process.env.NEXT_PUBLIC_BRIDGE_URL ?? "ws://localhost:8001/ws";
const RECONNECT_DELAY = 3000;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useBridge() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout>();
  const mountedRef = useRef(false);
  const [bridgeState, setBridgeState] = useState<BridgeState>("disconnected");
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    state: "ready",
    message: "",
  });
  const [lastError, setLastError] = useState<string | null>(null);
  const listenersRef = useRef<Set<(msg: InboundMessage) => void>>(new Set());

  useEffect(() => {
    mountedRef.current = true;

    function openConnection() {
      if (!mountedRef.current) return;
      if (
        wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING
      )
        return;

      setBridgeState("connecting");
      setLastError(null);

      const ws = new WebSocket(getAuthenticatedWsUrl(BRIDGE_URL));

      ws.onopen = () => {
        if (!mountedRef.current || wsRef.current !== ws) {
          ws.close();
          return;
        }
        setBridgeState("connected");
        setLastError(null);
        ws.send(JSON.stringify({ type: "status" }));
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const msg = JSON.parse(event.data) as InboundMessage;

          if (msg.type === "status") {
            setSystemStatus({
              state: msg.payload.state,
              message: msg.payload.message,
            });
          }

          if (msg.type === "error") {
            const errMsg = msg.payload.message ?? "Unknown error";
            setLastError(errMsg);
            setTimeout(() => setLastError(null), 10000);
          }

          if (msg.type === "result") {
            setLastError(null);
          }

          listenersRef.current.forEach((fn) => fn(msg));
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setBridgeState("disconnected");
        wsRef.current = null;
        reconnectTimer.current = setTimeout(openConnection, RECONNECT_DELAY);
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    }

    openConnection();

    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, []);

  // -- Send ----------------------------------------------------------------

  const send = useCallback((msg: OutboundMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  // -- Subscribe -----------------------------------------------------------

  const subscribe = useCallback((fn: (msg: InboundMessage) => void) => {
    listenersRef.current.add(fn);
    return () => {
      listenersRef.current.delete(fn);
    };
  }, []);

  // -- Convenience methods (typed) -----------------------------------------

  const uploadFile = useCallback(
    (file: File, searchSpaceId: number = 1) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(",")[1];
        send({
          type: "upload",
          payload: {
            filename: file.name,
            data: base64,
            search_space_id: searchSpaceId,
          },
        });
      };
      reader.onerror = () => {
        setLastError(`Failed to read file: ${file.name}`);
      };
      reader.readAsDataURL(file);
    },
    [send],
  );

  const query = useCallback(
    (text: string, searchSpaceId: number = 1, threadId?: string) => {
      send({
        type: "query",
        payload: {
          query: text,
          search_space_id: searchSpaceId,
          thread_id: threadId,
        },
      });
    },
    [send],
  );

  const listDocs = useCallback(
    (searchSpaceId: number = 1) => {
      send({ type: "list_docs", payload: { search_space_id: searchSpaceId } });
    },
    [send],
  );

  const listSpaces = useCallback(() => {
    send({ type: "list_spaces" });
  }, [send]);

  const createSpace = useCallback(
    (name: string, description?: string) => {
      send({
        type: "create_space",
        payload: { name, description: description ?? "" },
      });
    },
    [send],
  );

  const deleteDocument = useCallback(
    (documentId: number, searchSpaceId?: number) => {
      send({
        type: "delete_document",
        payload: { document_id: documentId, search_space_id: searchSpaceId },
      });
    },
    [send],
  );

  const deleteSpace = useCallback(
    (searchSpaceId: number) => {
      send({
        type: "delete_space",
        payload: { search_space_id: searchSpaceId },
      });
    },
    [send],
  );

  const searchDocuments = useCallback(
    (title: string, searchSpaceId?: number) => {
      send({
        type: "search_documents",
        payload: { title, search_space_id: searchSpaceId },
      });
    },
    [send],
  );

  const clearHistory = useCallback(() => {
    send({ type: "clear" });
  }, [send]);

  return {
    bridgeState,
    systemStatus,
    lastError,
    send,
    subscribe,
    uploadFile,
    query,
    listDocs,
    listSpaces,
    createSpace,
    deleteDocument,
    deleteSpace,
    searchDocuments,
    clearHistory,
  };
}
