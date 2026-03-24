"use client";

import { useCallback, useState } from "react";
import type { ConnectionState } from "../types/bridge";

export type UploadUiStatus = "idle" | "uploading" | "indexing" | "ready" | "error";

function mapConnectionToUpload(state: ConnectionState): UploadUiStatus {
  switch (state) {
    case "uploading":
      return "uploading";
    case "indexing":
      return "indexing";
    case "error":
      return "error";
    case "ready":
      return "ready";
    case "querying":
    default:
      return "idle";
  }
}

export function useUploadState() {
  const [showModal, setShowModal] = useState(false);
  const [status, setStatus] = useState<UploadUiStatus>("idle");
  const [message, setMessage] = useState("");

  const openModal = useCallback(() => {
    setStatus("idle");
    setMessage("");
    setShowModal(true);
  }, []);

  const closeModal = useCallback(() => {
    setShowModal(false);
    setStatus("idle");
    setMessage("");
  }, []);

  const updateFromBridge = useCallback((state: ConnectionState, msg: string) => {
    setStatus(mapConnectionToUpload(state));
    setMessage(msg);
  }, []);

  const reset = useCallback(() => {
    setStatus("idle");
    setMessage("");
  }, []);

  return {
    showModal,
    status,
    message,
    openModal,
    closeModal,
    updateFromBridge,
    reset,
  };
}
