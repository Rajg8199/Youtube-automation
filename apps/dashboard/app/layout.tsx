import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  title: "PhoneWala Gyan — Control",
  description: "Autonomous YouTube content system dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans">
        <div className="flex min-h-dvh">
          <Sidebar />
          <div className="flex-1 min-w-0">
            <main className="mx-auto max-w-6xl px-8 py-8">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
