import React, { useState, useEffect } from 'react';
import { RefreshCw, Play, CheckCircle2, AlertTriangle, Layers, FileCode, Clock, HardDrive, XCircle } from 'lucide-react';
import { apiFetch } from '../api';

export default function IndexingDashboard() {
  const [stats, setStats] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');

  const fetchStatus = () => {
    apiFetch('/api/index/status')
      .then((r) => r.json())
      .then(setStatus)
      .catch(console.error);

    apiFetch('/api/stats')
      .then((r) => r.json())
      .then(setStats)
      .catch(console.error);
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleStartIndexing = () => {
    setLoading(true);
    apiFetch('/api/index/start', { method: 'POST' })
      .then((r) => r.json())
      .then((d) => {
        setMsg(d.message);
        fetchStatus();
      })
      .finally(() => setLoading(false));
  };

  const handleRescan = () => {
    setLoading(true);
    apiFetch('/api/index/rescan', { method: 'POST' })
      .then((r) => r.json())
      .then((d) => {
        setMsg(d.message);
        fetchStatus();
      })
      .finally(() => setLoading(false));
  };

  const handleCancel = () => {
    apiFetch('/api/index/cancel', { method: 'POST' })
      .then((r) => r.json())
      .then((d) => {
        setMsg(d.message);
        fetchStatus();
      })
      .catch(console.error);
  };

  const isIndexing = status?.status === 'indexing' || status?.status === 'scanning';

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-in fade-in duration-300">
      {/* Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center space-x-2">
            <HardDrive className="w-5 h-5 text-sky-400" />
            <span>File Discovery & Indexing Engine</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time status of discovered files, vector embeddings, and persistent SQLite index.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleRescan}
            disabled={isIndexing || loading}
            className="flex items-center space-x-2 px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700/80 disabled:opacity-50 rounded-xl border border-slate-700/60 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isIndexing ? 'animate-spin text-sky-400' : ''}`} />
            <span>Rescan All</span>
          </button>

          {isIndexing ? (
            <button
              onClick={handleCancel}
              className="flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-rose-200 bg-rose-600/80 hover:bg-rose-500 rounded-xl shadow-lg shadow-rose-500/20 transition"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>Cancel Indexing</span>
            </button>
          ) : (
            <button
              onClick={handleStartIndexing}
              disabled={loading}
              className="flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 disabled:opacity-50 rounded-xl shadow-lg shadow-sky-500/20 transition"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Start Indexing</span>
            </button>
          )}
        </div>
      </div>

      {/* Progress Banner */}
      {status && (
        <div className="p-5 rounded-2xl glass-panel border border-slate-700/50 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <span
                className={`inline-block w-2.5 h-2.5 rounded-full ${
                  isIndexing
                    ? 'bg-amber-400 animate-ping'
                    : status.status === 'completed'
                    ? 'bg-emerald-400'
                    : 'bg-slate-500'
                }`}
              />
              <span className="font-semibold text-slate-200 capitalize">
                Status: {status.status}
              </span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-400">{status.message}</span>
            </div>
            <span className="font-mono text-sky-400 font-semibold">
              {status.percent_complete}%
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-sky-400 to-blue-500 transition-all duration-300 ease-out"
              style={{ width: `${Math.max(status.percent_complete, isIndexing ? 4 : 0)}%` }}
            />
          </div>

          {status.current_file && (
            <p className="text-[11px] text-slate-400 font-mono truncate">
              Processing: <span className="text-slate-200">{status.current_file}</span>
            </p>
          )}
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl glass-card bg-slate-900/60 border border-slate-800">
          <div className="flex items-center space-x-2 text-slate-400 text-xs font-medium mb-1">
            <Layers className="w-4 h-4 text-sky-400" />
            <span>Total Discovered</span>
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {stats?.total_files ?? 0}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Files found across scan paths</p>
        </div>

        <div className="p-4 rounded-xl glass-card bg-slate-900/60 border border-slate-800">
          <div className="flex items-center space-x-2 text-emerald-400 text-xs font-medium mb-1">
            <CheckCircle2 className="w-4 h-4" />
            <span>Indexed Files</span>
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {stats?.indexed_files ?? 0}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Processed into vector store</p>
        </div>

        <div className="p-4 rounded-xl glass-card bg-slate-900/60 border border-slate-800">
          <div className="flex items-center space-x-2 text-indigo-400 text-xs font-medium mb-1">
            <FileCode className="w-4 h-4" />
            <span>Total Chunks</span>
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {stats?.total_chunks ?? 0}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Vectorized units in FAISS</p>
        </div>

        <div className="p-4 rounded-xl glass-card bg-slate-900/60 border border-slate-800">
          <div className="flex items-center space-x-2 text-amber-400 text-xs font-medium mb-1">
            <AlertTriangle className="w-4 h-4" />
            <span>Unreadable / Empty</span>
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {stats?.failed_files ?? 0}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Protected from crashing</p>
        </div>
      </div>

      {/* Category Breakdown */}
      {stats?.categories && Object.keys(stats.categories).length > 0 && (
        <div className="p-5 rounded-2xl glass-card border border-slate-800">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            Indexed Files by Category
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(stats.categories).map(([category, count]) => (
              <div
                key={category}
                className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800/80"
              >
                <span className="text-xs font-medium text-slate-300 capitalize">{category}</span>
                <span className="text-xs font-bold text-sky-400 font-mono px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/20">
                  {count}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timestamp */}
      {stats?.last_index_time && (
        <div className="flex items-center space-x-2 text-xs text-slate-500 font-mono">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>Last indexed: {new Date(stats.last_index_time).toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}
