"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Upload,
  Cpu,
  GitBranch,
  Globe,
  Search,
  ShieldCheck,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { getHealth } from "@/lib/api";
import type { HealthResponse } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";

const sections = [
  {
    href: "/upload",
    label: "Upload Documents",
    icon: Upload,
    description: "Ingest PDFs, Word docs, and plain text for entity extraction.",
  },
  {
    href: "/extract",
    label: "Extract Entities",
    icon: Cpu,
    description: "Run AI pipelines to identify entities, relationships, and events.",
  },
  {
    href: "/ontology",
    label: "Ontology",
    icon: GitBranch,
    description: "Define and manage domain ontologies: classes, properties, constraints.",
  },
  {
    href: "/graph",
    label: "Graph Viewer",
    icon: Globe,
    description: "Explore the knowledge graph with interactive visualizations.",
  },
  {
    href: "/query",
    label: "Query",
    icon: Search,
    description: "Ask natural-language or Cypher/SPARQL questions over the graph.",
  },
  {
    href: "/validation",
    label: "Validation",
    icon: ShieldCheck,
    description: "Validate graph consistency against ontology rules and constraints.",
  },
  {
    href: "/semantic-search",
    label: "Semantic Search",
    icon: Sparkles,
    description: "Search document chunks by meaning using vector embeddings.",
  },
];

type ConnectionStatus = "loading" | "connected" | "unreachable";

export default function HomePage() {
  const [status, setStatus] = useState<ConnectionStatus>("loading");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [responseTimeMs, setResponseTimeMs] = useState<number | undefined>();

  useEffect(() => {
    const check = async () => {
      const start = performance.now();
      try {
        const data = await getHealth();
        setResponseTimeMs(Math.round(performance.now() - start));
        setHealth(data);
        setStatus("connected");
      } catch {
        setStatus("unreachable");
      }
    };
    check();
  }, []);

  return (
    <div className="max-w-5xl mx-auto">
      {/* Hero */}
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-slate-100 mb-2">
          Ontology Graph Studio
        </h1>
        <p className="text-slate-400 text-base max-w-2xl">
          Transform unstructured documents into structured, queryable knowledge
          graphs. Powered by AI — ready for enterprise ontology workflows.
        </p>
      </div>

      {/* Backend status */}
      <div className="card mb-8">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
              System Status
            </h2>
            <StatusBadge status={status} responseTimeMs={responseTimeMs} />
          </div>

          {health && status === "connected" && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-slate-500 text-xs uppercase tracking-wider">Version</p>
                <p className="text-slate-200 font-mono">{health.version}</p>
              </div>
              <div>
                <p className="text-slate-500 text-xs uppercase tracking-wider">Environment</p>
                <p className="text-slate-200 capitalize">{health.environment}</p>
              </div>
              <div>
                <p className="text-slate-500 text-xs uppercase tracking-wider">Database</p>
                <p className="text-slate-200 capitalize">{health.db_status.replace("_", " ")}</p>
              </div>
              <div>
                <p className="text-slate-500 text-xs uppercase tracking-wider">Response</p>
                <p className="text-slate-200">{responseTimeMs}ms</p>
              </div>
            </div>
          )}

          {status === "unreachable" && (
            <p className="text-sm text-slate-500">
              Ensure the backend is running on{" "}
              <code className="font-mono text-slate-400">localhost:8000</code>
            </p>
          )}
        </div>
      </div>

      {/* Quick-link grid */}
      <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
        Modules
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {sections.map(({ href, label, icon: Icon, description }) => (
          <Link
            key={href}
            href={href}
            className="card group hover:border-brand-700 hover:bg-slate-800/60 transition-all duration-150 flex flex-col gap-3"
          >
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-slate-800 group-hover:bg-brand-900/50 transition-colors">
                <Icon className="w-4 h-4 text-brand-400" />
              </div>
              <span className="font-medium text-slate-200 text-sm">{label}</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-brand-400 ml-auto transition-colors" />
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">{description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
