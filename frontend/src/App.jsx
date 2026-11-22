import React, { useState, useEffect } from 'react';
import {
  Search,
  Sparkles,
  FileText,
  Folder,
  ExternalLink,
  Eye,
  Settings,
  HardDrive,
  Copy,
  Check,
  Filter,
  FileSpreadsheet,
  Presentation,
  Image as ImageIcon,
  FileCode,
  X,
  Clock,
  Layers
} from 'lucide-react';
import IndexingDashboard from './components/IndexingDashboard';
import SettingsView from './components/SettingsView';
import PreviewModal from './components/PreviewModal';

const CATEGORIES = [
  { id: 'all', label: 'All Files', icon: Layers },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'presentations', label: 'Presentations', icon: Presentation },
  { id: 'spreadsheets', label: 'Spreadsheets', icon: FileSpreadsheet },
  { id: 'images', label: 'Images', icon: ImageIcon },
  { id: 'structured_data', label: 'Structured', icon: FileCode }
];

const SEARCH_EXAMPLES = [
  'Find the document containing information about decision trees.',
  'Find the presentation discussing neural networks.',
  'Find the spreadsheet containing employee salary details.',
  'Find the PDF about database normalization and ACID properties.',
  'Find the document discussing system design and load balancing.'
];

export default function App() {
  const [activeTab, setActiveTab] = useState('search'); // 'search' | 'dashboard' | 'settings'
  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [results, setResults] = useState([]);
  const [totalResults, setTotalResults] = useState(0);
  const [duration, setDuration] = useState(0);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [previewFileId, setPreviewFileId] = useState(null);
  const [copiedPath, setCopiedPath] = useState(null);
  const [notification, setNotification] = useState(null);
  const [systemStats, setSystemStats] = useState(null);

  // Poll stats for status badge
  useEffect(() => {
    fetch('/api/stats')
      .then((r) => r.json())
      .then(setSystemStats)
      .catch(() => {});
  }, []);

  const showNotification = (msg, isError = false) => {
    setNotification({ msg, isError });
    setTimeout(() => setNotification(null), 3000);
  };

  const handleSearch = (overrideQuery) => {
    const q = overrideQuery !== undefined ? overrideQuery : query;
    if (!q.trim()) return;

    setLoading(true);
    setHasSearched(true);

    const payload = {
      query: q.trim(),
      category: selectedCategory === 'all' ? null : selectedCategory,
      top_k: 25,
      min_score: 0.15
    };

    fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then((r) => {
        if (!r.ok) throw new Error('Search failed');
        return r.json();
      })
      .then((data) => {
        setResults(data.results || []);
        setTotalResults(data.total_results || 0);
        setDuration(data.duration_ms || 0);
      })
      .catch((err) => {
        showNotification(err.message, true);
      })
      .finally(() => setLoading(false));
  };

  const handleOpenFile = (filePathOrId) => {
    // If it's an object with file_id
    const id = typeof filePathOrId === 'number' ? filePathOrId : null;
    const url = id ? `/api/files/${id}/open` : `/api/files/${encodeURIComponent(filePathOrId)}/open`;

    fetch(url, { method: 'POST' })
      .then((r) => r.json())
      .then((d) => {
        if (d.success) {
          showNotification(d.message || 'Opened file in default application');
        } else {
          showNotification(d.error || 'Could not open file', true);
        }
      })
      .catch((err) => showNotification(err.message, true));
  };

  const handleOpenFolder = (filePathOrId) => {
    const id = typeof filePathOrId === 'number' ? filePathOrId : null;
    const url = id
      ? `/api/files/${id}/open-location`
      : `/api/files/${encodeURIComponent(filePathOrId)}/open-location`;

    fetch(url, { method: 'POST' })
      .then((r) => r.json())
      .then((d) => {
        if (d.success) {
          showNotification('Opened containing folder in Explorer');
        } else {
          showNotification(d.error || 'Could not open folder', true);
        }
      })
      .catch((err) => showNotification(err.message, true));
  };

  const handleCopyPath = (path) => {
    navigator.clipboard.writeText(path);
    setCopiedPath(path);
    showNotification('File path copied to clipboard');
    setTimeout(() => setCopiedPath(null), 2000);
  };

  const getFileIcon = (ext) => {
    ext = (ext || '').toLowerCase();
    if (['.pdf', '.docx', '.doc', '.txt', '.md', '.rtf'].includes(ext)) return FileText;
    if (['.pptx', '.ppt', '.odp'].includes(ext)) return Presentation;
    if (['.xlsx', '.xls', '.csv', '.ods'].includes(ext)) return FileSpreadsheet;
    if (['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'].includes(ext)) return ImageIcon;
    return FileCode;
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0b0f17] text-slate-100">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl border text-xs font-medium flex items-center space-x-2 animate-in slide-in-from-bottom duration-200 ${
            notification.isError
              ? 'bg-rose-950/90 text-rose-200 border-rose-800'
              : 'bg-slate-900/95 text-sky-200 border-sky-500/30'
          }`}
        >
          <span>{notification.msg}</span>
        </div>
      )}

      {/* Top Header & Navigation */}
      <header className="sticky top-0 z-40 border-b border-slate-800/80 glass-panel bg-[#0b0f17]/90">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo Branding */}
          <div
            onClick={() => setActiveTab('search')}
            className="flex items-center space-x-3 cursor-pointer group"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-500 via-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20 group-hover:scale-105 transition-transform">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="font-extrabold text-lg tracking-wider text-white">LENS</span>
                <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
                  AI Discovery
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-medium">Semantic Local File Retrieval</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center space-x-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('search')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === 'search'
                  ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search</span>
            </button>

            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === 'dashboard'
                  ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <HardDrive className="w-3.5 h-3.5" />
              <span>Indexing</span>
              {systemStats && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] text-slate-300 font-mono">
                  {systemStats.indexed_files}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('settings')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === 'settings'
                  ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Settings className="w-3.5 h-3.5" />
              <span>Settings</span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main View Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        {activeTab === 'dashboard' && <IndexingDashboard />}
        {activeTab === 'settings' && <SettingsView />}

        {activeTab === 'search' && (
          <div className="space-y-8 animate-in fade-in duration-300">
            {/* Search Hero Box */}
            <div className="flex flex-col items-center justify-center pt-4 pb-2 text-center max-w-2xl mx-auto space-y-3">
              <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
                Describe the content you remember.
              </h1>
              <p className="text-sm text-slate-400">
                Natural-language retrieval across documents, slides, spreadsheets, and images without remembering filenames or folder locations.
              </p>
            </div>

            {/* Input Bar */}
            <div className="max-w-3xl mx-auto">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSearch();
                }}
                className="relative flex items-center"
              >
                <div className="absolute left-4 text-sky-400">
                  <Search className="w-5 h-5" />
                </div>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. Find the document containing details about decision trees..."
                  className="w-full pl-12 pr-28 py-3.5 text-sm rounded-2xl glass-input text-white placeholder-slate-500 shadow-2xl focus:shadow-sky-500/10"
                />
                {query && (
                  <button
                    type="button"
                    onClick={() => {
                      setQuery('');
                      setResults([]);
                      setHasSearched(false);
                    }}
                    className="absolute right-20 p-1 text-slate-400 hover:text-white transition"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
                <button
                  type="submit"
                  disabled={loading || !query.trim()}
                  className="absolute right-2.5 px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 disabled:opacity-40 rounded-xl shadow-md shadow-sky-500/20 transition"
                >
                  {loading ? 'Searching...' : 'Search'}
                </button>
              </form>

              {/* Category Filter Pills */}
              <div className="flex items-center space-x-2 mt-4 overflow-x-auto pb-1 scrollbar-none justify-center">
                {CATEGORIES.map((cat) => {
                  const Icon = cat.icon;
                  const isActive = selectedCategory === cat.id;
                  return (
                    <button
                      key={cat.id}
                      onClick={() => {
                        setSelectedCategory(cat.id);
                        if (query.trim()) {
                          setTimeout(() => handleSearch(), 50);
                        }
                      }}
                      className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition whitespace-nowrap ${
                        isActive
                          ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
                          : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{cat.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Quick Suggestions Chips */}
              {!hasSearched && (
                <div className="mt-8 space-y-2.5">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 text-center">
                    Try searching:
                  </p>
                  <div className="flex flex-wrap gap-2 justify-center">
                    {SEARCH_EXAMPLES.map((example, i) => (
                      <button
                        key={i}
                        onClick={() => {
                          setQuery(example);
                          handleSearch(example);
                        }}
                        className="text-xs px-3 py-1.5 rounded-lg bg-slate-900/60 hover:bg-slate-800/80 text-slate-300 hover:text-sky-300 border border-slate-800/80 transition text-left"
                      >
                        "{example}"
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Results Header */}
            {hasSearched && (
              <div className="flex items-center justify-between text-xs text-slate-400 border-b border-slate-800 pb-3">
                <span>
                  Found <strong className="text-white">{totalResults}</strong> matching original{' '}
                  {totalResults === 1 ? 'file' : 'files'}
                </span>
                <span className="font-mono text-slate-500 flex items-center space-x-1">
                  <Clock className="w-3 h-3" />
                  <span>{duration} ms</span>
                </span>
              </div>
            )}

            {/* Loading Spinner */}
            {loading && (
              <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                <div className="w-8 h-8 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mb-3"></div>
                <p className="text-xs font-medium">Scanning semantic vector index...</p>
              </div>
            )}

            {/* No Results Empty State */}
            {!loading && hasSearched && results.length === 0 && (
              <div className="text-center py-16 space-y-3 max-w-md mx-auto">
                <div className="w-12 h-12 rounded-2xl bg-slate-800/60 flex items-center justify-center mx-auto text-slate-500">
                  <Search className="w-6 h-6" />
                </div>
                <h3 className="text-base font-semibold text-white">No matching files found</h3>
                <p className="text-xs text-slate-400">
                  Try rephrasing your search query, selecting "All Files" category, or ensure your
                  folders have been indexed in the Indexing tab.
                </p>
              </div>
            )}

            {/* Results Cards List */}
            {!loading && results.length > 0 && (
              <div className="space-y-4">
                {results.map((item) => {
                  const FileIcon = getFileIcon(item.extension);
                  const matchPercent = Math.min(Math.round(item.relevance_score * 100), 100);

                  return (
                    <div
                      key={item.file_id}
                      className="p-5 rounded-2xl glass-card border border-slate-800/80 space-y-3.5 group hover:border-slate-700/80"
                    >
                      {/* Top Bar of Card */}
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start space-x-3 overflow-hidden">
                          <div className="p-2.5 rounded-xl bg-slate-800/80 text-sky-400 border border-slate-700/60 flex-shrink-0 group-hover:scale-105 transition-transform">
                            <FileIcon className="w-5 h-5" />
                          </div>
                          <div className="overflow-hidden">
                            <h3 className="text-base font-bold text-white hover:text-sky-300 transition truncate cursor-pointer"
                              onClick={() => setPreviewFileId(item.file_id)}
                            >
                              {item.file_name}
                            </h3>
                            <div className="flex items-center space-x-2 text-xs text-slate-400 mt-0.5">
                              <span className="font-mono truncate max-w-md" title={item.file_path}>
                                {item.file_path}
                              </span>
                              <button
                                onClick={() => handleCopyPath(item.file_path)}
                                className="text-slate-500 hover:text-slate-300 transition"
                                title="Copy path"
                              >
                                {copiedPath === item.file_path ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5" />
                                )}
                              </button>
                            </div>
                          </div>
                        </div>

                        {/* Relevance Badge */}
                        <div className="flex items-center space-x-2 flex-shrink-0">
                          <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                            {matchPercent}% Match
                          </span>
                        </div>
                      </div>

                      {/* Snippet Area with Source Citation Tag */}
                      <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/70 space-y-1.5">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-semibold px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30">
                            Location: {item.primary_source}
                          </span>
                          <span className="text-slate-500 capitalize">{item.category}</span>
                        </div>
                        <p className="text-xs text-slate-200 leading-relaxed font-sans whitespace-pre-wrap">
                          {item.primary_snippet}
                        </p>
                      </div>

                      {/* Bottom Action Buttons */}
                      <div className="flex items-center justify-between pt-1 text-xs">
                        <div className="text-slate-500 text-[11px]">
                          Size: {(item.file_size_bytes / 1024).toFixed(1)} KB
                        </div>

                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => setPreviewFileId(item.file_id)}
                            className="flex items-center space-x-1.5 px-3 py-1.5 text-slate-300 hover:text-white bg-slate-800/70 hover:bg-slate-700/80 rounded-lg border border-slate-700/50 transition font-medium"
                          >
                            <Eye className="w-3.5 h-3.5 text-sky-400" />
                            <span>Preview</span>
                          </button>

                          <button
                            onClick={() => handleOpenFolder(item.file_id)}
                            className="flex items-center space-x-1.5 px-3 py-1.5 text-slate-300 hover:text-white bg-slate-800/70 hover:bg-slate-700/80 rounded-lg border border-slate-700/50 transition font-medium"
                          >
                            <Folder className="w-3.5 h-3.5 text-amber-400" />
                            <span>Containing Folder</span>
                          </button>

                          <button
                            onClick={() => handleOpenFile(item.file_id)}
                            className="flex items-center space-x-1.5 px-3.5 py-1.5 text-white bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 rounded-lg shadow-sm shadow-sky-500/20 transition font-semibold"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            <span>Open File</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Preview Modal */}
      {previewFileId && (
        <PreviewModal
          fileId={previewFileId}
          onClose={() => setPreviewFileId(null)}
          onOpenFile={(path) => handleOpenFile(path || previewFileId)}
          onOpenLocation={(path) => handleOpenFolder(path || previewFileId)}
        />
      )}
    </div>
  );
}
