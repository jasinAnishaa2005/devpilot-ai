import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DevPilot AI — Repository Onboarding",
  description:
    "AI-powered GitHub repository onboarding assistant. Understand any codebase in seconds.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
