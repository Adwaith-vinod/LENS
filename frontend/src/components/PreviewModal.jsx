import React, { useState, useEffect } from 'react';
import { X, ExternalLink, Folder, FileText, Check, AlertCircle } from 'lucide-react';

export default function PreviewModal({ fileId, onClose, onOpenFile, onOpenLocation }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!fileId) return;
    setLoading(true);
    fetch(`/api/files/${fileId}/preview`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load file preview');
        return res.json();
      })
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [fileId]);

  if (!fileId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[85vh] flex flex-col rounded-2xl glass-panel bg-[#0f172a]/95 border border-slate-700/60 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60">
          <div className="flex items-center space-x-3 overflow-hidden">
            <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <FileText className="w-5 h-5" />
            </div>
            <div className="overflow-hidden">
              <h3 className="text-lg font-semibold text-white truncate">
                {data?.file?.file_name || 'Loading preview...'}
              </h3>
              <p className="text-xs text-slate-400 font-mono truncate max-w-xl">
                {data?.file?.file_path || ''}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {loading && (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <div className="w-8 h-8 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mb-3"></div>
              <p className="text-sm">Reading document content...</p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          {data && (
            <>
              {/* Metadata Badges */}
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 font-medium border border-slate-700">
                  Type: {data.file.extension.toUpperCase()}
                </span>
                <span className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 font-medium border border-slate-700">
                  Category: {data.file.category}
                </span>
                <span className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 font-medium border border-slate-700">
                  Size: {(data.file.file_size_bytes / 1024).toFixed(1)} KB
                </span>
                <span className="px-2.5 py-1 rounded-md bg-sky-500/10 text-sky-300 font-medium border border-sky-500/20">
                  {data.chunks.length} Extracted Chunks
                </span>
              </div>

              {/* Chunks List */}
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Extracted Sections & Context
                </h4>
                {data.chunks.map((c, i) => (
                  <div
                    key={c.id || i}
                    className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30">
                        {c.source_info || `Section ${c.unit_number}`}
                      </span>
                      <span className="text-[11px] text-slate-500 font-mono">
                        Chunk #{c.chunk_index + 1}
                      </span>
                    </div>
                    <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
                      {c.chunk_text}
                    </p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-900/80">
          <button
            onClick={() => onOpenLocation(data?.file?.file_path)}
            className="flex items-center space-x-2 px-3 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 rounded-lg transition"
          >
            <Folder className="w-4 h-4 text-amber-400" />
            <span>Open Containing Folder</span>
          </button>

          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white transition"
            >
              Close
            </button>
            <button
              onClick={() => onOpenFile(data?.file?.file_path)}
              className="flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 rounded-lg shadow-lg shadow-sky-500/20 transition"
            >
              <ExternalLink className="w-4 h-4" />
              <span>Open Original File</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
