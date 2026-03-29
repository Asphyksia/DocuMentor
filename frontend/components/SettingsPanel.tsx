"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Plus,
  Database,
  Cpu,
  Key,
  ExternalLink,
  Shield,
  LogOut,
  Keyboard,
} from "lucide-react";
import clsx from "clsx";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Space = { id: number; name: string; description?: string };

type Props = {
  spaces: Space[];
  activeSpaceId: number;
  onChangeSpace: (id: number) => void;
  onCreateSpace: (name: string, desc: string) => void;
  onLogout?: () => void;
};

type HealthInfo = {
  version?: string;
  hermes?: boolean;
  auth_enabled?: boolean;
  clients?: number;
  pool_size?: number;
  pool_available?: number;
  model?: string;
};

// ---------------------------------------------------------------------------
// Health fetcher
// ---------------------------------------------------------------------------

const BRIDGE_HTTP =
  process.env.NEXT_PUBLIC_BRIDGE_HTTP_URL ??
  (process.env.NEXT_PUBLIC_BRIDGE_URL
    ? process.env.NEXT_PUBLIC_BRIDGE_URL
        .replace("ws://", "http://")
        .replace("wss://", "https://")
        .replace("/ws", "")
    : "http://localhost:8001");

async function fetchHealth(): Promise<HealthInfo> {
  try {
    const [bridgeRes, hermesRes] = await Promise.allSettled([
      fetch(`${BRIDGE_HTTP}/health`, { credentials: "include" }),
      fetch(`${BRIDGE_HTTP.replace(":8001", ":8002")}/health`),
    ]);

    const bridge =
      bridgeRes.status === "fulfilled" && bridgeRes.value.ok
        ? await bridgeRes.value.json()
        : {};
    const hermes =
      hermesRes.status === "fulfilled" && hermesRes.value.ok
        ? await hermesRes.value.json()
        : {};

    return {
      version: bridge.version,
      hermes: bridge.hermes ?? false,
      auth_enabled: bridge.auth_enabled,
      clients: bridge.clients,
      pool_size: hermes.pool_size,
      pool_available: hermes.pool_available,
      model: hermes.model,
    };
  } catch {
    return {};
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SettingsPanel({
  spaces,
  activeSpaceId,
  onChangeSpace,
  onCreateSpace,
  onLogout,
}: Props) {
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [health, setHealth] = useState<HealthInfo>({});

  useEffect(() => {
    fetchHealth().then(setHealth);
  }, []);

  const handleCreate = () => {
    if (!newName.trim()) return;
    onCreateSpace(newName.trim(), newDesc.trim());
    setNewName("");
    setNewDesc("");
  };

  return (
    <div className="max-w-2xl mx-auto p-8 space-y-6 overflow-y-auto h-full">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h2 className="text-xl font-bold mb-1">Settings</h2>
        <p className="text-sm text-muted-foreground">
          Manage your DocuMentor configuration
        </p>
      </motion.div>

      {/* Knowledge Bases */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Database className="w-4 h-4 text-primary" />
              Knowledge Bases
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {spaces.map((s) => (
              <button
                key={s.id}
                onClick={() => onChangeSpace(s.id)}
                className={clsx(
                  "w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all",
                  activeSpaceId === s.id
                    ? "bg-primary/10 border border-primary/30"
                    : "bg-muted/50 border border-transparent hover:border-border"
                )}
              >
                <Database className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">{s.name}</p>
                  {s.description && (
                    <p className="text-xs text-muted-foreground">
                      {s.description}
                    </p>
                  )}
                </div>
                {activeSpaceId === s.id && (
                  <Badge variant="secondary" className="ml-auto text-[10px]">
                    Active
                  </Badge>
                )}
              </button>
            ))}

            <Separator />

            <div className="space-y-2">
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="New knowledge base name..."
                className="text-sm"
              />
              <Input
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="Description (optional)"
                className="text-sm"
              />
              <Button
                onClick={handleCreate}
                disabled={!newName.trim()}
                size="sm"
                className="gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                Create
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* System Info */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.15 }}
      >
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Cpu className="w-4 h-4 text-primary" />
              System Info
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground text-xs mb-0.5">Bridge</p>
                <p className="font-medium">
                  v{health.version ?? "—"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs mb-0.5">Hermes Agent</p>
                <div className="flex items-center gap-1.5">
                  <span
                    className={clsx(
                      "w-2 h-2 rounded-full",
                      health.hermes ? "bg-green-500" : "bg-red-500"
                    )}
                  />
                  <span className="font-medium">
                    {health.hermes ? "Connected" : "Disconnected"}
                  </span>
                </div>
              </div>
              <div>
                <p className="text-muted-foreground text-xs mb-0.5">Model</p>
                <p className="font-medium font-mono text-xs">
                  {health.model ?? "N/A"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs mb-0.5">Agent Pool</p>
                <p className="font-medium">
                  {health.pool_available !== undefined
                    ? `${health.pool_available}/${health.pool_size} available`
                    : "N/A"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs mb-0.5">Auth</p>
                <Badge variant={health.auth_enabled ? "default" : "outline"} className="text-[10px]">
                  {health.auth_enabled ? "Enabled" : "Disabled"}
                </Badge>
              </div>
              <div>
                <p className="text-muted-foreground text-xs mb-0.5">
                  Connected Clients
                </p>
                <p className="font-medium">{health.clients ?? "—"}</p>
              </div>
            </div>

            <Separator className="my-4" />

            <a
              href="https://relay.opengpu.network"
              target="_blank"
              rel="noopener"
              className="inline-flex items-center gap-1.5 text-xs text-primary hover:text-primary/80 transition-colors"
            >
              <Key className="w-3 h-3" />
              Manage API key at RelayGPU
              <ExternalLink className="w-3 h-3" />
            </a>
          </CardContent>
        </Card>
      </motion.div>

      {/* Keyboard Shortcuts */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.2 }}
      >
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Keyboard className="w-4 h-4 text-primary" />
              Keyboard Shortcuts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              {[
                { keys: "Enter", desc: "Send message" },
                { keys: "Shift+Enter", desc: "New line in message" },
                { keys: "Ctrl+U", desc: "Upload document" },
                { keys: "Ctrl+N", desc: "New conversation" },
                { keys: "Esc", desc: "Close modal" },
              ].map((s) => (
                <div
                  key={s.keys}
                  className="flex items-center justify-between"
                >
                  <span className="text-muted-foreground text-xs">
                    {s.desc}
                  </span>
                  <kbd className="text-[10px] font-mono bg-muted px-2 py-0.5 rounded border border-border">
                    {s.keys}
                  </kbd>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Logout */}
      {onLogout && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.25 }}
        >
          <Button
            variant="outline"
            size="sm"
            onClick={onLogout}
            className="gap-1.5 text-destructive hover:text-destructive"
          >
            <LogOut className="w-3.5 h-3.5" />
            Log out
          </Button>
        </motion.div>
      )}
    </div>
  );
}
