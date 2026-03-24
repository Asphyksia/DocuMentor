"use client";

import { useCallback, useState } from "react";
import type { DashboardData } from "../types/bridge";

export function useDashboardState() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);

  const updateDashboard = useCallback((data: DashboardData) => {
    setDashboard(data);
  }, []);

  const clearDashboard = useCallback(() => {
    setDashboard(null);
  }, []);

  return { dashboard, updateDashboard, clearDashboard };
}
