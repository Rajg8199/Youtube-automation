import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PhoneWala Gyan — Control",
  description: "Autonomous YouTube content system dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-neutral-800 px-6 py-4">
          <span className="text-brand-orange font-bold">PhoneWala Gyan</span>
          <span className="text-neutral-500"> · Control</span>
        </header>
        <main className="p-6">{children}</main>
      </body>
    </html>
  );
}
