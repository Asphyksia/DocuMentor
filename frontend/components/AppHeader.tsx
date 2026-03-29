"use client";

import { motion, AnimatePresence } from "framer-motion";
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
          className="flex items-center gap-1.5 bg-primary/10 text-primary px-2.5 py-1 rounded-full"
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
// Connection banner
// ---------------------------------------------------------------------------

export function ConnectionBanner({ bridgeState }: { bridgeState: BridgeState }) {
  return (
    <AnimatePresence>
      {bridgeState === "disconnected" && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="overflow-hidden"
        >
          <div className="flex items-center justify-center gap-2 bg-destructive/10 border-b border-destructive/20 px-4 py-2 text-xs text-destructive">
            <WifiOff className="w-3.5 h-3.5" />
            <span>Connection lost — reconnecting automatically...</span>
            <Loader2 className="w-3 h-3 animate-spin" />
          </div>
        </motion.div>
      )}
      {bridgeState === "connecting" && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="overflow-hidden"
        >
          <div className="flex items-center justify-center gap-2 bg-yellow-500/10 border-b border-yellow-500/20 px-4 py-2 text-xs text-yellow-500">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Connecting to server...</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
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
    <header className="bg-background border-b border-border">
      <div className="h-14 flex items-center justify-between px-4">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center shadow-lg shadow-primary/20">
            <FileText className="w-4 h-4 text-primary-foreground" />
          </div>
          <h1 className="text-base font-bold tracking-tight">
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
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute inset-0 bg-muted rounded-lg"
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
      </div>

      {/* Connection banner */}
      <ConnectionBanner bridgeState={bridgeState} />
    </header>
  );
}
