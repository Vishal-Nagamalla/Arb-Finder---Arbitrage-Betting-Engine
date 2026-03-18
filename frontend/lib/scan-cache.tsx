"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";
import { ScanResponse, ArbOpportunity } from "@/lib/api";

interface ScanCacheContextType {
  scanData: ScanResponse | null;
  setScanData: (data: ScanResponse | null) => void;
  opportunities: ArbOpportunity[];
  setOpportunities: (arbs: ArbOpportunity[]) => void;
  loading: boolean;
  setLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
  autoScan: boolean;
  setAutoScan: (auto: boolean) => void;
}

const ScanCacheContext = createContext<ScanCacheContextType | undefined>(undefined);

export function ScanCacheProvider({ children }: { children: ReactNode }) {
  const [scanData, setScanData] = useState<ScanResponse | null>(null);
  const [opportunities, setOpportunities] = useState<ArbOpportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoScan, setAutoScan] = useState(false);

  return (
    <ScanCacheContext.Provider
      value={{
        scanData, setScanData,
        opportunities, setOpportunities,
        loading, setLoading,
        error, setError,
        autoScan, setAutoScan,
      }}
    >
      {children}
    </ScanCacheContext.Provider>
  );
}

export function useScanCache() {
  const context = useContext(ScanCacheContext);
  if (!context) {
    throw new Error("useScanCache must be used within a ScanCacheProvider");
  }
  return context;
}