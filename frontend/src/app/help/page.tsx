"use client";

import { useEffect, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BookOpen, Code2, ChevronRight, Search } from "lucide-react";

type Tab = "user" | "tech";

const DOCS: Record<Tab, { file: string; label: string; description: string }> = {
  user: {
    file: "/docs/user-manual.md",
    label: "User Manual",
    description: "For business users — workflows, modules, and practical examples",
  },
  tech: {
    file: "/docs/technical-guide.md",
    label: "Technical Documentation",
    description: "For developers — APIs, data models, Neo4j, and deployment",
  },
};

interface Heading {
  id: string;
  text: string;
  level: number;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

function extractHeadings(markdown: string): Heading[] {
  const lines = markdown.split("\n");
  const headings: Heading[] = [];
  for (const line of lines) {
    const match = line.match(/^(#{1,3})\s+(.+)$/);
    if (match) {
      const level = match[1].length;
      const text = match[2].replace(/\*\*/g, "").trim();
      headings.push({ id: slugify(text), text, level });
    }
  }
  return headings;
}

export default function HelpPage() {
  const [activeTab, setActiveTab] = useState<Tab>("user");
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [headings, setHeadings] = useState<Heading[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeHeading, setActiveHeading] = useState<string>("");

  const loadDoc = useCallback(async (tab: Tab) => {
    setLoading(true);
    try {
      const res = await fetch(DOCS[tab].file);
      const text = await res.text();
      setContent(text);
      setHeadings(extractHeadings(text));
      setActiveHeading("");
    } catch {
      setContent("# Error\n\nFailed to load documentation.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDoc(activeTab);
  }, [activeTab, loadDoc]);

  const filteredHeadings = headings.filter(
    (h) =>
      h.level <= 2 &&
      (searchQuery === "" || h.text.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab);
    setSearchQuery("");
    window.scrollTo({ top: 0 });
  };

  const scrollToHeading = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      const offset = 80;
      const top = el.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: "smooth" });
      setActiveHeading(id);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900 px-6 py-5">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-xl font-semibold text-white mb-1">Help &amp; Documentation</h1>
          <p className="text-sm text-slate-400">
            Ontology Graph Studio — Platform Reference
          </p>

          {/* Tab switcher */}
          <div className="flex gap-2 mt-4">
            {(Object.entries(DOCS) as [Tab, (typeof DOCS)[Tab]][]).map(([key, doc]) => (
              <button
                key={key}
                onClick={() => handleTabChange(key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === key
                    ? "bg-blue-600 text-white"
                    : "bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700"
                }`}
              >
                {key === "user" ? <BookOpen className="w-4 h-4" /> : <Code2 className="w-4 h-4" />}
                {doc.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-500 mt-2">{DOCS[activeTab].description}</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto flex gap-0">
        {/* Sidebar */}
        <aside className="w-64 flex-shrink-0 border-r border-slate-800 min-h-[calc(100vh-120px)] sticky top-0 self-start pt-6 pb-8 px-4">
          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search sections…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-md text-xs text-slate-200 pl-8 pr-3 py-1.5 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 px-1">
            Sections
          </p>

          <nav className="space-y-0.5">
            {loading ? (
              <div className="space-y-2 mt-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="h-5 bg-slate-800 rounded animate-pulse" style={{ width: `${60 + (i % 4) * 10}%` }} />
                ))}
              </div>
            ) : filteredHeadings.length === 0 ? (
              <p className="text-xs text-slate-600 px-1">No sections match</p>
            ) : (
              filteredHeadings.map((h) => (
                <button
                  key={h.id}
                  onClick={() => scrollToHeading(h.id)}
                  className={`w-full text-left flex items-start gap-1.5 px-2 py-1 rounded text-xs transition-colors group ${
                    activeHeading === h.id
                      ? "bg-blue-900/40 text-blue-300"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                  } ${h.level === 1 ? "font-semibold" : h.level === 2 ? "pl-4" : "pl-6"}`}
                >
                  <ChevronRight className={`w-3 h-3 mt-0.5 flex-shrink-0 transition-opacity ${activeHeading === h.id ? "opacity-100 text-blue-400" : "opacity-0 group-hover:opacity-60"}`} />
                  <span className="leading-snug">{h.text}</span>
                </button>
              ))
            )}
          </nav>
        </aside>

        {/* Main content */}
        <main className="flex-1 min-w-0 px-10 py-8">
          {loading ? (
            <div className="space-y-4 animate-pulse">
              <div className="h-8 bg-slate-800 rounded w-2/3" />
              <div className="h-4 bg-slate-800 rounded w-full" />
              <div className="h-4 bg-slate-800 rounded w-5/6" />
              <div className="h-4 bg-slate-800 rounded w-4/5" />
              <div className="h-6 bg-slate-800 rounded w-1/2 mt-8" />
              <div className="h-4 bg-slate-800 rounded w-full" />
              <div className="h-4 bg-slate-800 rounded w-5/6" />
            </div>
          ) : (
            <div className="prose-doc">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => {
                    const text = String(children);
                    const id = slugify(text);
                    return (
                      <h1 id={id} className="text-2xl font-bold text-white mt-0 mb-4 pb-3 border-b border-slate-700">
                        {children}
                      </h1>
                    );
                  },
                  h2: ({ children }) => {
                    const text = String(children);
                    const id = slugify(text);
                    return (
                      <h2 id={id} className="text-lg font-semibold text-slate-100 mt-10 mb-3 pb-2 border-b border-slate-800">
                        {children}
                      </h2>
                    );
                  },
                  h3: ({ children }) => {
                    const text = String(children);
                    const id = slugify(text);
                    return (
                      <h3 id={id} className="text-base font-semibold text-slate-200 mt-6 mb-2">
                        {children}
                      </h3>
                    );
                  },
                  h4: ({ children }) => (
                    <h4 className="text-sm font-semibold text-slate-300 mt-4 mb-1 uppercase tracking-wide">
                      {children}
                    </h4>
                  ),
                  p: ({ children }) => (
                    <p className="text-sm text-slate-300 leading-relaxed mb-4">{children}</p>
                  ),
                  ul: ({ children }) => (
                    <ul className="list-disc list-outside pl-5 mb-4 space-y-1 text-sm text-slate-300">
                      {children}
                    </ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal list-outside pl-5 mb-4 space-y-1 text-sm text-slate-300">
                      {children}
                    </ol>
                  ),
                  li: ({ children }) => (
                    <li className="leading-relaxed">{children}</li>
                  ),
                  strong: ({ children }) => (
                    <strong className="font-semibold text-slate-100">{children}</strong>
                  ),
                  em: ({ children }) => (
                    <em className="italic text-slate-300">{children}</em>
                  ),
                  code: ({ className, children, ...props }) => {
                    const isInline = !className;
                    if (isInline) {
                      return (
                        <code className="bg-slate-800 text-blue-300 text-xs px-1.5 py-0.5 rounded font-mono border border-slate-700">
                          {children}
                        </code>
                      );
                    }
                    const lang = className?.replace("language-", "") ?? "";
                    return (
                      <div className="my-4 rounded-lg overflow-hidden border border-slate-700">
                        {lang && (
                          <div className="bg-slate-800 border-b border-slate-700 px-4 py-1.5 flex items-center justify-between">
                            <span className="text-xs text-slate-500 font-mono uppercase tracking-wider">{lang}</span>
                          </div>
                        )}
                        <code className="block bg-slate-900 text-slate-300 text-xs font-mono p-4 overflow-x-auto leading-relaxed whitespace-pre">
                          {children}
                        </code>
                      </div>
                    );
                  },
                  pre: ({ children }) => <>{children}</>,
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-4 border-blue-600 pl-4 my-4 text-slate-400 italic text-sm">
                      {children}
                    </blockquote>
                  ),
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-6">
                      <table className="w-full text-sm border-collapse border border-slate-700 rounded-lg overflow-hidden">
                        {children}
                      </table>
                    </div>
                  ),
                  thead: ({ children }) => (
                    <thead className="bg-slate-800">{children}</thead>
                  ),
                  tbody: ({ children }) => (
                    <tbody className="divide-y divide-slate-800">{children}</tbody>
                  ),
                  tr: ({ children }) => (
                    <tr className="hover:bg-slate-800/50 transition-colors">{children}</tr>
                  ),
                  th: ({ children }) => (
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="px-4 py-2.5 text-slate-300 text-xs align-top border-slate-800">
                      {children}
                    </td>
                  ),
                  hr: () => (
                    <hr className="border-slate-800 my-8" />
                  ),
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 underline underline-offset-2"
                    >
                      {children}
                    </a>
                  ),
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
