"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Save, Plus, Database, Cpu, Key, ExternalLink } from "lucide-react";
import clsx from "clsx";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Space = { id: number; name: string; description?: string };

type Props = {
  spaces: Space[];
  activeSpaceId: number;
  onChangeSpace: (id: number) => void;
  onCreateSpace: (name: string, desc: string) => void;
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SettingsPanel({
  spaces,
  activeSpaceId,
  onChangeSpace,
  onCreateSpace,
}: Props) {
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const handleCreate = () => {
    if (!newName.trim()) return;
    onCreateSpace(newName.trim(), newDesc.trim());
    setNewName("");
    setNewDesc("");
  };

  return (
    <div className="max-w-2xl mx-auto p-8 space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h2 className="text-xl font-bold text-white mb-1">Settings</h2>
        <p className="text-sm text-gray-500">Manage your DocuMentor configuration</p>
      </motion.div>

      {/* Search Spaces */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-6"
      >
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-blue-400" />
          <h3 className="text-sm font-semibold text-white">Knowledge Bases</h3>
        </div>

        <div className="space-y-2 mb-4">
          {spaces.map((s) => (
            <button
              key={s.id}
              onClick={() => onChangeSpace(s.id)}
              className={clsx(
                "w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all",
                activeSpaceId === s.id
                  ? "bg-blue-600/20 border border-blue-500/30 text-white"
                  : "bg-gray-900/50 border border-transparent hover:border-gray-700 text-gray-300"
              )}
            >
              <Database className="w-4 h-4 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium">{s.name}</p>
                {s.description && (
                  <p className="text-xs text-gray-500">{s.description}</p>
                )}
              </div>
            </button>
          ))}
        </div>

        <div className="border-t border-gray-700/50 pt-4 space-y-3">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="New knowledge base name..."
            className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />
          <input
            type="text"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="Description (optional)"
            className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleCreate}
            disabled={!newName.trim()}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              newName.trim()
                ? "bg-blue-600 hover:bg-blue-500 text-white"
                : "bg-gray-800 text-gray-500 cursor-not-allowed"
            )}
          >
            <Plus className="w-4 h-4" />
            Create
          </motion.button>
        </div>
      </motion.section>

      {/* Info */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.2 }}
        className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-6 space-y-4"
      >
        <div className="flex items-center gap-2 mb-2">
          <Cpu className="w-5 h-5 text-indigo-400" />
          <h3 className="text-sm font-semibold text-white">System Info</h3>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500 text-xs">LLM Provider</p>
            <p className="text-gray-200">RelayGPU (OpenGPU)</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs">Model</p>
            <p className="text-gray-200">Configured in .env</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs">RAG Backend</p>
            <p className="text-gray-200">SurfSense</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs">Agent</p>
            <p className="text-gray-200">Hermes Agent</p>
          </div>
        </div>

        <a
          href="https://relay.opengpu.network"
          target="_blank"
          rel="noopener"
          className="inline-flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors"
        >
          <Key className="w-3 h-3" />
          Manage API key at RelayGPU
          <ExternalLink className="w-3 h-3" />
        </a>
      </motion.section>
    </div>
  );
}
