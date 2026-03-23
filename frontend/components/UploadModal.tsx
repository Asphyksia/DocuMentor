"use client";

import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, X, FileText, CheckCircle, AlertCircle } from "lucide-react";
import clsx from "clsx";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (file: File) => void;
  status: "idle" | "uploading" | "indexing" | "ready" | "error";
  statusMessage: string;
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function UploadModal({
  isOpen,
  onClose,
  onUpload,
  status,
  statusMessage,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) onUpload(file);
    },
    [onUpload]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  };

  const isBusy = status === "uploading" || status === "indexing";

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={!isBusy ? onClose : undefined}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="bg-gray-900 rounded-2xl border border-gray-700/50 shadow-2xl w-full max-w-lg p-6">
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-white">Upload Document</h2>
                {!isBusy && (
                  <button
                    onClick={onClose}
                    className="p-1.5 rounded-lg hover:bg-gray-800 transition-colors"
                  >
                    <X className="w-5 h-5 text-gray-400" />
                  </button>
                )}
              </div>

              {/* Drop zone */}
              <div
                onDrop={handleDrop}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onClick={() => !isBusy && inputRef.current?.click()}
                className={clsx(
                  "relative rounded-xl border-2 border-dashed p-12 text-center transition-all duration-300 cursor-pointer",
                  isDragging && "border-blue-400 bg-blue-500/10 scale-[1.02]",
                  isBusy && "cursor-wait",
                  status === "ready" && "border-green-400 bg-green-500/5",
                  status === "error" && "border-red-400 bg-red-500/5",
                  !isDragging && !isBusy && status === "idle" &&
                    "border-gray-700 hover:border-blue-500/50 hover:bg-gray-800/50"
                )}
              >
                <input
                  ref={inputRef}
                  type="file"
                  className="hidden"
                  accept=".pdf,.xlsx,.xls,.csv,.docx,.doc,.txt,.md,.pptx"
                  onChange={handleChange}
                />

                <motion.div
                  animate={
                    isBusy
                      ? { rotate: 360 }
                      : status === "ready"
                      ? { scale: [1, 1.1, 1] }
                      : {}
                  }
                  transition={
                    isBusy
                      ? { repeat: Infinity, duration: 2, ease: "linear" }
                      : { duration: 0.4 }
                  }
                  className="mx-auto mb-4"
                >
                  {status === "ready" ? (
                    <CheckCircle className="w-12 h-12 text-green-400 mx-auto" />
                  ) : status === "error" ? (
                    <AlertCircle className="w-12 h-12 text-red-400 mx-auto" />
                  ) : (
                    <Upload
                      className={clsx(
                        "w-12 h-12 mx-auto",
                        isBusy ? "text-blue-400" : "text-gray-500"
                      )}
                    />
                  )}
                </motion.div>

                <p className="text-sm font-medium text-gray-200 mb-1">
                  {status === "idle" && "Drop your file here or click to browse"}
                  {status === "uploading" && "Uploading..."}
                  {status === "indexing" && "Indexing document..."}
                  {status === "ready" && "Document processed successfully!"}
                  {status === "error" && "Upload failed — try again"}
                </p>
                <p className="text-xs text-gray-500">
                  {statusMessage || "PDF · Excel · CSV · Word · PowerPoint · TXT"}
                </p>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 mt-6">
                {status === "ready" && (
                  <motion.button
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={onClose}
                    className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
                  >
                    Done
                  </motion.button>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
