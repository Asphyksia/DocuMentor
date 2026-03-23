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
} from "lucide-react";
import clsx from "clsx";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type DocItem = {
  id: number;
  title: string;
  type: string;
  status: string;
  created_at?: string;
};

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

function docIcon(type: string) {
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
    <aside className="w-64 h-full bg-gray-950 text-gray-200 flex flex-col border-r border-gray-800">
      {/* Header */}
      <div className="px-4 pt-5 pb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FolderOpen className="w-5 h-5 text-blue-400" />
          <span className="font-semibold text-sm text-white">Documents</span>
        </div>
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          onClick={onUploadClick}
          className="p-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 transition-colors"
          title="Upload document"
        >
          <Plus className="w-4 h-4" />
        </motion.button>
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 text-gray-500 animate-spin" />
          </div>
        )}

        {!isLoading && documents.length === 0 && (
          <div className="text-center py-8 px-4">
            <File className="w-8 h-8 text-gray-700 mx-auto mb-2" />
            <p className="text-xs text-gray-500">
              No documents yet.
              <br />
              Upload your first file to get started.
            </p>
          </div>
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
                  ? "bg-blue-600/20 text-white"
                  : "hover:bg-gray-800/60 text-gray-300"
              )}
            >
              {doc.status === "ready" ? (
                docIcon(doc.type)
              ) : (
                <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm truncate">{doc.title}</p>
                <p className="text-[10px] text-gray-500">{formatDate(doc.created_at)}</p>
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
      <div className="px-4 py-3 border-t border-gray-800 text-[10px] text-gray-600">
        {documents.length} document{documents.length !== 1 ? "s" : ""}
      </div>
    </aside>
  );
}
