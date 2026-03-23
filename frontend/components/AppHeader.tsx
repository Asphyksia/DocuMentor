"use client";

import { motion } from "framer-motion";
import {
  MessageSquare,
  LayoutDashboard,
  Settings,
  Wifi,
  WifiOff,
  Loader2,
  FileText,
} from "lucide-react";
import clsx from "clsx";
import type { BridgeState, SystemStatus } from "../hooks/useBridge";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type TabId = "chat" | "dashboard" | "settings";

type Props = {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  bridgeState: BridgeState;
  systemStatus: SystemStatus;
};

// ---------------------------------------------------------------------------
// Tab config
// ---------------------------------------------------------------------------

const TABS: { id: TabId; label: string; icon: typeof MessageSquare }[] = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "settings", label: "Settings", icon: Settings },
];

// ---------------------------------------------------------------------------
// Status indicator
// ---------------------------------------------------------------------------

function StatusIndicator({
  bridgeState,
  systemStatus,
}: {
  bridgeState: BridgeState;
  systemStatus: SystemStatus;
}) {
  const isConnected = bridgeState === "connected";
  const isBusy = ["uploading", "indexing", "querying"].includes(systemStatus.state);

  return (
    <div className="flex items-center gap-2 text-xs">
      {isBusy && (
        <motion.div
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: 1, width: "auto" }}
          exit={{ opacity: 0, width: 0 }}
          className="flex items-center gap-1.5 bg-blue-500/10 text-blue-400 px-2.5 py-1 rounded-full"
        >
          <Loader2 className="w-3 h-3 animate-spin" />
          <span className="capitalize">{systemStatus.state}</span>
        </motion.div>
      )}

      <div
        className={clsx(
          "flex items-center gap-1.5 px-2.5 py-1 rounded-full",
          isConnected
            ? "bg-green-500/10 text-green-400"
            : "bg-red-500/10 text-red-400"
        )}
      >
        {isConnected ? (
          <Wifi className="w-3 h-3" />
        ) : (
          <WifiOff className="w-3 h-3" />
        )}
        <span>{isConnected ? "Connected" : "Disconnected"}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AppHeader({
  activeTab,
  onTabChange,
  bridgeState,
  systemStatus,
}: Props) {
  return (
    <header className="h-14 bg-gray-950 border-b border-gray-800 flex items-center justify-between px-4">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <FileText className="w-4 h-4 text-white" />
        </div>
        <h1 className="text-base font-bold text-white tracking-tight">
          DocuMentor
        </h1>
      </div>

      {/* Tabs */}
      <nav className="flex items-center gap-1">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={clsx(
                "relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors",
                isActive
                  ? "text-white"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-gray-800 rounded-lg"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <span className="relative z-10 flex items-center gap-2">
                <Icon className="w-4 h-4" />
                {tab.label}
              </span>
            </button>
          );
        })}
      </nav>

      {/* Status */}
      <StatusIndicator bridgeState={bridgeState} systemStatus={systemStatus} />
    </header>
  );
}
