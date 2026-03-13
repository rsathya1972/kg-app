import { GitBranch } from "lucide-react";

export default function OntologyPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-800">
          <GitBranch className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Ontology</h1>
          <p className="text-slate-500 text-sm">Define classes, properties, and constraints</p>
        </div>
      </div>

      <div className="card flex flex-col items-center justify-center gap-4 py-20 border-dashed">
        <GitBranch className="w-10 h-10 text-slate-600" />
        <div className="text-center">
          <p className="text-slate-300 font-medium">Ontology editor coming soon</p>
          <p className="text-slate-500 text-sm mt-1">
            Define OWL/RDFS classes, object properties, data properties, and axioms.
          </p>
        </div>
        <span className="badge bg-slate-800 text-slate-400 border border-slate-700">
          Coming Soon
        </span>
      </div>
    </div>
  );
}
