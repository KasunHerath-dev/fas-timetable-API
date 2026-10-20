import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Calendar,
  Code2,
  Copy,
  Check,
  Share2,
  ExternalLink,
  AlertTriangle,
  ArrowLeft,
  Terminal,
  Database,
  Layers,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Globe,
  Zap,
  Shield,
  Clock,
  RefreshCw,
  HelpCircle,
  GitBranch,
  Play,
  X,
  Menu,
  Info,
  CheckCircle2,
  AlertCircle,
  Search,
} from 'lucide-react';
import { GithubIcon } from './Navbar';

// ─── Constants ─────────────────────────────────────────────────────────────
const LIVE_BASE_URL = 'https://fas-timetable-downloader-ipa1.vercel.app/api';
const GITHUB_REPO   = 'https://github.com/KasunHerath-dev/fas-timetable-downloader';
const GITHUB_DEV    = 'https://github.com/KasunHerath-dev';

export function getResolvedApiBaseUrl() {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && envUrl.trim()) {
    const trimmed = envUrl.trim().replace(/\/+$/, '');
    return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`;
  }
  if (typeof window !== 'undefined' && window.location?.origin) {
    return `${window.location.origin}/api`;
  }
  return '/api';
}

// ─── Section IDs for in-page navigation ────────────────────────────────────
const SECTIONS = [
  { id: 'overview',       label: 'Overview',               icon: Globe },
  { id: 'quickstart',     label: 'Quick Start',             icon: Zap },
  { id: 'base-url',       label: 'Base URL',                icon: Globe },
  { id: 'auth',           label: 'Authentication',          icon: Shield },
  { id: 'endpoints',      label: 'API Endpoints',           icon: Code2 },
  { id: 'explorer',       label: 'Interactive Explorer',    icon: Play },
  { id: 'schema',         label: 'Data Schema',             icon: Layers },
  { id: 'examples',       label: 'Code Examples',           icon: Terminal },
  { id: 'errors',         label: 'Error Handling',          icon: AlertTriangle },
  { id: 'freshness',      label: 'Data Freshness',          icon: RefreshCw },
  { id: 'cors',           label: 'CORS & Limits',           icon: Shield },
  { id: 'best-practices', label: 'Best Practices',          icon: CheckCircle2 },
  { id: 'openapi',        label: 'OpenAPI / Swagger',       icon: Database },
  { id: 'faq',            label: 'FAQ',                     icon: HelpCircle },
  { id: 'resources',      label: 'GitHub & Resources',      icon: GitBranch },
];

// ─── Utility ────────────────────────────────────────────────────────────────
function useCopy() {
  const [copiedId, setCopiedId] = useState(null);
  const handleCopy = useCallback(async (text, id) => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement('textarea');
        ta.value = text; document.body.appendChild(ta); ta.select();
        document.execCommand('copy'); document.body.removeChild(ta);
      }
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2500);
    } catch { /* silently fail */ }
  }, []);
  return { copiedId, handleCopy };
}

// ─── Reusable: Copy Button ──────────────────────────────────────────────────
function CopyBtn({ text, id, copiedId, handleCopy, size = 'sm', label }) {
  const active = copiedId === id;
  return (
    <button
      onClick={() => handleCopy(text, id)}
      title={`Copy ${label || 'to clipboard'}`}
      aria-label={active ? 'Copied!' : `Copy ${label || ''}`}
      className={`inline-flex items-center gap-1 font-semibold rounded transition-colors cursor-pointer ${
        size === 'xs'
          ? 'px-2 py-0.5 text-[11px]'
          : 'px-2.5 py-1 text-xs'
      } ${active
          ? 'bg-emerald-100 text-emerald-700 border border-emerald-300'
          : 'bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200'
      }`}
    >
      {active ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
      {active ? 'Copied!' : 'Copy'}
    </button>
  );
}

// ─── Reusable: Code Block ───────────────────────────────────────────────────
function CodeBlock({ code, language = 'bash', id, copiedId, handleCopy, label }) {
  return (
    <div className="relative group">
      <div className="flex items-center justify-between bg-slate-800 rounded-t-lg px-3 py-2 border-b border-slate-700">
        <span className="text-[11px] font-mono font-semibold text-slate-400 uppercase tracking-wider">
          {language}
        </span>
        <CopyBtn text={code} id={id} copiedId={copiedId} handleCopy={handleCopy} size="xs" label={label} />
      </div>
      <pre className="bg-slate-900 text-slate-100 p-4 rounded-b-lg overflow-x-auto text-xs font-mono leading-relaxed border border-slate-800 border-t-0 m-0">
        <code>{code}</code>
      </pre>
    </div>
  );
}

// ─── Reusable: HTTP Method Badge ────────────────────────────────────────────
function MethodBadge({ method }) {
  const colors = {
    GET: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    POST: 'bg-blue-100 text-blue-800 border-blue-300',
    PUT: 'bg-amber-100 text-amber-800 border-amber-300',
    DELETE: 'bg-red-100 text-red-800 border-red-300',
  };
  return (
    <span className={`inline-block font-mono font-bold text-xs px-2 py-0.5 rounded border ${colors[method] || 'bg-slate-100 text-slate-700 border-slate-300'}`}>
      {method}
    </span>
  );
}

// ─── Reusable: Endpoint Accordion ──────────────────────────────────────────
function EndpointBlock({ endpoint, defaultOpen = true, copiedId, handleCopy }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left flex items-center gap-3 px-4 sm:px-5 py-4 bg-white hover:bg-slate-50 transition-colors"
        aria-expanded={open}
      >
        <MethodBadge method={endpoint.method} />
        <code className="font-mono text-sm font-semibold text-slate-800 flex-1 truncate">
          {endpoint.path}
        </code>
        <span className="text-xs text-slate-500 hidden sm:block truncate max-w-xs">
          {endpoint.summary}
        </span>
        {open
          ? <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
          : <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />}
      </button>

      {open && (
        <div className="px-4 sm:px-6 py-5 border-t border-slate-100 bg-slate-50/40 space-y-5">
          <p className="text-sm text-slate-700">{endpoint.description}</p>

          {endpoint.params && endpoint.params.length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Parameters</h4>
              <div className="overflow-x-auto border border-slate-200 rounded-lg">
                <table className="min-w-full text-xs divide-y divide-slate-100">
                  <thead className="bg-slate-50">
                    <tr>
                      {['Name', 'In', 'Type', 'Required', 'Description'].map(h => (
                        <th key={h} className="px-3 py-2 text-left font-semibold text-slate-600">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-slate-50">
                    {endpoint.params.map(p => (
                      <tr key={p.name}>
                        <td className="px-3 py-2 font-mono font-semibold text-brand-700">{p.name}</td>
                        <td className="px-3 py-2 text-slate-500">{p.in}</td>
                        <td className="px-3 py-2 font-mono text-slate-600">{p.type}</td>
                        <td className="px-3 py-2">
                          {p.required
                            ? <span className="text-red-600 font-semibold">yes</span>
                            : <span className="text-slate-400">no</span>}
                        </td>
                        <td className="px-3 py-2 text-slate-700">{p.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Response (200 OK)</h4>
            <div className="relative">
              <div className="flex items-center justify-between bg-slate-800 rounded-t-lg px-3 py-2 border-b border-slate-700">
                <span className="text-[11px] font-mono font-semibold text-slate-400 uppercase tracking-wider">json</span>
                <CopyBtn
                  text={JSON.stringify(endpoint.exampleResponse, null, 2)}
                  id={`resp-${endpoint.path}`}
                  copiedId={copiedId}
                  handleCopy={handleCopy}
                  size="xs"
                  label="response"
                />
              </div>
              <pre className="bg-slate-900 text-slate-100 p-4 rounded-b-lg overflow-x-auto text-xs font-mono leading-relaxed border border-slate-800 border-t-0 m-0">
                <code>{JSON.stringify(endpoint.exampleResponse, null, 2)}</code>
              </pre>
            </div>
          </div>

          {endpoint.errorCodes && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Error Responses</h4>
              <div className="flex flex-wrap gap-2">
                {endpoint.errorCodes.map(e => (
                  <div key={e.code} className="flex items-center gap-1.5 bg-red-50 border border-red-200 rounded-lg px-2.5 py-1.5 text-xs">
                    <span className="font-bold text-red-700">{e.code}</span>
                    <span className="text-red-800">—</span>
                    <span className="text-red-700">{e.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Example cURL</h4>
            <CodeBlock
              code={endpoint.curlExample}
              language="bash"
              id={`curl-${endpoint.path}`}
              copiedId={copiedId}
              handleCopy={handleCopy}
              label="cURL"
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Interactive Explorer ───────────────────────────────────────────────────
const EXPLORER_ENDPOINTS = [
  {
    id: 'health',
    label: 'GET /health',
    buildUrl: (_p, _q) => `${LIVE_BASE_URL}/health`,
    params: [],
    queryParams: [],
  },
  {
    id: 'timetables',
    label: 'GET /timetables',
    buildUrl: (_p, q) => {
      const u = new URL(`${LIVE_BASE_URL}/timetables`);
      if (q.level) u.searchParams.set('level', q.level);
      return u.toString();
    },
    params: [],
    queryParams: [{ key: 'level', placeholder: '1–4 (optional)', hint: 'Filter by academic level' }],
  },
  {
    id: 'sessions',
    label: 'GET /timetables/{level}/sessions',
    buildUrl: (p, q) => {
      const u = new URL(`${LIVE_BASE_URL}/timetables/${p.level || '1'}/sessions`);
      if (q.academicYear) u.searchParams.set('academicYear', q.academicYear);
      if (q.semester) u.searchParams.set('semester', q.semester);
      if (q.day) u.searchParams.set('day', q.day);
      if (q.subjectCode) u.searchParams.set('subjectCode', q.subjectCode);
      return u.toString();
    },
    params: [{ key: 'level', placeholder: '1', hint: 'Academic level (1–4)' }],
    queryParams: [
      { key: 'academicYear', placeholder: '2024/2025 (optional)' },
      { key: 'semester', placeholder: 'Semester I (optional)' },
      { key: 'day', placeholder: 'Friday (optional)' },
      { key: 'subjectCode', placeholder: 'CMIS (optional)' },
    ],
  },
  {
    id: 'status',
    label: 'GET /timetables/{level}/status',
    buildUrl: (p, q) => {
      const u = new URL(`${LIVE_BASE_URL}/timetables/${p.level || '1'}/status`);
      if (q.academicYear) u.searchParams.set('academicYear', q.academicYear);
      if (q.semester) u.searchParams.set('semester', q.semester);
      return u.toString();
    },
    params: [{ key: 'level', placeholder: '1', hint: 'Academic level (1–4)' }],
    queryParams: [
      { key: 'academicYear', placeholder: '2024/2025 (optional)' },
      { key: 'semester', placeholder: 'Semester I (optional)' },
    ],
  },
];

function InteractiveExplorer({ copiedId, handleCopy }) {
  const [selected, setSelected] = useState(EXPLORER_ENDPOINTS[0]);
  const [pathParams, setPathParams] = useState({});
  const [queryParams, setQueryParams] = useState({});
  const [result, setResult] = useState(null); // {url, status, statusText, data, error, loading}

  const builtUrl = selected.buildUrl(pathParams, queryParams);

  const handleRun = async () => {
    setResult({ loading: true, url: builtUrl });
    const start = Date.now();
    try {
      const res = await fetch(builtUrl, {
        headers: { Accept: 'application/json' },
        mode: 'cors',
      });
      const text = await res.text();
      const elapsed = Date.now() - start;
      let parsed;
      try { parsed = JSON.parse(text); } catch { parsed = text; }
      setResult({
        url: builtUrl,
        status: res.status,
        statusText: res.statusText,
        data: typeof parsed === 'string' ? parsed : JSON.stringify(parsed, null, 2),
        ok: res.ok,
        elapsed,
        loading: false,
      });
    } catch (err) {
      setResult({
        url: builtUrl,
        error: `Network error: ${err.message}. This may be a CORS restriction — use the cURL example instead.`,
        loading: false,
      });
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
      {/* Endpoint selector */}
      <div className="bg-slate-50 border-b border-slate-200 p-4 sm:p-5">
        <div className="flex items-center gap-2 mb-3">
          <Play className="w-4 h-4 text-brand-600" />
          <h3 className="text-sm font-bold text-slate-900">Try an Endpoint</h3>
          <span className="text-xs text-slate-500 ml-1">— requests go to the live production API</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {EXPLORER_ENDPOINTS.map(ep => (
            <button
              key={ep.id}
              onClick={() => { setSelected(ep); setPathParams({}); setQueryParams({}); setResult(null); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer ${
                selected.id === ep.id
                  ? 'bg-brand-600 text-white border-brand-600'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
              }`}
            >
              {ep.label}
            </button>
          ))}
        </div>
      </div>

      {/* Parameters */}
      <div className="p-4 sm:p-5 space-y-4">
        {(selected.params.length > 0 || selected.queryParams.length > 0) && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {selected.params.map(p => (
              <div key={p.key}>
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                  {p.key} <span className="text-red-500">*</span> <span className="font-normal normal-case text-slate-400">(path)</span>
                </label>
                <input
                  type="text"
                  placeholder={p.placeholder}
                  value={pathParams[p.key] || ''}
                  onChange={e => setPathParams(pp => ({ ...pp, [p.key]: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white font-mono"
                />
              </div>
            ))}
            {selected.queryParams.map(p => (
              <div key={p.key}>
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                  {p.key} <span className="font-normal normal-case text-slate-400">(query)</span>
                </label>
                <input
                  type="text"
                  placeholder={p.placeholder}
                  value={queryParams[p.key] || ''}
                  onChange={e => setQueryParams(qp => ({ ...qp, [p.key]: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white font-mono"
                />
              </div>
            ))}
          </div>
        )}

        {/* Built URL preview */}
        <div className="flex items-center gap-2 bg-slate-900 rounded-lg px-3 py-2.5">
          <span className="text-emerald-400 font-mono text-xs shrink-0">GET</span>
          <span className="font-mono text-xs text-slate-200 truncate flex-1">{builtUrl}</span>
          <CopyBtn text={builtUrl} id="explorer-url" copiedId={copiedId} handleCopy={handleCopy} size="xs" label="URL" />
        </div>

        <button
          onClick={handleRun}
          disabled={result?.loading}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {result?.loading
            ? <><RefreshCw className="w-4 h-4 animate-spin" />Sending…</>
            : <><Play className="w-4 h-4" />Send Request</>}
        </button>

        {/* Response panel */}
        {result && !result.loading && (
          <div className="border border-slate-200 rounded-xl overflow-hidden">
            <div className={`flex items-center justify-between px-4 py-2.5 ${
              result.error ? 'bg-red-50 border-b border-red-200' :
              result.ok ? 'bg-emerald-50 border-b border-emerald-200' :
              'bg-amber-50 border-b border-amber-200'
            }`}>
              <div className="flex items-center gap-2">
                {result.error
                  ? <AlertCircle className="w-4 h-4 text-red-600" />
                  : result.ok
                    ? <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    : <AlertTriangle className="w-4 h-4 text-amber-600" />}
                <span className={`text-xs font-bold ${
                  result.error ? 'text-red-700' : result.ok ? 'text-emerald-700' : 'text-amber-700'
                }`}>
                  {result.error ? 'Error' : `HTTP ${result.status} ${result.statusText}`}
                </span>
                {result.elapsed && <span className="text-xs text-slate-500">{result.elapsed}ms</span>}
              </div>
              {result.data && (
                <CopyBtn text={result.data} id="explorer-response" copiedId={copiedId} handleCopy={handleCopy} size="xs" label="response" />
              )}
            </div>
            <pre className="bg-slate-900 text-slate-100 p-4 overflow-x-auto text-xs font-mono leading-relaxed max-h-72">
              <code>{result.error || result.data || 'No response body'}</code>
            </pre>
          </div>
        )}

        <p className="text-[11px] text-slate-400">
          <Info className="w-3 h-3 inline mr-1" />
          Requests are sent directly to the live API. If CORS blocks the request in your browser, use the cURL example in the endpoint reference above.
        </p>
      </div>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────
export default function DeveloperDocs({ onNavigateHome, onNavigateToReadme }) {
  const { copiedId, handleCopy } = useCopy();
  const [activeSection, setActiveSection] = useState('overview');
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [activeCodeTab, setActiveCodeTab] = useState('js');
  const sectionRefs = useRef({});
  const observerRef = useRef(null);

  const apiBaseUrl = getResolvedApiBaseUrl();
  const docsPageUrl = typeof window !== 'undefined' ? `${window.location.origin}/developers` : '/developers';

  // Intersection observer for active-section tracking
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;
    observerRef.current = new IntersectionObserver(
      entries => {
        const visible = entries.filter(e => e.isIntersecting);
        if (visible.length > 0) {
          const first = visible.sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
          setActiveSection(first.target.id);
        }
      },
      { rootMargin: '-80px 0px -60% 0px', threshold: 0 }
    );
    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observerRef.current.observe(el);
    });
    return () => observerRef.current?.disconnect();
  }, []);

  const scrollTo = useCallback((id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setMobileSidebarOpen(false);
  }, []);

  // ── Endpoint definitions ────────────────────────────────────────────────
  const endpoints = [
    {
      method: 'GET',
      path: '/api/health',
      summary: 'Health check — database connectivity',
      description: 'Returns the runtime status of the FastAPI backend and its connection to MongoDB Atlas. Useful as a liveness probe before making data requests.',
      params: [],
      curlExample: `curl -X GET "${LIVE_BASE_URL}/health" \\
  -H "Accept: application/json"`,
      exampleResponse: {
        status: 'ok',
        database: 'connected',
        timestamp: '2026-10-15T20:55:45.079183+00:00',
      },
      errorCodes: [
        { code: 503, reason: 'Database unreachable — MongoDB Atlas connection failed' },
      ],
    },
    {
      method: 'GET',
      path: '/api/timetables',
      summary: 'List all available timetables with metadata',
      description: 'Returns an array of timetable metadata records for published PDF timetables. Each record contains academic term information, revision identifiers, source PDF URL, SHA-256 digest, and publication dates. Optionally filter by level (1–4).',
      params: [
        { name: 'level', in: 'query', type: 'integer (1–4)', required: false, description: 'Filter results to a specific academic level.' },
      ],
      curlExample: `# All timetables
curl -X GET "${LIVE_BASE_URL}/timetables" \\
  -H "Accept: application/json"

# Filter to Level 1 only
curl -X GET "${LIVE_BASE_URL}/timetables?level=1" \\
  -H "Accept: application/json"`,
      exampleResponse: [
        {
          id: '6ad0c57e655367c0eb0e592d',
          level: 1,
          academicYear: '2024/2025',
          semester: 'Semester I',
          revision: 'Revised 02',
          noticeTitle: 'Revised – Academic Time Table – Level 1 Semester I (Academic Year 2024/2025)',
          noticeUrl: 'https://fas.wyb.ac.lk/revised-academic-time-table-level-1-semester-i-academic-year-2024-2025/',
          sourcePdfUrl: 'https://fas.wyb.ac.lk/wp-content/uploads/2026/10/Level-1-Revesed-2.pdf',
          publishedDate: '2026-10-05',
          downloadedAt: '2026-10-15T17:33:56.807360+05:30',
          fileSize: 675037,
          sha256: '94061dc7442c115a05340835561bd164ea4024bea4226e85943c027c1e0003b7',
          updatedAt: '2026-10-15T17:52:22.327920+05:30',
        },
      ],
      errorCodes: [
        { code: 422, reason: 'Validation error — level parameter is out of range 1–4' },
        { code: 503, reason: 'Database unavailable' },
      ],
    },
    {
      method: 'GET',
      path: '/api/timetables/{level}/sessions',
      summary: 'Retrieve parsed schedule sessions for an academic level',
      description: 'Returns all parsed teaching sessions for the specified academic level. Defaults to the most recently available academic year and semester if term parameters are omitted. Supports filtering by day (Monday–Friday) and subject code prefix.',
      params: [
        { name: '{level}', in: 'path', type: 'integer (1–4)', required: true, description: 'Target academic level.' },
        { name: 'academicYear', in: 'query', type: 'string', required: false, description: 'e.g. "2024/2025". Defaults to latest available.' },
        { name: 'semester', in: 'query', type: 'string', required: false, description: 'e.g. "Semester I". Defaults to latest available.' },
        { name: 'day', in: 'query', type: 'string', required: false, description: 'One of: Monday, Tuesday, Wednesday, Thursday, Friday.' },
        { name: 'subjectCode', in: 'query', type: 'string', required: false, description: 'Case-insensitive prefix match, e.g. "CMIS" matches "CMIS 1113".' },
      ],
      curlExample: `# All sessions for Level 2 (latest term)
curl -X GET "${LIVE_BASE_URL}/timetables/2/sessions" \\
  -H "Accept: application/json"

# Friday sessions only
curl -X GET "${LIVE_BASE_URL}/timetables/2/sessions?day=Friday" \\
  -H "Accept: application/json"

# Filter by subject code prefix
curl -X GET "${LIVE_BASE_URL}/timetables/1/sessions?subjectCode=CMIS" \\
  -H "Accept: application/json"`,
      exampleResponse: {
        level: 2,
        academicYear: '2024/2025',
        semester: 'Semester I',
        day: 'Friday',
        subjectCode: null,
        totalSessions: 5,
        sessions: [
          {
            id: '6ad0fd33655367c0eb0e6585',
            timetableId: '6ad0c57f655367c0eb0e592e',
            level: 2,
            academicYear: '2024/2025',
            semester: 'Semester I',
            day: 'Friday',
            startTime: '08:30',
            endTime: '09:30',
            subjectCode: 'CMIS 2113',
            sessionType: 'Lecture',
            group: null,
            location: 'LR- 07',
            rawCellText: 'CMIS 2113 (L)\nLR- 07',
            validationStatus: 'VALID',
            warnings: [],
            sourcePdfHash: '0e872ee45891554f337d5906e1a53998b05e6cddfe55660048164bb22cffa957',
            updatedAt: '2026-10-15T21:49:59.424171+05:30',
          },
        ],
      },
      errorCodes: [
        { code: 422, reason: 'Validation error — invalid level or day value' },
        { code: 503, reason: 'Database unavailable' },
      ],
    },
    {
      method: 'GET',
      path: '/api/timetables/{level}/status',
      summary: 'Session validation counts and type breakdown for a level',
      description: 'Returns aggregate counts: total sessions, verified sessions (VALID), sessions awaiting review (NEEDS_REVIEW), and a breakdown by session type (Lecture, Practical, Tutorial, Unspecified). Defaults to the latest academic term.',
      params: [
        { name: '{level}', in: 'path', type: 'integer (1–4)', required: true, description: 'Target academic level.' },
        { name: 'academicYear', in: 'query', type: 'string', required: false, description: 'e.g. "2024/2025".' },
        { name: 'semester', in: 'query', type: 'string', required: false, description: 'e.g. "Semester I".' },
      ],
      curlExample: `curl -X GET "${LIVE_BASE_URL}/timetables/1/status" \\
  -H "Accept: application/json"`,
      exampleResponse: {
        level: 1,
        academicYear: '2024/2025',
        semester: 'Semester I',
        totalSessions: 44,
        validSessions: 40,
        needsReviewSessions: 4,
        sessionTypes: { Lecture: 21, Practical: 8, Tutorial: 8, Unspecified: 7 },
      },
      errorCodes: [
        { code: 422, reason: 'Validation error — level out of range 1–4' },
        { code: 503, reason: 'Database unavailable' },
      ],
    },
    {
      method: 'GET',
      path: '/api/academic-calendar',
      summary: 'List available academic calendars',
      description: 'Returns all available academic calendar documents and their metadata, including academic year, document revision status (approved, revised, draft), covered levels and semesters, SHA-256 fingerprint, and activity counts.',
      params: [
        { name: 'academicYear', in: 'query', type: 'string', required: false, description: 'Filter by academic year (e.g. "2024/2025" or "2024-2025").' },
        { name: 'status', in: 'query', type: 'string', required: false, description: 'Filter by document status ("approved", "revised", "draft").' },
      ],
      curlExample: `# List all academic calendars
curl -X GET "${LIVE_BASE_URL}/academic-calendar" \\
  -H "Accept: application/json"`,
      exampleResponse: [
        {
          id: 'cal_2024_2025_approved_6ca12081',
          calendarId: 'cal_2024_2025_approved_6ca12081',
          academicYear: '2024/2025',
          academicYearStart: 2024,
          academicYearEnd: 2025,
          documentTitle: 'CALENDAR OF DATES',
          documentStatus: 'approved',
          revision: 'Original',
          levels: [1, 2, 3, 4],
          semesters: ['Semester I', 'Semester II'],
          sourceUrl: 'https://fas.wyb.ac.lk/wp-content/uploads/2026/07/COD-2024-2025.pdf',
          publicationDate: '2026-07-17',
          signatureDate: '2026-07-03',
          sha256: '6ca12081e4b8948cc161e130503931060303a1982961e84c19698b80d983c964',
          validationStatus: 'VALID',
          activitiesCount: 14,
          isCurrent: true,
          isCurrentConfirmed: true,
        },
      ],
      errorCodes: [
        { code: 503, reason: 'Database service unavailable' },
      ],
    },
    {
      method: 'GET',
      path: '/api/academic-calendar/current',
      summary: 'Get authoritative current academic calendar',
      description: 'Returns the verified active official academic calendar including all structured activities, date ranges, duration labels, and confirmation metadata. If multiple conflicting documents exist or evidence is insufficient, current status is explicitly flagged as unconfirmed.',
      params: [],
      curlExample: `curl -X GET "${LIVE_BASE_URL}/academic-calendar/current" \\
  -H "Accept: application/json"`,
      exampleResponse: {
        id: 'cal_2024_2025_approved_6ca12081',
        academicYear: '2024/2025',
        documentTitle: 'CALENDAR OF DATES',
        documentStatus: 'approved',
        levels: [1, 2, 3, 4],
        semesters: ['Semester I', 'Semester II'],
        signatureDate: '2026-07-03',
        publicationDate: '2026-07-17',
        isCurrent: true,
        isCurrentConfirmed: true,
        selectionReason: 'Verified official approved calendar for Academic Year 2024/2025',
        activitiesCount: 14,
        activities: [
          {
            activity: 'Academic Session',
            category: 'academic_session',
            semester: 'Semester I',
            startDate: '2026-08-03',
            endDate: '2026-09-27',
            durationRaw: '08 Weeks',
            durationWeeks: 8.0,
            validationStatus: 'VALID',
            warnings: [],
          },
        ],
      },
      errorCodes: [
        { code: 404, reason: 'No official academic calendar found' },
        { code: 503, reason: 'Database service unavailable' },
      ],
    },
    {
      method: 'GET',
      path: '/api/academic-calendar/{academic_year}',
      summary: 'Get calendar for a specific academic year',
      description: 'Retrieves the complete academic calendar for the specified academic period. Handles both slash and hyphen notation (e.g. "2024-2025" or "2024%2F2025").',
      params: [
        { name: '{academic_year}', in: 'path', type: 'string', required: true, description: 'Academic year, e.g. "2024-2025" or "2024/2025".' },
      ],
      curlExample: `curl -X GET "${LIVE_BASE_URL}/academic-calendar/2024-2025" \\
  -H "Accept: application/json"`,
      exampleResponse: {
        academicYear: '2024/2025',
        documentTitle: 'CALENDAR OF DATES',
        documentStatus: 'approved',
        levels: [1, 2, 3, 4],
        semesters: ['Semester I', 'Semester II'],
        activitiesCount: 14,
      },
      errorCodes: [
        { code: 404, reason: 'Academic calendar not found for specified year' },
        { code: 503, reason: 'Database service unavailable' },
      ],
    },
    {
      method: 'GET',
      path: '/api/academic-calendar/{academic_year}/semesters/{semester}',
      summary: 'Get activities for a specific semester in an academic year',
      description: 'Filters schedule activities to a specific semester. Accepts canonical names ("Semester I", "Semester II") or shorthand numbers ("1", "2").',
      params: [
        { name: '{academic_year}', in: 'path', type: 'string', required: true, description: 'Academic year (e.g. "2024-2025").' },
        { name: '{semester}', in: 'path', type: 'string', required: true, description: 'Semester name (e.g. "Semester I", "Semester II", or "1").' },
      ],
      curlExample: `curl -X GET "${LIVE_BASE_URL}/academic-calendar/2024-2025/semesters/Semester%20I" \\
  -H "Accept: application/json"`,
      exampleResponse: {
        academicYear: '2024/2025',
        semester: 'Semester I',
        startDate: '2026-08-03',
        endDate: '2027-01-17',
        totalActivities: 8,
        activities: [],
      },
      errorCodes: [
        { code: 404, reason: 'Semester or academic year not found' },
        { code: 503, reason: 'Database service unavailable' },
      ],
    },
    {
      method: 'GET',
      path: '/api/academic-calendar/upcoming',
      summary: 'Get upcoming & ongoing academic activities',
      description: 'Returns scheduled activities occurring on or after a reference date (defaults to current date in Sri Lanka / Asia:Colombo). Each activity is dynamically classified as "ongoing", "upcoming", or "completed".',
      params: [
        { name: 'reference_date', in: 'query', type: 'string (YYYY-MM-DD)', required: false, description: 'Base date for upcoming filtering (defaults to today).' },
        { name: 'limit', in: 'query', type: 'integer (1–50)', required: false, description: 'Maximum activities to return (default: 10).' },
        { name: 'academicYear', in: 'query', type: 'string', required: false, description: 'Filter to specific academic year.' },
      ],
      curlExample: `# Upcoming activities from today
curl -X GET "${LIVE_BASE_URL}/academic-calendar/upcoming?limit=5" \\
  -H "Accept: application/json"

# With explicit reference date
curl -X GET "${LIVE_BASE_URL}/academic-calendar/upcoming?reference_date=2026-09-01" \\
  -H "Accept: application/json"`,
      exampleResponse: {
        referenceDate: '2026-09-01',
        academicYear: '2024/2025',
        totalUpcoming: 13,
        limit: 5,
        activities: [
          {
            activity: 'Academic Session',
            category: 'academic_session',
            semester: 'Semester I',
            startDate: '2026-08-03',
            endDate: '2026-09-27',
            durationRaw: '08 Weeks',
            durationWeeks: 8.0,
            status: 'ongoing',
          },
        ],
      },
      errorCodes: [
        { code: 404, reason: 'No active calendar found' },
        { code: 503, reason: 'Database service unavailable' },
      ],
    },
    {
      method: 'GET',
      path: '/api/academic-calendar/status',
      summary: 'Academic calendar synchronization health & audit metrics',
      description: 'Provides operational insight into official source discovery, SHA-256 change detection, validation status, confirmation state, and run timestamps.',
      params: [],
      curlExample: `curl -X GET "${LIVE_BASE_URL}/academic-calendar/status" \\
  -H "Accept: application/json"`,
      exampleResponse: {
        lastCheckedAt: '2026-10-20T12:00:00+05:30',
        lastSuccessfulSyncAt: '2026-10-20T12:00:00+05:30',
        sourcePageUrl: 'https://fas.wyb.ac.lk/timetables/academic-calendar/',
        discoverySuccess: true,
        newerDocumentDiscovered: false,
        documentAwaitingValidation: false,
        currentCalendarConfirmed: true,
        currentCalendarId: 'cal_2024_2025_approved_6ca12081',
        currentAcademicYear: '2024/2025',
        lastRunFailed: false,
        discoveredDocumentsCount: 6,
        unchangedCount: 6,
        synchronizedCount: 0,
        failedCount: 0,
        lastError: null,
      },
      errorCodes: [
        { code: 503, reason: 'Database service unavailable' },
      ],
    },
  ];

  // ── Code Examples ─────────────────────────────────────────────────────────
  const jsExample = `// JavaScript — fetch Level 2 Friday schedule
const API_BASE = '${LIVE_BASE_URL}';

async function fetchLevel2FridaySchedule() {
  const url = new URL(\`\${API_BASE}/timetables/2/sessions\`);
  url.searchParams.set('day', 'Friday');

  const response = await fetch(url.toString(), {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(
      \`HTTP \${response.status}: \${err.detail || response.statusText}\`
    );
  }

  const data = await response.json();
  console.log(\`Level 2 Friday — \${data.totalSessions} sessions (\${data.academicYear} \${data.semester})\`);

  data.sessions.forEach(session => {
    const time = \`\${session.startTime}–\${session.endTime}\`;
    const subject = session.subjectCode || 'N/A';
    const venue = session.location || 'TBA';
    console.log(\`[\${session.day}] \${time} \${subject} @ \${venue}\`);

    // Always surface NEEDS_REVIEW warnings to users
    if (session.validationStatus === 'NEEDS_REVIEW') {
      console.warn('⚠ Unverified entry:', session.warnings.join(', '));
    }
  });

  return data;
}

// JavaScript — fetch Current Official Academic Calendar
async function fetchCurrentAcademicCalendar() {
  const response = await fetch(\`\${API_BASE}/academic-calendar/current\`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw new Error(\`HTTP \${response.status}\`);
  const calendar = await response.json();
  console.log(\`Academic Calendar: \${calendar.academicYear} (\${calendar.documentStatus})\`);
  console.log(\`Confirmed: \${calendar.isCurrentConfirmed ? 'YES' : 'UNCONFIRMED'}\`);
  return calendar;
}

fetchLevel2FridaySchedule()
  .catch(err => console.error('API error:', err.message));`;

  const pyExample = `import requests

API_BASE = '${LIVE_BASE_URL}'

def get_level2_friday_sessions():
    """Fetch Level 2 Friday timetable sessions."""
    url = f"{API_BASE}/timetables/2/sessions"
    params = {'day': 'Friday'}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError("Request timed out — the API may be starting up. Retry once.")
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.response.status_code}: {exc.response.text}") from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Network error: {exc}") from exc

    data = response.json()
    print(f"Level 2 Friday — {data['totalSessions']} sessions "
          f"({data.get('academicYear')} {data.get('semester')})")

    for session in data.get('sessions', []):
        code = session.get('subjectCode') or 'N/A'
        venue = session.get('location') or 'TBA'
        stype = session.get('sessionType') or 'Session'
        print(f"  [{session['day']}] {session['startTime']}–{session['endTime']} "
              f"{code} ({stype}) @ {venue}")
        if session.get('validationStatus') == 'NEEDS_REVIEW':
            print(f"    ⚠ Unverified: {session.get('warnings')}")

    return data

def get_current_academic_calendar():
    """Fetch current official academic calendar and upcoming activities."""
    url = f"{API_BASE}/academic-calendar/current"
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    cal = res.json()
    print(f"Academic Calendar: {cal['academicYear']} ({cal['documentStatus']})")
    print(f"Confirmation: {'CONFIRMED' if cal['isCurrentConfirmed'] else 'UNCONFIRMED'}")
    return cal

if __name__ == '__main__':
    get_level2_friday_sessions()`;

  const curlExamples = `# Health check
curl -X GET "${LIVE_BASE_URL}/health" -H "Accept: application/json"

# All timetable metadata
curl -X GET "${LIVE_BASE_URL}/timetables" -H "Accept: application/json"

# Level 1 timetable metadata only
curl -X GET "${LIVE_BASE_URL}/timetables?level=1" -H "Accept: application/json"

# All sessions for Level 2 (latest term)
curl -X GET "${LIVE_BASE_URL}/timetables/2/sessions" -H "Accept: application/json"

# Level 2 Friday sessions
curl -X GET "${LIVE_BASE_URL}/timetables/2/sessions?day=Friday" -H "Accept: application/json"

# Level 1 CMIS subject sessions
curl -X GET "${LIVE_BASE_URL}/timetables/1/sessions?subjectCode=CMIS" -H "Accept: application/json"

# Level 1 session validation status
curl -X GET "${LIVE_BASE_URL}/timetables/1/status" -H "Accept: application/json"

# Academic Calendar: Current official calendar
curl -X GET "${LIVE_BASE_URL}/academic-calendar/current" -H "Accept: application/json"

# Academic Calendar: Upcoming & ongoing activities
curl -X GET "${LIVE_BASE_URL}/academic-calendar/upcoming?limit=5" -H "Accept: application/json"

# Academic Calendar: Synchronization audit status
curl -X GET "${LIVE_BASE_URL}/academic-calendar/status" -H "Accept: application/json"`;

  // ── Session field schema ─────────────────────────────────────────────────
  const sessionFields = [
    { name: 'id', type: 'string', req: true,  ex: '"6ad0fd33..."',           desc: 'Unique document identifier (MongoDB ObjectId serialized as string).' },
    { name: 'timetableId', type: 'string', req: true, ex: '"6ad0c57f..."',   desc: 'Reference to the parent timetable metadata document.' },
    { name: 'level', type: 'integer', req: true, ex: '2',                    desc: 'Academic level (1, 2, 3, or 4).' },
    { name: 'academicYear', type: 'string', req: true, ex: '"2024/2025"',    desc: 'Academic year in the form "YYYY/YYYY".' },
    { name: 'semester', type: 'string', req: true, ex: '"Semester I"',       desc: 'Semester identifier.' },
    { name: 'day', type: 'string', req: true, ex: '"Friday"',                desc: 'Weekday: Monday, Tuesday, Wednesday, Thursday, or Friday.' },
    { name: 'startTime', type: 'string', req: true, ex: '"08:30"',           desc: '24-hour normalized session start time (HH:MM).' },
    { name: 'endTime', type: 'string', req: true, ex: '"09:30"',             desc: '24-hour normalized session end time (HH:MM).' },
    { name: 'subjectCode', type: 'string | null', req: false, ex: '"CMIS 1113"', desc: 'Module or course code as printed in the timetable PDF.' },
    { name: 'sessionType', type: 'string | null', req: false, ex: '"Lecture"', desc: 'Teaching format: Lecture, Practical, Tutorial, Other, or null if the PDF cell lacked a type annotation.' },
    { name: 'group', type: 'string | null', req: false, ex: '"Gp. I"',       desc: 'Practical or lab group label, if designated (e.g. Gp. I, Gp. II). Null for lectures and tutorials.' },
    { name: 'location', type: 'string | null', req: false, ex: '"LR- 07"',  desc: 'Classroom, lab, or venue as extracted from the PDF. Null if unspecified.' },
    { name: 'rawCellText', type: 'string', req: true, ex: '"CMIS 1113 (L)\\nLR- 07"', desc: 'Verbatim text extracted from the PDF grid cell, including newlines. Useful for debugging parsing discrepancies.' },
    { name: 'validationStatus', type: 'string', req: true, ex: '"VALID"',    desc: '"VALID" or "NEEDS_REVIEW". NEEDS_REVIEW means the parser found ambiguous or non-standard content.' },
    { name: 'warnings', type: 'string[]', req: true, ex: '["Unusual character..."]', desc: 'Parser diagnostic messages explaining why the session is flagged. Empty array for VALID sessions.' },
    { name: 'sourcePdfHash', type: 'string', req: true, ex: '"0e872ee4..."', desc: 'SHA-256 digest of the source PDF at extraction time. Changes when a revised PDF is published.' },
    { name: 'updatedAt', type: 'string (ISO 8601)', req: true, ex: '"2026-10-15T21:49:59..."', desc: 'UTC timestamp of the last database write for this document.' },
  ];

  const timetableFields = [
    { name: 'id', type: 'string', req: true, ex: '"6ad0c57e..."',            desc: 'Document identifier (MongoDB ObjectId).' },
    { name: 'level', type: 'integer', req: true, ex: '1',                    desc: 'Academic level (1–4).' },
    { name: 'academicYear', type: 'string', req: true, ex: '"2024/2025"',    desc: 'Academic year.' },
    { name: 'semester', type: 'string', req: true, ex: '"Semester I"',       desc: 'Semester identifier.' },
    { name: 'revision', type: 'string', req: true, ex: '"Revised 02"',       desc: 'Revision label extracted from the notice title.' },
    { name: 'noticeTitle', type: 'string', req: true, ex: '"Revised – Academic Time Table..."', desc: 'Full title of the faculty notice that contained this PDF.' },
    { name: 'noticeUrl', type: 'string (URL)', req: true, ex: '"https://fas.wyb.ac.lk/..."', desc: 'Link to the original faculty notice page.' },
    { name: 'sourcePdfUrl', type: 'string (URL)', req: true, ex: '"https://fas.wyb.ac.lk/..."', desc: 'Direct URL to the source timetable PDF.' },
    { name: 'publishedDate', type: 'string (YYYY-MM-DD)', req: true, ex: '"2026-10-05"', desc: 'Date the notice was published on the faculty website.' },
    { name: 'downloadedAt', type: 'string (ISO 8601)', req: true, ex: '"2026-10-15T17:33:56..."', desc: 'Timestamp when the worker downloaded the PDF for processing.' },
    { name: 'fileSize', type: 'integer', req: true, ex: '675037',            desc: 'PDF file size in bytes.' },
    { name: 'sha256', type: 'string', req: true, ex: '"94061dc7..."',        desc: 'SHA-256 digest of the source PDF. Used for change detection.' },
    { name: 'updatedAt', type: 'string (ISO 8601)', req: true, ex: '"2026-10-15T17:52:22..."', desc: 'Last MongoDB document update timestamp.' },
  ];

  // ── FAQ ───────────────────────────────────────────────────────────────────
  const faqs = [
    {
      q: 'Do I need an API key or authentication?',
      a: 'No. The API is publicly accessible over HTTPS. No API key, token, or authentication header is required for any endpoint. All endpoints are read-only.',
    },
    {
      q: 'Can I retrieve sessions for all 4 levels in a single request?',
      a: 'No. Sessions are organized by level. To retrieve all levels, make four separate requests: /api/timetables/1/sessions through /api/timetables/4/sessions. You can run these requests concurrently with Promise.all().',
    },
    {
      q: 'What does NEEDS_REVIEW mean?',
      a: 'The parser found non-standard content in the source PDF — for example an unusual subject code like "ELPC 2+20" that contains a "+" character, or a cell that lacked a session-type annotation. These sessions are retained with their rawCellText unchanged so that no data is silently discarded. Always display a warning badge for NEEDS_REVIEW sessions and advise users to verify with their department.',
    },
    {
      q: 'How often is the data updated?',
      a: 'A GitHub Actions workflow runs daily at 00:00 UTC (05:30 Sri Lanka time). It checks the FAS WUSL timetable notices page for new or revised PDFs. If a PDF\'s SHA-256 hash matches what is already stored, no database write occurs. If a new revision is detected, sessions are re-parsed and the database is updated atomically.',
    },
    {
      q: 'Is the API rate-limited?',
      a: 'No explicit rate limit is configured. The API is hosted on Vercel\'s serverless infrastructure, which has its own usage tiers. The API is intended for student applications. Please do not hammer it with high-frequency polling — implement a client-side cache instead.',
    },
    {
      q: 'How do I request sessions for a specific academic term that is not the latest?',
      a: 'Pass academicYear and semester as query parameters, e.g. ?academicYear=2024/2025&semester=Semester+I. First call /api/timetables to discover which academic terms are available.',
    },
    {
      q: 'Is there a Swagger UI or OpenAPI schema?',
      a: 'FastAPI generates an OpenAPI spec at /openapi.json and a Swagger UI at /docs. However, the Vercel deployment routes all non-API paths to the frontend SPA, so /docs resolves to the React app rather than Swagger. The OpenAPI schema is accessible at https://fas-timetable-downloader-ipa1.vercel.app/openapi.json (served by the FastAPI serverless function), though this is not guaranteed to remain stable across deployments.',
    },
    {
      q: 'Why are some localPath values visible in timetable metadata?',
      a: 'The localPath field reflects the path used during the worker\'s temporary download. It is a known issue that this field is persisted to MongoDB rather than being cleared to null after processing. This is an internal artifact and not meaningful for API consumers — you should ignore it.',
    },
  ];

  // ── Sidebar ───────────────────────────────────────────────────────────────
  const SidebarNav = () => (
    <nav aria-label="Documentation sections">
      <ul className="space-y-0.5">
        {SECTIONS.map(({ id, label, icon: Icon }) => {
          const active = activeSection === id;
          return (
            <li key={id}>
              <button
                onClick={() => scrollTo(id)}
                className={`w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer ${
                  active
                    ? 'bg-brand-50 text-brand-700 font-semibold border-l-2 border-brand-600 -ml-px pl-[11px]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 shrink-0 ${active ? 'text-brand-600' : 'text-slate-400'}`} />
                {label}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );

  // ─── Render ─────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">

      {/* ── Sticky Top Header ─────────────────────────────────────── */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-14 sm:h-16">

            {/* Left */}
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
              <button
                onClick={onNavigateHome}
                className="p-2 -ml-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer shrink-0"
                aria-label="Back to Timetables"
              >
                <ArrowLeft className="w-4 h-4 sm:w-5 sm:h-5" />
              </button>
              <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-gradient-to-tr from-brand-700 to-indigo-600 flex items-center justify-center text-white shadow-sm ring-2 ring-brand-100 shrink-0">
                <Code2 className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <div className="min-w-0">
                <span className="text-[10px] sm:text-xs font-bold uppercase tracking-wider text-brand-700">
                  Developer API
                </span>
                <h1 className="text-sm sm:text-base font-bold text-slate-900 leading-tight truncate">
                  FAS Timetable API — Documentation
                </h1>
              </div>
            </div>

            {/* Right */}
            <div className="flex items-center gap-1.5 shrink-0">
              {/* Mobile nav toggle */}
              <button
                onClick={() => setMobileSidebarOpen(v => !v)}
                className="lg:hidden p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                aria-label="Toggle navigation"
              >
                {mobileSidebarOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
              </button>

              <button
                onClick={() => handleCopy(docsPageUrl, 'share-page')}
                className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg transition-colors cursor-pointer"
                title="Copy link to this page"
              >
                {copiedId === 'share-page' ? <Check className="w-3 h-3 text-emerald-600" /> : <Share2 className="w-3 h-3 text-slate-500" />}
                <span className="hidden md:inline">{copiedId === 'share-page' ? 'Copied!' : 'Share'}</span>
              </button>

              {onNavigateToReadme && (
                <button
                  onClick={onNavigateToReadme}
                  className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg transition-colors cursor-pointer"
                  title="View project README"
                >
                  <BookOpen className="w-3 h-3 text-brand-600" />
                  <span className="hidden md:inline">README</span>
                </button>
              )}

              <a
                href={GITHUB_REPO}
                target="_blank"
                rel="noopener noreferrer"
                className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg transition-colors"
                title="View on GitHub"
              >
                <GithubIcon className="w-3 h-3 text-slate-700" />
                <span className="hidden md:inline">GitHub</span>
              </a>

              <button
                onClick={onNavigateHome}
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200 rounded-lg transition-colors cursor-pointer"
                aria-label="Student Timetable Portal"
              >
                <Calendar className="w-3 h-3 text-brand-600" />
                <span className="hidden sm:inline">Student Timetable Portal</span>
                <span className="sm:hidden">App</span>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile sidebar drawer */}
        {mobileSidebarOpen && (
          <div className="lg:hidden border-t border-slate-200 bg-white px-4 py-4 max-h-[60vh] overflow-y-auto">
            <SidebarNav />
          </div>
        )}
      </header>

      {/* ── Layout: Sidebar + Main ─────────────────────────────────── */}
      <div className="max-w-[1400px] mx-auto w-full flex flex-1 px-4 sm:px-6 lg:px-8 py-8 gap-8">

        {/* Desktop Sidebar */}
        <aside className="hidden lg:block w-52 xl:w-60 shrink-0">
          <div className="sticky top-24 bg-white border border-slate-200 rounded-2xl p-4 shadow-xs max-h-[calc(100vh-7rem)] overflow-y-auto">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3 px-1">On This Page</p>
            <SidebarNav />
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0 space-y-16">

          {/* ═══ 1. OVERVIEW ═══════════════════════════════════════════ */}
          <section id="overview" className="scroll-mt-20 space-y-5">
            <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs">
              <span className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-brand-700 bg-brand-50 px-2.5 py-1 rounded-full mb-4">
                <BookOpen className="w-3.5 h-3.5" />Public REST API
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mb-3">
                FAS Timetable API — Developer Documentation
              </h2>
              <p className="text-sm sm:text-base text-slate-600 leading-relaxed max-w-3xl">
                The FAS WUSL Timetable API provides <strong>read-only, publicly accessible</strong> academic
                schedule data for the Faculty of Applied Sciences, Wayamba University of Sri Lanka.
                Data is automatically extracted from official timetable PDF notices, validated, and
                synchronized to MongoDB Atlas every 24 hours.
              </p>

              <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  { icon: Shield, label: 'Read-Only & Public', desc: 'No auth required. Free to use.' },
                  { icon: AlertTriangle, label: 'Provenance & Needs Review', desc: 'Non-standard cell annotations flagged for student review.' },
                  { icon: RefreshCw, label: 'Dynamic Term Discovery', desc: 'Query terms dynamically rather than hardcoding dates.' },
                ].map(({ icon: Icon, label, desc }) => (
                  <div key={label} className="flex items-start gap-3 p-4 bg-brand-50/60 border border-brand-100 rounded-xl">
                    <Icon className="w-5 h-5 text-brand-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{label}</p>
                      <p className="text-xs text-slate-600">{desc}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Canonical API Base URL */}
              <div className="mt-6 pt-6 border-t border-slate-100">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Canonical API Base URL
                </label>
                <div className="flex flex-col sm:flex-row gap-2">
                  <div className="flex-1 flex items-center bg-slate-900 text-slate-100 px-4 py-2.5 rounded-xl font-mono text-sm shadow-inner overflow-x-auto select-all">
                    <span className="text-indigo-400 mr-2 shrink-0 select-none">$</span>
                    <span className="truncate">{apiBaseUrl}</span>
                  </div>
                  <button
                    onClick={() => handleCopy(apiBaseUrl, 'base-url')}
                    className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm rounded-xl transition-colors cursor-pointer shrink-0"
                    aria-label="Copy API Base URL"
                  >
                    {copiedId === 'base-url' ? (
                      <>
                        <Check className="w-4 h-4 text-emerald-300" />
                        <span>Copied Base URL!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4" />
                        <span>Copy API Base URL</span>
                      </>
                    )}
                  </button>
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  Verified live production API: <code className="font-mono text-brand-700">{LIVE_BASE_URL}</code>. Timetable & Academic Calendar endpoints active.
                </p>
              </div>

              {/* Academic Calendar Integration Highlights */}
              <div className="mt-6 pt-6 border-t border-slate-100 space-y-3">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-brand-600" />
                  Academic Calendar Synchronization & Selection Architecture
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-slate-600">
                  <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl space-y-1">
                    <p className="font-semibold text-slate-900">Source Discovery & Hashing</p>
                    <p>
                      Automated workers monitor <code>https://fas.wyb.ac.lk/timetables/academic-calendar/</code>.
                      Each candidate PDF is hashed with SHA-256. Unchanged documents are skipped; new or changed documents are parsed and validated before MongoDB Atlas updates.
                    </p>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl space-y-1">
                    <p className="font-semibold text-slate-900">Selection Policy & Confirmation</p>
                    <p>
                      The current calendar is selected using verified official academic year labels (e.g. <code>2024/2025</code>)
                      and status hierarchy (Revised &gt; Approved &gt; Draft). If conflicting documents exist without clear authority, current selection is explicitly marked <code>isCurrentConfirmed: false</code>.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* ═══ 2. QUICK START ═══════════════════════════════════════ */}
          <section id="quickstart" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Zap className="w-5 h-5 text-brand-600" />Quick Start
            </h2>
            <p className="text-sm text-slate-600">
              Get timetable data in under 60 seconds — no account, no API key.
            </p>

            <div className="space-y-3">
              {[
                { n: 1, title: 'Check the API is reachable', code: `curl "${LIVE_BASE_URL}/health"` },
                { n: 2, title: 'List available timetable terms', code: `curl "${LIVE_BASE_URL}/timetables"` },
                { n: 3, title: 'Fetch Level 2 sessions', code: `curl "${LIVE_BASE_URL}/timetables/2/sessions"` },
                { n: 4, title: 'Filter by day', code: `curl "${LIVE_BASE_URL}/timetables/2/sessions?day=Friday"` },
              ].map(({ n, title, code }) => (
                <div key={n} className="flex gap-4 bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
                  <div className="w-7 h-7 rounded-full bg-brand-600 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">{n}</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-slate-700 mb-2">{title}</p>
                    <CodeBlock
                      code={code}
                      language="bash"
                      id={`qs-${n}`}
                      copiedId={copiedId}
                      handleCopy={handleCopy}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* ═══ 3. BASE URL ══════════════════════════════════════════ */}
          <section id="base-url" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Globe className="w-5 h-5 text-brand-600" />Base URL & Availability
            </h2>

            <div className="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-xs space-y-4">
              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="min-w-full text-xs divide-y divide-slate-100">
                  <thead className="bg-slate-50">
                    <tr>
                      {['Environment', 'Base URL', 'Notes'].map(h => (
                        <th key={h} className="px-4 py-3 text-left font-semibold text-slate-600">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-slate-50">
                    <tr>
                      <td className="px-4 py-3 font-semibold text-emerald-700">Production</td>
                      <td className="px-4 py-3 font-mono text-slate-800 select-all">{LIVE_BASE_URL}</td>
                      <td className="px-4 py-3 text-slate-600">Live. Verified working.</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-semibold text-brand-700">Local dev</td>
                      <td className="px-4 py-3 font-mono text-slate-800">http://localhost:8000/api</td>
                      <td className="px-4 py-3 text-slate-600">Run <code className="bg-slate-100 px-1 rounded">uvicorn api.index:app</code></td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900">
                <AlertTriangle className="w-3.5 h-3.5 inline mr-1 text-amber-600" />
                The production deployment is hosted on <strong>Vercel's serverless infrastructure</strong>.
                Cold starts may add 1–3 seconds on the first request. Subsequent requests are faster.
                The daily sync worker runs at <strong>00:00 UTC</strong> — expect data to reflect the latest
                revision within minutes of that time.
              </div>
            </div>
          </section>

          {/* ═══ 4. AUTHENTICATION ════════════════════════════════════ */}
          <section id="auth" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Shield className="w-5 h-5 text-brand-600" />Authentication
            </h2>
            <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5 sm:p-6 shadow-xs">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-emerald-900 mb-1">No Authentication Required</h3>
                  <p className="text-sm text-emerald-800">
                    All API endpoints are publicly accessible over HTTPS. No API key, Bearer token,
                    OAuth flow, or any authorization header is required. Simply send a GET request
                    to the endpoint URL.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* ═══ 5. API ENDPOINTS ═════════════════════════════════════ */}
          <section id="endpoints" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Code2 className="w-5 h-5 text-brand-600" />API Endpoint Reference
            </h2>
            <p className="text-sm text-slate-600">
              All endpoints use <MethodBadge method="GET" /> HTTP. No request body is required for any endpoint.
              Click an endpoint to expand parameters, response schema, and a cURL example.
            </p>
            <div className="space-y-3">
              {endpoints.map(ep => (
                <EndpointBlock
                  key={ep.path}
                  endpoint={ep}
                  copiedId={copiedId}
                  handleCopy={handleCopy}
                />
              ))}
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-900">
              <Info className="w-3.5 h-3.5 inline mr-1 text-blue-600" />
              <strong>Retrieving all 4 levels:</strong> There is no single endpoint that returns sessions for all levels.
              Make 4 parallel requests (<code className="bg-blue-100 px-1 rounded font-mono">levels 1–4</code>) and
              merge client-side. With JavaScript, use <code className="bg-blue-100 px-1 rounded font-mono">Promise.all()</code>.
            </div>
          </section>

          {/* ═══ 6. INTERACTIVE EXPLORER ══════════════════════════════ */}
          <section id="explorer" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Play className="w-5 h-5 text-brand-600" />Interactive API Explorer
            </h2>
            <p className="text-sm text-slate-600">
              Send real requests to the live production API directly from your browser.
              CORS is configured to allow <code className="bg-slate-100 px-1 rounded font-mono text-xs">*.vercel.app</code> origins —
              requests may succeed or be blocked depending on your browser and origin.
              Use the cURL examples above for guaranteed access.
            </p>
            <InteractiveExplorer copiedId={copiedId} handleCopy={handleCopy} />
          </section>

          {/* ═══ 7. DATA SCHEMA ═══════════════════════════════════════ */}
          <section id="schema" className="scroll-mt-20 space-y-6">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Layers className="w-5 h-5 text-brand-600" />Timetable Data Schema
            </h2>

            {/* Session Schema */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100">
                <h3 className="font-bold text-slate-900 text-sm">TimetableSession — individual teaching slot</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Returned in the <code className="bg-slate-100 px-1 rounded font-mono">sessions</code> array by
                  <code className="bg-slate-100 px-1 rounded font-mono"> GET /timetables/&#123;level&#125;/sessions</code>
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs divide-y divide-slate-100">
                  <thead className="bg-slate-50">
                    <tr>
                      {['Field', 'Type', 'Req?', 'Example', 'Description'].map(h => (
                        <th key={h} className="px-4 py-3 text-left font-semibold text-slate-600 whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-slate-50">
                    {sessionFields.map(f => (
                      <tr key={f.name}>
                        <td className="px-4 py-2.5 font-mono font-semibold text-brand-700 whitespace-nowrap">{f.name}</td>
                        <td className="px-4 py-2.5 font-mono text-slate-500 whitespace-nowrap">{f.type}</td>
                        <td className="px-4 py-2.5 text-center">
                          {f.req ? <span className="text-red-600 font-bold">●</span> : <span className="text-slate-300">○</span>}
                        </td>
                        <td className="px-4 py-2.5 font-mono text-slate-500 text-[11px] whitespace-nowrap">{f.ex}</td>
                        <td className="px-4 py-2.5 text-slate-600">{f.desc}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Timetable Metadata Schema */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100">
                <h3 className="font-bold text-slate-900 text-sm">TimetableMetadata — source PDF record</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Returned by <code className="bg-slate-100 px-1 rounded font-mono">GET /timetables</code>
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs divide-y divide-slate-100">
                  <thead className="bg-slate-50">
                    <tr>
                      {['Field', 'Type', 'Req?', 'Example', 'Description'].map(h => (
                        <th key={h} className="px-4 py-3 text-left font-semibold text-slate-600 whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-slate-50">
                    {timetableFields.map(f => (
                      <tr key={f.name}>
                        <td className="px-4 py-2.5 font-mono font-semibold text-brand-700 whitespace-nowrap">{f.name}</td>
                        <td className="px-4 py-2.5 font-mono text-slate-500 whitespace-nowrap">{f.type}</td>
                        <td className="px-4 py-2.5 text-center">
                          {f.req ? <span className="text-red-600 font-bold">●</span> : <span className="text-slate-300">○</span>}
                        </td>
                        <td className="px-4 py-2.5 font-mono text-slate-500 text-[11px] whitespace-nowrap">{f.ex}</td>
                        <td className="px-4 py-2.5 text-slate-600">{f.desc}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-5 py-3 bg-amber-50 border-t border-amber-200 text-xs text-amber-800">
                <AlertTriangle className="w-3 h-3 inline mr-1 text-amber-600" />
                <strong>Known issue:</strong> The <code className="bg-amber-100 font-mono px-1 rounded">localPath</code> field
                contains an internal worker path artifact and is <em>not meaningful</em> for API consumers.
                It will be removed in a future release. Ignore it in your application.
              </div>
            </div>

            {/* NEEDS_REVIEW explanation */}
            <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 sm:p-6 space-y-3">
              <h3 className="font-bold text-amber-950 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>Displaying Review Warnings to Students (Do Not Silently Confirm)</span>
              </h3>
              <p className="text-sm text-amber-900 leading-relaxed">
                When <code className="bg-amber-100 px-1 rounded font-mono text-xs">validationStatus</code> is
                <code className="bg-amber-100 px-1 rounded font-mono text-xs ml-1">"NEEDS_REVIEW"</code>,
                the parser found ambiguous or non-standard content in the source PDF — for example, a subject code
                containing a "+" character (e.g. <code className="bg-amber-100 px-1 rounded font-mono text-xs">"ELPC 2+20"</code>),
                or a cell with no session type annotation. The session is retained verbatim to avoid silent data loss.
              </p>
              <p className="text-sm font-semibold text-amber-900">
                Your application must: display a visible "Unverified" badge or warning indicator for these sessions,
                and advise users to confirm with their department. Never silently confirm or drop NEEDS_REVIEW sessions.
              </p>
              <CodeBlock
                code={`// Always check validationStatus
if (session.validationStatus === 'NEEDS_REVIEW') {
  // Show warning badge — don't hide this from students
  console.warn('⚠ Unverified:', session.warnings.join(', '));
  // session.rawCellText contains the verbatim PDF text for reference
}`}
                language="javascript"
                id="needs-review-code"
                copiedId={copiedId}
                handleCopy={handleCopy}
              />
            </div>
          </section>

          {/* ═══ 8. CODE EXAMPLES ═════════════════════════════════════ */}
          <section id="examples" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Terminal className="w-5 h-5 text-brand-600" />Integration Code Examples
            </h2>
            <p className="text-sm text-slate-600">
              Complete, copy-ready integration examples verified against the live API schema.
            </p>

            {/* Language tabs */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
              <div className="flex border-b border-slate-200 bg-slate-50">
                {[
                  { id: 'js', label: 'JavaScript (fetch)' },
                  { id: 'py', label: 'Python (requests)' },
                  { id: 'curl', label: 'cURL / REST' },
                ].map(t => (
                  <button
                    key={t.id}
                    onClick={() => setActiveCodeTab(t.id)}
                    className={`px-4 py-3 text-xs font-semibold border-b-2 transition-colors cursor-pointer ${
                      activeCodeTab === t.id
                        ? 'border-brand-600 text-brand-700 bg-white'
                        : 'border-transparent text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <div className="p-4 sm:p-5">
                {activeCodeTab === 'js' && (
                  <CodeBlock code={jsExample} language="javascript" id="ex-js" copiedId={copiedId} handleCopy={handleCopy} label="JavaScript example" />
                )}
                {activeCodeTab === 'py' && (
                  <CodeBlock code={pyExample} language="python" id="ex-py" copiedId={copiedId} handleCopy={handleCopy} label="Python example" />
                )}
                {activeCodeTab === 'curl' && (
                  <CodeBlock code={curlExamples} language="bash" id="ex-curl" copiedId={copiedId} handleCopy={handleCopy} label="cURL examples" />
                )}
              </div>
            </div>
          </section>

          {/* ═══ 9. ERROR HANDLING ════════════════════════════════════ */}
          <section id="errors" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-brand-600" />Error Handling
            </h2>
            <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs divide-y divide-slate-100">
                  <thead className="bg-slate-50">
                    <tr>
                      {['HTTP Status', 'Meaning', 'Cause', 'Client Action'].map(h => (
                        <th key={h} className="px-4 py-3 text-left font-semibold text-slate-600">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-slate-50 text-slate-700">
                    {[
                      { code: '200', meaning: 'OK', cause: 'Request succeeded', action: 'Parse JSON body' },
                      { code: '404', meaning: 'Not Found', cause: 'Path does not match any endpoint', action: 'Check URL spelling' },
                      { code: '422', meaning: 'Unprocessable Entity', cause: 'Invalid parameter — e.g. level=5, day=Saturday', action: 'Inspect detail array in response body, fix parameter' },
                      { code: '503', meaning: 'Service Unavailable', cause: 'MongoDB Atlas connection failure', action: 'Retry after 5–30 seconds; check /health for status' },
                    ].map(r => (
                      <tr key={r.code}>
                        <td className="px-4 py-3 font-mono font-bold text-slate-800">{r.code}</td>
                        <td className="px-4 py-3 font-semibold">{r.meaning}</td>
                        <td className="px-4 py-3 text-slate-600">{r.cause}</td>
                        <td className="px-4 py-3 text-slate-600">{r.action}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-800">422 Validation Error Shape</h3>
              <CodeBlock
                code={`// Example: level=5 returns HTTP 422
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["path", "level"],
      "msg": "Input should be less than or equal to 4",
      "input": "5",
      "ctx": { "le": 4 }
    }
  ]
}`}
                language="json"
                id="err-422"
                copiedId={copiedId}
                handleCopy={handleCopy}
              />

              <h3 className="text-sm font-bold text-slate-800 pt-2">Client-Side Retry Pattern</h3>
              <CodeBlock
                code={`async function fetchWithRetry(url, maxRetries = 2) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const res = await fetch(url, { headers: { Accept: 'application/json' } });
      if (res.status === 503 && attempt < maxRetries) {
        await new Promise(r => setTimeout(r, 5000 * (attempt + 1))); // back-off
        continue;
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(\`HTTP \${res.status}: \${JSON.stringify(err.detail || err)}\`);
      }
      return await res.json();
    } catch (err) {
      if (attempt === maxRetries) throw err;
    }
  }
}`}
                language="javascript"
                id="err-retry"
                copiedId={copiedId}
                handleCopy={handleCopy}
              />
            </div>
          </section>

          {/* ═══ 10. DATA FRESHNESS ═══════════════════════════════════ */}
          <section id="freshness" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-brand-600" />Data Freshness & Synchronization
            </h2>
            <div className="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-xs space-y-5">
              {[
                {
                  icon: Clock,
                  title: 'Update schedule',
                  text: 'A GitHub Actions scheduled workflow runs automatically every 24 hours at 00:00 UTC (05:30 Sri Lanka Time). Manual runs can be triggered through the repository Actions tab with optional --force and --dry-run flags.',
                },
                {
                  icon: Search,
                  title: 'Change detection',
                  text: 'For each academic level, the worker computes a SHA-256 digest of the downloaded PDF in memory and compares it against the stored digest. If the hashes match, no database write occurs. This means the API data is exactly as accurate as the most recent PDF published on the FAS WUSL website.',
                },
                {
                  icon: Database,
                  title: 'Revision tracking',
                  text: 'The revision field in timetable metadata (e.g. "Revised 02") reflects the label extracted from the faculty notice title. The sha256 field changes whenever the source PDF is replaced — you can use this as a cache-busting signal.',
                },
                {
                  icon: Shield,
                  title: 'PDF handling',
                  text: 'PDFs are downloaded into an isolated temporary workspace (tempfile.TemporaryDirectory) and deleted immediately after parsing. No permanent PDF files are stored by this system.',
                },
              ].map(({ icon: Icon, title, text }) => (
                <div key={title} className="flex gap-4">
                  <Icon className="w-5 h-5 text-brand-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-slate-900 mb-1">{title}</p>
                    <p className="text-sm text-slate-600">{text}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-900">
              <Info className="w-3.5 h-3.5 inline mr-1 text-blue-600" />
              <strong>Recommendation:</strong> Cache API responses client-side for at least 15 minutes.
              The underlying data changes at most once per day when a new PDF revision is published by the faculty.
              Polling every few seconds is unnecessary and will waste your users' bandwidth.
            </div>
          </section>

          {/* ═══ 11. CORS & LIMITS ════════════════════════════════════ */}
          <section id="cors" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Shield className="w-5 h-5 text-brand-600" />CORS, Rate Limits & Usage Policy
            </h2>
            <div className="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-xs space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 mb-2">CORS Policy (verified from source)</h3>
                <p className="text-sm text-slate-600 mb-3">
                  The production CORS configuration allows any <code className="bg-slate-100 px-1 rounded font-mono text-xs">*.vercel.app</code> origin
                  and a set of explicit localhost development origins. Cross-origin requests from other domains (e.g. your custom domain)
                  <strong> may be blocked</strong> unless the <code className="bg-slate-100 px-1 rounded font-mono text-xs">CORS_ORIGINS</code> environment
                  variable is updated in the Vercel deployment. Use the cURL examples or a server-side proxy if your origin is blocked.
                </p>
                <CodeBlock
                  code={`# Default allowed origins (from source code):
# - http://localhost:5173
# - http://localhost:3000
# - http://127.0.0.1:5173
# - http://localhost:8000
# - http://127.0.0.1:8000
# - Regex: ^https:\\/\\/.*\\.vercel\\.app$  (all *.vercel.app subdomains)`}
                  language="bash"
                  id="cors-origins"
                  copiedId={copiedId}
                  handleCopy={handleCopy}
                />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900 mb-2">Rate Limits</h3>
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-sm text-slate-600">
                  No explicit rate limit is configured by this application.
                  Vercel's platform imposes its own limits based on its free/pro tier.
                  Please be considerate: implement client-side caching, avoid polling at high frequency,
                  and do not scrape all endpoints in tight loops.
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900 mb-2">Usage Policy</h3>
                <ul className="text-sm text-slate-600 space-y-1.5 list-disc list-inside">
                  <li>Free to use for student applications, academic tools, and personal projects.</li>
                  <li>Do not use for commercial resale of the timetable data without attribution.</li>
                  <li>Data is sourced from official FAS WUSL faculty notices — always attribute the faculty.</li>
                  <li>All endpoints are read-only; there are no write or mutation operations.</li>
                </ul>
              </div>
            </div>
          </section>

          {/* ═══ 12. BEST PRACTICES ═══════════════════════════════════ */}
          <section id="best-practices" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-brand-600" />Best Practices
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[
                { icon: Clock, title: 'Cache responses', text: 'Store responses for at least 15 minutes. Data changes at most once per day.' },
                { icon: Zap, title: 'Fetch in parallel', text: 'Use Promise.all() to fetch levels 1–4 concurrently rather than sequentially.' },
                { icon: AlertTriangle, title: 'Always show NEEDS_REVIEW warnings', text: 'Never silently confirm or hide flagged sessions from students.' },
                { icon: RefreshCw, title: 'Handle cold starts', text: 'The first request after inactivity may take 2–4 s. Show a loading indicator and retry once on timeout.' },
                { icon: Database, title: 'Use sha256 as a cache key', text: 'Compare the sha256 field in /timetables response to detect PDF revisions without re-downloading all sessions.' },
                { icon: Shield, title: 'Validate path parameters', text: 'Level must be 1–4. Day must be exactly one of the 5 weekday strings. Validate client-side before making requests.' },
              ].map(({ icon: Icon, title, text }) => (
                <div key={title} className="flex gap-3 bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
                  <Icon className="w-4 h-4 text-brand-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-semibold text-slate-900 mb-1">{title}</p>
                    <p className="text-xs text-slate-600">{text}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* ═══ 13. OPENAPI ══════════════════════════════════════════ */}
          <section id="openapi" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Database className="w-5 h-5 text-brand-600" />OpenAPI & Swagger
            </h2>
            <div className="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-xs space-y-3">
              <p className="text-sm text-slate-600">
                FastAPI automatically generates an OpenAPI 3.1 schema. In the Vercel deployment,
                the <code className="bg-slate-100 px-1 rounded font-mono text-xs">/docs</code> route
                is intercepted by the SPA rewrite rule and returns the React app.
                The raw OpenAPI JSON schema is served by the FastAPI serverless function:
              </p>
              <CodeBlock
                code={`# OpenAPI JSON schema
curl "${LIVE_BASE_URL.replace('/api', '')}/openapi.json"

# Note: /docs (Swagger UI) is not accessible at the Vercel deployment
# because the SPA catch-all rewrite intercepts the route.
# Use the documentation on this page instead.`}
                language="bash"
                id="openapi-curl"
                copiedId={copiedId}
                handleCopy={handleCopy}
              />
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900">
                <AlertTriangle className="w-3.5 h-3.5 inline mr-1 text-amber-600" />
                The <code className="font-mono bg-amber-100 px-1 rounded">/openapi.json</code> path availability
                depends on how the serverless function resolves the path at runtime and may not be stable.
                The endpoint documentation on this page is the authoritative reference.
              </div>
            </div>
          </section>

          {/* ═══ 14. FAQ ══════════════════════════════════════════════ */}
          <section id="faq" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <HelpCircle className="w-5 h-5 text-brand-600" />Frequently Asked Questions
            </h2>
            <div className="space-y-3">
              {faqs.map((item, i) => (
                <FaqItem key={i} q={item.q} a={item.a} />
              ))}
            </div>
          </section>

          {/* ═══ 15. RESOURCES ════════════════════════════════════════ */}
          <section id="resources" className="scroll-mt-20 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-brand-600" />GitHub & Developer Resources
            </h2>
            <div className="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-xs">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-6">
                <div className="max-w-lg">
                  <h3 className="text-base font-bold text-slate-900 mb-1">FAS WUSL Timetable Downloader & Portal</h3>
                  <p className="text-sm text-slate-600">
                    Open source. Contains the PDF scraper, coordinate-aware parser, MongoDB sync worker,
                    FastAPI backend, React frontend, GitHub Actions workflow, and all tests.
                  </p>
                  <p className="text-sm text-slate-600 mt-2">
                    Maintained by{' '}
                    <a href={GITHUB_DEV} target="_blank" rel="noopener noreferrer"
                      className="text-brand-600 font-semibold hover:underline">
                      Kasun Herath
                    </a>
                    {' '}· Open source under the MIT License.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 shrink-0">
                  <a href={GITHUB_REPO} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-xl transition-colors">
                    <GithubIcon className="w-4 h-4" />Repository
                  </a>
                  <a href={GITHUB_DEV} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-100 text-slate-800 text-xs font-semibold border border-slate-300 rounded-xl transition-colors">
                    <GithubIcon className="w-4 h-4" />Developer Profile
                  </a>
                  {onNavigateToReadme && (
                    <button onClick={onNavigateToReadme}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-100 text-slate-800 text-xs font-semibold border border-slate-300 rounded-xl transition-colors cursor-pointer">
                      <BookOpen className="w-4 h-4 text-brand-600" />Project README
                    </button>
                  )}
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                {[
                  { label: 'Live Application', href: 'https://fas-timetable-downloader-ipa1.vercel.app', desc: 'Student-facing timetable portal' },
                  { label: 'FAS WUSL Timetables', href: 'https://fas.wyb.ac.lk/timetables/', desc: 'Official source of timetable PDFs' },
                  { label: 'FastAPI documentation', href: 'https://fastapi.tiangolo.com', desc: 'Backend framework used by this API' },
                  { label: 'Issues & Contributions', href: `${GITHUB_REPO}/issues`, desc: 'Report bugs or suggest improvements' },
                ].map(({ label, href, desc }) => (
                  <a key={href} href={href} target="_blank" rel="noopener noreferrer"
                    className="flex items-start gap-2 p-3 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors group">
                    <ExternalLink className="w-3.5 h-3.5 text-slate-400 group-hover:text-brand-600 shrink-0 mt-0.5 transition-colors" />
                    <div>
                      <p className="font-semibold text-slate-900 group-hover:text-brand-700 transition-colors text-xs">{label}</p>
                      <p className="text-xs text-slate-500">{desc}</p>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          </section>
        </main>
      </div>

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <footer className="bg-white border-t border-slate-200 py-8 text-center text-xs text-slate-500">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 space-y-3">
          <p className="font-semibold text-slate-700">
            FAS WUSL Timetable API · Faculty of Applied Sciences, Wayamba University of Sri Lanka
          </p>
          <p>Free and public read-only service for students, faculty, and developers.</p>
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-slate-600 pt-1">
            <button onClick={onNavigateHome} className="hover:text-brand-700 font-medium cursor-pointer">Timetable Portal</button>
            {onNavigateToReadme && (
              <><span className="text-slate-300">·</span>
              <button onClick={onNavigateToReadme} className="hover:text-brand-700 font-medium cursor-pointer">Project README</button></>
            )}
            <span className="text-slate-300">·</span>
            <a href={GITHUB_REPO} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 hover:text-slate-900 font-medium">
              <GithubIcon className="w-3.5 h-3.5" />GitHub
            </a>
          </div>
          <p className="text-[11px] text-slate-400 pt-1">
            Maintained by{' '}
            <a href={GITHUB_DEV} target="_blank" rel="noopener noreferrer"
              className="font-medium text-slate-600 hover:text-brand-600 underline">
              Kasun Herath
            </a>{' '}
            · Open Source Under MIT License
          </p>
        </div>
      </footer>
    </div>
  );
}

// ─── FAQ Item (accordion) ──────────────────────────────────────────────────
function FaqItem({ q, a }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left flex items-center justify-between gap-3 px-5 py-4 hover:bg-slate-50 transition-colors"
        aria-expanded={open}
      >
        <span className="text-sm font-semibold text-slate-900">{q}</span>
        {open ? <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" /> : <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />}
      </button>
      {open && (
        <div className="px-5 pb-4 pt-0 border-t border-slate-100 bg-slate-50/30">
          <p className="text-sm text-slate-600 leading-relaxed pt-3">{a}</p>
        </div>
      )}
    </div>
  );
}
