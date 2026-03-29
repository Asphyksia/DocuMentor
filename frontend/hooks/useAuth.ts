"use client";

import { useCallback, useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AuthState = "checking" | "authenticated" | "unauthenticated";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const BRIDGE_HTTP =
  process.env.NEXT_PUBLIC_BRIDGE_HTTP_URL ??
  (process.env.NEXT_PUBLIC_BRIDGE_URL
    ? process.env.NEXT_PUBLIC_BRIDGE_URL
        .replace("ws://", "http://")
        .replace("wss://", "https://")
        .replace("/ws", "")
    : "http://localhost:8001");

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth() {
  const [state, setState] = useState<AuthState>("checking");
  const [error, setError] = useState<string | null>(null);
  const [authEnabled, setAuthEnabled] = useState(true);

  // Check session on mount
  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const res = await fetch(`${BRIDGE_HTTP}/auth/check`, {
          credentials: "include",
        });

        if (cancelled) return;

        if (res.ok) {
          const data = await res.json();
          setAuthEnabled(data.auth_enabled);
          setState("authenticated");
        } else {
          const data = await res.json().catch(() => ({}));
          setAuthEnabled(data.auth_enabled ?? true);
          setState("unauthenticated");
        }
      } catch {
        // Bridge not reachable — show login anyway
        if (!cancelled) {
          setState("unauthenticated");
        }
      }
    }

    check();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);

    try {
      const res = await fetch(`${BRIDGE_HTTP}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });

      if (res.ok) {
        const data = await res.json();
        // Store token for WebSocket auth (query param fallback)
        if (data.token) {
          sessionStorage.setItem("documenter_token", data.token);
        }
        setState("authenticated");
        return true;
      } else {
        setError("Credenciales incorrectas");
        return false;
      }
    } catch {
      setError("No se puede conectar con el servidor");
      return false;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${BRIDGE_HTTP}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // ignore
    }
    sessionStorage.removeItem("documenter_token");
    setState("unauthenticated");
  }, []);

  return { state, error, authEnabled, login, logout };
}

/**
 * Get the WebSocket URL with auth token appended as query param.
 * Falls back to cookie-based auth if no token stored.
 */
export function getAuthenticatedWsUrl(baseUrl: string): string {
  const token =
    typeof window !== "undefined"
      ? sessionStorage.getItem("documenter_token")
      : null;

  if (token) {
    const separator = baseUrl.includes("?") ? "&" : "?";
    return `${baseUrl}${separator}token=${token}`;
  }

  return baseUrl;
}
