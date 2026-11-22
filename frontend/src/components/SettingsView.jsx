import React, { useState, useEffect } from 'react';
import { Settings, FolderPlus, Trash2, Save, Check, HardDrive, ShieldCheck } from 'lucide-react';
import { apiFetch } from '../api';

export default function SettingsView() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);
  const [newDir, setNewDir] = useState('');
  const [systemDrives, setSystemDrives] = useState([]);

  useEffect(() => {
    apiFetch('/api/config')
      .then((r) => r.json())
      .then((c) => {
        setConfig(c);
        setLoading(false);
      });

    apiFetch('/api/system/drives')
      .then((r) => r.json())
      .then((d) => setSystemDrives(d.drives || []))
      .catch(console.error);
  }, []);

  const handleAddDir = () => {
    if (!newDir.trim() || !config) return;
    if (config.included_directories.includes(newDir.trim())) return;
    setConfig({
      ...config,
      included_directories: [...config.included_directories, newDir.trim()]
    });
    setNewDir('');
  };

  const handleRemoveDir = (dirToRemove) => {
    setConfig({
      ...config,
      included_directories: config.included_directories.filter((d) => d !== dirToRemove)
    });
  };

  const handleSave = () => {
    apiFetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    })
      .then((r) => r.json())
      .then(() => {
        setSaved(true);
        setTimeout(() => setSaved(false), 2500);
      });
  };

  if (loading || !config) {
    return <div className="p-8 text-center text-slate-400">Loading settings...</div>;
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto animate-in fade-in duration-300">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center space-x-2">
            <Settings className="w-5 h-5 text-sky-400" />
            <span>Search & Indexing Preferences</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Configure scan directories, exclusion policies, chunking parameters, and local storage.
          </p>
        </div>
        <button
          onClick={handleSave}
          className="flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 rounded-xl shadow-lg shadow-sky-500/20 transition"
        >
          {saved ? <Check className="w-4 h-4 text-emerald-200" /> : <Save className="w-4 h-4" />}
          <span>{saved ? 'Saved!' : 'Save Preferences'}</span>
        </button>
      </div>

      {/* Included Directories */}
      <div className="p-5 rounded-2xl glass-card border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
            <HardDrive className="w-4 h-4 text-sky-400" />
            <span>Included Directories for Discovery</span>
          </h3>
          <span className="text-[11px] text-slate-400">
            {config.included_directories.length} folders configured
          </span>
        </div>

        <div className="space-y-2">
          {config.included_directories.map((dir, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/70 border border-slate-800/80 font-mono text-xs text-slate-200"
            >
              <span className="truncate max-w-lg">{dir}</span>
              <button
                onClick={() => handleRemoveDir(dir)}
                className="p-1 text-slate-500 hover:text-rose-400 transition"
                title="Remove directory"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>

        {/* Add Directory Input */}
        <div className="flex items-center space-x-2 pt-2">
          <input
            type="text"
            value={newDir}
            onChange={(e) => setNewDir(e.target.value)}
            placeholder="Enter custom absolute directory path (e.g. C:\Users\adwai\Documents)..."
            className="flex-1 px-3.5 py-2 text-xs rounded-xl glass-input text-white placeholder-slate-500 font-mono"
            onKeyDown={(e) => e.key === 'Enter' && handleAddDir()}
          />
          <button
            onClick={handleAddDir}
            className="flex items-center space-x-1.5 px-3.5 py-2 text-xs font-medium text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-xl transition"
          >
            <FolderPlus className="w-4 h-4 text-sky-400" />
            <span>Add Folder</span>
          </button>
        </div>

        {/* System Drives Quick Add */}
        {systemDrives.length > 0 && (
          <div className="pt-2 flex items-center space-x-2 text-xs text-slate-400">
            <span>Detected fixed drives:</span>
            {systemDrives.map((drive) => (
              <button
                key={drive}
                onClick={() => {
                  if (!config.included_directories.includes(drive)) {
                    setConfig({
                      ...config,
                      included_directories: [...config.included_directories, drive]
                    });
                  }
                }}
                className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-sky-300 font-mono border border-slate-700 transition"
              >
                + {drive}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Chunking & Indexing Configuration */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="p-5 rounded-2xl glass-card border border-slate-800 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Intelligent Chunking Size
          </h3>
          <p className="text-xs text-slate-400">
            Maximum character length for each semantic document segment.
          </p>
          <input
            type="number"
            value={config.chunk_size}
            onChange={(e) => setConfig({ ...config, chunk_size: parseInt(e.target.value) || 500 })}
            className="w-full px-3.5 py-2 text-xs rounded-xl glass-input text-white font-mono"
          />
        </div>

        <div className="p-5 rounded-2xl glass-card border border-slate-800 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Chunk Overlap
          </h3>
          <p className="text-xs text-slate-400">
            Character overlap between neighboring sentences to preserve context.
          </p>
          <input
            type="number"
            value={config.chunk_overlap}
            onChange={(e) => setConfig({ ...config, chunk_overlap: parseInt(e.target.value) || 60 })}
            className="w-full px-3.5 py-2 text-xs rounded-xl glass-input text-white font-mono"
          />
        </div>
      </div>

      {/* Privacy Guarantee Box */}
      <div className="p-4 rounded-xl bg-sky-500/10 border border-sky-500/20 text-xs text-sky-300 flex items-center space-x-3">
        <ShieldCheck className="w-5 h-5 flex-shrink-0 text-sky-400" />
        <div>
          <span className="font-semibold text-white">Local-First & Privacy Preserving: </span>
          LENS operates 100% locally on your machine. Original files are never modified, deleted, moved, or sent to any external server.
        </div>
      </div>
    </div>
  );
}
