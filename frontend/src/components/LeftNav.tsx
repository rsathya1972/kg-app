"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  Upload,
  Cpu,
  GitBranch,
  Globe,
  Search,
  ShieldCheck,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/upload", label: "Upload Documents", icon: Upload },
  { href: "/extract", label: "Extract Entities", icon: Cpu },
  { href: "/ontology", label: "Ontology", icon: GitBranch },
  { href: "/graph", label: "Graph Viewer", icon: Globe },
  { href: "/query", label: "Query", icon: Search },
  { href: "/validation", label: "Validation", icon: ShieldCheck },
];

export default function LeftNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-14 left-0 bottom-0 w-56 bg-slate-900 border-r border-slate-800 flex flex-col py-4 px-3 overflow-y-auto">
      <ul className="flex flex-col gap-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <li key={href}>
              <Link
                href={href}
                className={`nav-link ${isActive ? "nav-link-active" : ""}`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>

      <div className="mt-auto pt-4 border-t border-slate-800">
        <p className="text-xs text-slate-600 px-3">Ontology Graph Studio</p>
        <p className="text-xs text-slate-700 px-3">Foundation v0.1.0</p>
      </div>
    </nav>
  );
}
