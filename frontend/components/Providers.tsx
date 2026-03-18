"use client";

import { ScanCacheProvider } from "@/lib/scan-cache";

export default function Providers({ children }: { children: React.ReactNode }) {
  return <ScanCacheProvider>{children}</ScanCacheProvider>;
}