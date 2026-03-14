import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import LeftNav from "@/components/LeftNav";

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
      <body suppressHydrationWarning>
        <Header />
        <div className="flex min-h-screen pt-14">
          <LeftNav />
          <main className="flex-1 ml-56 p-8 overflow-y-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
