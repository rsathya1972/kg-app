import { Upload } from "lucide-react";

export default function UploadPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-800">
          <Upload className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Upload Documents</h1>
          <p className="text-slate-500 text-sm">Ingest PDFs, Word docs, and plain text</p>
        </div>
      </div>

      <div className="card flex flex-col items-center justify-center gap-4 py-20 border-dashed">
        <Upload className="w-10 h-10 text-slate-600" />
        <div className="text-center">
          <p className="text-slate-300 font-medium">Document upload coming soon</p>
          <p className="text-slate-500 text-sm mt-1">
            This module will support PDF, DOCX, TXT, and markdown ingestion.
          </p>
        </div>
        <span className="badge bg-slate-800 text-slate-400 border border-slate-700">
          Coming Soon
        </span>
      </div>
    </div>
  );
}
