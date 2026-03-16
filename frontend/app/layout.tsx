import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Arb Finder",
  description: "Personal arbitrage betting detection engine",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Sidebar />
        <main className="md:ml-56 min-h-screen pb-20 md:pb-0">{children}</main>
      </body>
    </html>
  );
}