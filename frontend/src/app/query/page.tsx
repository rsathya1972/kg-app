import { Search } from "lucide-react";

export default function QueryPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-800">
          <Search className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Query</h1>
          <p className="text-slate-500 text-sm">Natural language and Cypher/SPARQL querying</p>
        </div>
      </div>

      <div className="card flex flex-col items-center justify-center gap-4 py-20 border-dashed">
        <Search className="w-10 h-10 text-slate-600" />
        <div className="text-center">
          <p className="text-slate-300 font-medium">Query interface coming soon</p>
          <p className="text-slate-500 text-sm mt-1">
            Ask questions in plain English or write Cypher/SPARQL directly against the graph.
          </p>
        </div>
        <span className="badge bg-slate-800 text-slate-400 border border-slate-700">
          Coming Soon
        </span>
      </div>
    </div>
  );
}
