"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  FileSpreadsheet,
  File,
  Plus,
  ChevronRight,
  FolderOpen,
  Loader2,
  Upload,
} from "lucide-react";
import clsx from "clsx";
import { Skeleton } from "@/components/ui/skeleton";

import type { DocItem } from "../hooks/useDocumentsState";

export type { DocItem };

type Props = {
  documents: DocItem[];
  activeDocId: number | null;
  onSelectDoc: (doc: DocItem) => void;
  onUploadClick: () => void;
  isLoading: boolean;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function docIcon(type?: string) {
  const t = type?.toLowerCase() ?? "";
  if (t.includes("pdf")) return <FileText className="w-4 h-4 text-red-400" />;
  if (t.includes("sheet") || t.includes("csv") || t.includes("xls"))
    return <FileSpreadsheet className="w-4 h-4 text-green-400" />;
  return <File className="w-4 h-4 text-blue-400" />;
}

function formatDate(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// ---------------------------------------------------------------------------
// Skeleton loader
// ---------------------------------------------------------------------------

function SidebarSkeleton() {
  return (
    <div className="space-y-2 px-1">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="flex items-center gap-3 px-3 py-2.5">
          <Skeleton className="w-4 h-4 rounded" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3.5 w-[75%]" />
            <Skeleton className="h-2.5 w-[40%]" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyState({ onUploadClick }: { onUploadClick: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.1 }}
      className="text-center py-10 px-4"
    >
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-muted/50 mb-3">
        <Upload className="w-5 h-5 text-muted-foreground" />
      </div>
      <p className="text-sm font-medium text-foreground/80 mb-1">
        No documents yet
      </p>
      <p className="text-xs text-muted-foreground mb-4">
        Upload your first file to get started
      </p>
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={onUploadClick}
        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors"
      >
        <Plus className="w-3.5 h-3.5" />
        Upload document
      </motion.button>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DocSidebar({
  documents,
  activeDocId,
  onSelectDoc,
  onUploadClick,
  isLoading,
}: Props) {
  return (
    <aside className="w-64 h-full bg-background flex flex-col border-r border-border">
      {/* Header */}
      <div className="px-4 pt-5 pb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FolderOpen className="w-5 h-5 text-primary" />
          <span className="font-semibold text-sm">Documents</span>
        </div>
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          onClick={onUploadClick}
          className="p-1.5 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground transition-colors"
          title="Upload document"
        >
          <Plus className="w-4 h-4" />
        </motion.button>
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {isLoading && <SidebarSkeleton />}

        {!isLoading && documents.length === 0 && (
          <EmptyState onUploadClick={onUploadClick} />
        )}

        <AnimatePresence mode="popLayout">
          {documents.map((doc) => (
            <motion.button
              key={doc.id}
              layout
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              onClick={() => onSelectDoc(doc)}
              className={clsx(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors group",
                activeDocId === doc.id
                  ? "bg-primary/15 text-foreground"
                  : "hover:bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              {doc.status === "ready" ? (
                docIcon(doc.type)
              ) : (
                <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm truncate">{doc.title}</p>
                <p className="text-[10px] text-muted-foreground">
                  {formatDate(doc.created_at)}
                </p>
              </div>
              <ChevronRight
                className={clsx(
                  "w-3 h-3 opacity-0 group-hover:opacity-60 transition-opacity",
                  activeDocId === doc.id && "opacity-60"
                )}
              />
            </motion.button>
          ))}
        </AnimatePresence>
      </div>

      {/* Footer stats */}
      <div className="px-4 py-3 border-t border-border text-[10px] text-muted-foreground">
        {documents.length} document{documents.length !== 1 ? "s" : ""}
      </div>
    </aside>
  );
}
