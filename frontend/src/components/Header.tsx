import { Network } from "lucide-react";

export default function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 bg-slate-900 border-b border-slate-800 flex items-center px-6">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand-600">
          <Network className="w-4 h-4 text-white" />
        </div>
        <span className="text-base font-semibold text-slate-100 tracking-tight">
          Ontology Graph Studio
        </span>
      </div>
      <div className="ml-auto flex items-center gap-2 text-xs text-slate-500">
        <span className="hidden sm:block">v0.1.0</span>
      </div>
    </header>
  );
}
