import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ontology Graph Studio",
  description: "AI-powered ontology-based knowledge graph builder",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
