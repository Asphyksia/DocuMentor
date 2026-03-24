"use client";

import { useCallback, useState } from "react";
import type { DocumentItem, SpaceItem } from "../types/bridge";

export interface DocItem {
  id: number;
  title: string;
  type?: string;
  status?: string;
  created_at?: string;
}

export function useDocumentsState(defaultSpaceId: number) {
  const [documents, setDocuments] = useState<DocItem[]>([]);
  const [activeDocId, setActiveDocId] = useState<number | null>(null);
  const [docsLoading, setDocsLoading] = useState(true);
  const [spaces, setSpaces] = useState<SpaceItem[]>([]);
  const [activeSpaceId, setActiveSpaceId] = useState(defaultSpaceId);

  const updateDocuments = useCallback((docs: DocumentItem[]) => {
    setDocuments(
      docs.map((d) => ({
        id: d.id,
        title: d.title,
        type: d.type,
        status: d.status,
        created_at: d.created_at,
      }))
    );
    setDocsLoading(false);
  }, []);

  const updateSpaces = useCallback((items: SpaceItem[]) => {
    setSpaces(items);
  }, []);

  return {
    documents,
    activeDocId,
    setActiveDocId,
    docsLoading,
    spaces,
    activeSpaceId,
    setActiveSpaceId,
    updateDocuments,
    updateSpaces,
  };
}
