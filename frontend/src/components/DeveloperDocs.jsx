import React, { useState } from 'react';
import {
  Calendar,
  Code2,
  Copy,
  Check,
  Share2,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  ArrowLeft,
  Terminal,
  Database,
  Layers,
  BookOpen,
} from 'lucide-react';

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

export default function DeveloperDocs({ onNavigateHome }) {
  const [copiedId, setCopiedId] = useState(null);
  const [activeCodeTab, setActiveCodeTab] = useState('javascript');

  const apiBaseUrl = getResolvedApiBaseUrl();
  const docsPageUrl =
    typeof window !== 'undefined'
      ? `${window.location.origin}/developers`
      : '/developers';

  const handleCopy = async (text, id) => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2500);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const endpoints = [
    {
      id: 'health',
      method: 'GET',
      path: '/api/health',
      title: 'Health Check & Database Connectivity',
      description:
        'Returns the runtime status of the FastAPI backend service and its connectivity to MongoDB Atlas.',
      params: [],
      exampleUrl: `${apiBaseUrl}/health`,
      response: {
        status: 'ok',
        database: 'connected',
        timestamp: '2026-10-16T00:53:34.149012+05:30',
      },
    },
    {
      id: 'timetables',
      method: 'GET',
      path: '/api/timetables',
      title: 'List Available Timetables & Metadata',
      description:
        'Retrieves published timetable metadata including academic year, semester, revision identifier, publication date, and source PDF SHA-256 checksum.',
      params: [
        {
          name: 'level',
          type: 'integer',
          required: false,
          description: 'Filter by academic level: 1, 2, 3, or 4.',
          example: 'level=2',
        },
      ],
      exampleUrl: `${apiBaseUrl}/timetables?level=2`,
      response: [
        {
          id: '670f55df4b614d1123456789',
          level: 2,
          academicYear: '2024/2025',
          semester: 'Semester I',
          revision: 'Revised 01',
          noticeTitle:
            'Revised – Academic Time Table – Level 1,2,3 & 4 Semester I (Academic Year 2024/2025)',
          noticeUrl:
            'https://fas.wyb.ac.lk/revised-academic-time-table-level-123-4-semester-i-academic-year-2024-2025/',
          sourcePdfUrl: 'https://fas.wyb.ac.lk/wp-content/uploads/2026/09/Level-23.pdf',
          publishedDate: '2026-09-10',
          downloadedAt: '2026-10-15T17:55:03.426529+05:30',
          localPath: null,
          fileSize: 715435,
          sha256: '0e872ee45891554f337d5906e1a53998b05e6cddfe55660048164bb22cffa957',
          updatedAt: '2026-10-16T00:00:00.000000+00:00',
        },
      ],
    },
    {
      id: 'sessions',
      method: 'GET',
      path: '/api/timetables/{level}/sessions',
      title: 'Get Teaching & Practical Sessions',
      description:
        'Retrieves atomic schedule sessions for an academic level. Automatically defaults to the newest available academic term if year or semester query parameters are omitted.',
      params: [
        {
          name: '{level}',
          type: 'path (integer)',
          required: true,
          description: 'Target academic level (1, 2, 3, or 4).',
          example: '2',
        },
        {
          name: 'academicYear',
          type: 'string',
          required: false,
          description: 'Academic year (e.g. "2024/2025"). Defaults to active term.',
          example: 'academicYear=2024/2025',
        },
        {
          name: 'semester',
          type: 'string',
          required: false,
          description: 'Semester name (e.g. "Semester I"). Defaults to active term.',
          example: 'semester=Semester I',
        },
        {
          name: 'day',
          type: 'string',
          required: false,
          description:
            'Filter by weekday: Monday, Tuesday, Wednesday, Thursday, or Friday.',
          example: 'day=Friday',
        },
        {
          name: 'subjectCode',
          type: 'string',
          required: false,
          description: 'Case-insensitive course code prefix filter (e.g. "CMIS").',
          example: 'subjectCode=CMIS',
        },
      ],
      exampleUrl: `${apiBaseUrl}/timetables/2/sessions?day=Friday`,
      response: {
        level: 2,
        academicYear: '2024/2025',
        semester: 'Semester I',
        day: 'Friday',
        subjectCode: null,
        totalSessions: 1,
        sessions: [
          {
            id: '670f55df4b614d112345678a',
            timetableId: '670f55df4b614d1123456789',
            level: 2,
            academicYear: '2024/2025',
            semester: 'Semester I',
            day: 'Friday',
            startTime: '12:30',
            endTime: '13:30',
            subjectCode: 'CMIS 2113',
            sessionType: 'Lecture',
            group: null,
            location: 'LR- 07',
            rawCellText: 'CMIS 2113 (L)\nLR- 07',
            validationStatus: 'VALID',
            warnings: [],
            sourcePdfHash:
              '0e872ee45891554f337d5906e1a53998b05e6cddfe55660048164bb22cffa957',
            updatedAt: '2026-10-16T00:00:00.000000+00:00',
          },
        ],
      },
    },
    {
      id: 'status',
      method: 'GET',
      path: '/api/timetables/{level}/status',
      title: 'Level Validation Status & Session Breakdown',
      description:
        'Provides summary metrics for an academic level, including counts of verified sessions, review-flagged sessions, and session type breakdowns.',
      params: [
        {
          name: '{level}',
          type: 'path (integer)',
          required: true,
          description: 'Target academic level (1, 2, 3, or 4).',
          example: '1',
        },
        {
          name: 'academicYear',
          type: 'string',
          required: false,
          description: 'Academic year (e.g. "2024/2025").',
          example: 'academicYear=2024/2025',
        },
        {
          name: 'semester',
          type: 'string',
          required: false,
          description: 'Semester (e.g. "Semester I").',
          example: 'semester=Semester I',
        },
      ],
      exampleUrl: `${apiBaseUrl}/timetables/1/status`,
      response: {
        level: 1,
        academicYear: '2024/2025',
        semester: 'Semester I',
        totalSessions: 44,
        validSessions: 40,
        needsReviewSessions: 4,
        sessionTypes: {
          Lecture: 24,
          Practical: 16,
          Tutorial: 4,
        },
      },
    },
  ];

  const jsFetchExample = `// Complete JavaScript Integration Example
// Fetches Level 2 Friday sessions using the FAS WUSL Timetable API

async function fetchLevel2FridaySchedule() {
  const API_BASE = '${apiBaseUrl}';
  const url = \`\${API_BASE}/timetables/2/sessions?day=Friday\`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(\`HTTP error \${response.status}: \${response.statusText}\`);
    }

    const data = await response.json();
    console.log(\`Academic Term: \${data.academicYear} \${data.semester}\`);
    console.log(\`Found \${data.totalSessions} sessions on Friday:\`);

    data.sessions.forEach((session) => {
      console.log(
        \`[\${session.startTime} - \${session.endTime}] \` +
        \`\${session.subjectCode || 'No Code'} (\${session.sessionType || 'Session'}) \` +
        \`Location: \${session.location || 'TBA'}\`
      );

      // Important: Inspect sessions flagged for review
      if (session.validationStatus === 'NEEDS_REVIEW') {
        console.warn(
          \`  ⚠️ NEEDS_REVIEW: Ambiguous or non-standard cell text. \` +
          \`Warnings: \${session.warnings.join(', ')}\`
        );
      }
    });

    return data.sessions;
  } catch (error) {
    console.error('Failed to load timetable:', error.message);
    throw error;
  }
}

// Invoke function
fetchLevel2FridaySchedule();`;

  const pythonExample = `# Complete Python Integration Example
import requests

API_BASE = "${apiBaseUrl}"

def get_level2_friday_sessions():
    url = f"{API_BASE}/timetables/2/sessions"
    params = {"day": "Friday"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        print(f"Term: {data.get('academicYear')} {data.get('semester')}")
        for s in data.get("sessions", []):
            code = s.get("subjectCode") or "N/A"
            loc = s.get("location") or "TBA"
            print(f"- {s['startTime']}-{s['endTime']}: {code} at {loc}")
            
            if s.get("validationStatus") == "NEEDS_REVIEW":
                print(f"  [REVIEW] {s.get('warnings')}")

    except requests.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    get_level2_friday_sessions()`;

  const curlExample = `# Retrieve Level 2 Friday Sessions
curl -X GET "${apiBaseUrl}/timetables/2/sessions?day=Friday" \\
  -H "Accept: application/json"

# Check API health status
curl -X GET "${apiBaseUrl}/health"`;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16 sm:h-20">
            {/* Left: Branding & Back Navigation */}
            <div className="flex items-center space-x-3 sm:space-x-4">
              <button
                onClick={onNavigateHome}
                className="p-2 -ml-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                title="Back to Timetables"
                aria-label="Back to Timetables"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>

              <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-gradient-to-tr from-brand-700 to-indigo-600 flex items-center justify-center text-white shadow-sm ring-2 ring-brand-100">
                <Code2 className="w-5 h-5 sm:w-6 sm:h-6" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
                    Developer API
                  </span>
                  <span className="text-xs text-slate-500 hidden sm:inline">
                    Faculty of Applied Sciences • WUSL
                  </span>
                </div>
                <h1 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight leading-tight">
                  FAS Timetable API Documentation
                </h1>
              </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center space-x-2 sm:space-x-3">
              <button
                onClick={() => handleCopy(docsPageUrl, 'share-page')}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-2xs transition-colors cursor-pointer"
                title="Copy shareable link to this documentation page"
              >
                {copiedId === 'share-page' ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="text-emerald-700">Link Copied</span>
                  </>
                ) : (
                  <>
                    <Share2 className="w-3.5 h-3.5 text-slate-500" />
                    <span className="hidden sm:inline">Share Page</span>
                  </>
                )}
              </button>

              <button
                onClick={onNavigateHome}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200 rounded-lg transition-colors cursor-pointer"
                aria-label="Student Timetable Portal"
              >
                <Calendar className="w-3.5 h-3.5 text-brand-600" />
                <span className="hidden sm:inline">Student Timetable</span>
                <span className="sm:hidden">App</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Section */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs">
          <div className="max-w-3xl">
            <span className="inline-flex items-center space-x-1.5 text-xs font-semibold uppercase tracking-wider text-brand-700 bg-brand-50 px-2.5 py-1 rounded-full mb-3">
              <BookOpen className="w-3.5 h-3.5" />
              <span>Public REST API</span>
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              FAS Timetable API — Developer Documentation
            </h2>
            <p className="mt-3 text-sm sm:text-base text-slate-600 leading-relaxed">
              Integrate verified academic timetables from the Faculty of Applied Sciences,
              Wayamba University of Sri Lanka into your web, mobile, or desktop application.
              Data is automatically parsed from official timetable PDF notices and synchronized
              with MongoDB Atlas.
            </p>
          </div>

          {/* Prominent Copyable API Base URL */}
          <div className="mt-6 pt-6 border-t border-slate-100">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
              Canonical API Base URL
            </label>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
              <div className="flex-1 flex items-center bg-slate-900 text-slate-100 px-4 py-2.5 rounded-xl font-mono text-sm shadow-inner overflow-x-auto select-all">
                <span className="text-indigo-400 mr-2 select-none">$</span>
                <span className="truncate">{apiBaseUrl}</span>
              </div>
              <button
                onClick={() => handleCopy(apiBaseUrl, 'base-url')}
                className="inline-flex items-center justify-center space-x-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm rounded-xl shadow-xs transition-colors cursor-pointer shrink-0"
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
            <p className="text-xs text-slate-500 mt-2 flex items-center gap-1.5">
              <span>All endpoints documented below are accessed relative to this Base URL.</span>
            </p>
          </div>
        </div>

        {/* API Guarantees & Safety Banner */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex items-start space-x-3.5">
            <div className="p-2 rounded-lg bg-emerald-50 text-emerald-700 shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Read-Only & Public</h3>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                No API keys or authentication required. The API provides read-only access to academic schedules and metadata.
              </p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex items-start space-x-3.5">
            <div className="p-2 rounded-lg bg-amber-50 text-amber-700 shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Provenance & Needs Review</h3>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Sessions with ambiguous cell annotations carry status <code className="text-amber-800 bg-amber-50 px-1 py-0.5 rounded font-mono text-2xs">NEEDS_REVIEW</code>. Client apps should visibly display review warnings.
              </p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex items-start space-x-3.5">
            <div className="p-2 rounded-lg bg-indigo-50 text-indigo-700 shrink-0">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Dynamic Term Discovery</h3>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Query <code className="text-indigo-800 bg-indigo-50 px-1 py-0.5 rounded font-mono text-2xs">/api/timetables</code> to discover current academic terms dynamically rather than hardcoding dates.
              </p>
            </div>
          </div>
        </div>

        {/* Endpoints Reference */}
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2">
              <Terminal className="w-5 h-5 text-brand-600" />
              <span>Verified Endpoints Reference</span>
            </h2>
            <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-md">
              JSON Responses
            </span>
          </div>

          <div className="space-y-6">
            {endpoints.map((ep) => (
              <div
                key={ep.id}
                className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs hover:border-slate-300 transition-colors"
              >
                {/* Endpoint Header Bar */}
                <div className="bg-slate-50/80 px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center space-x-3">
                    <span className="px-2.5 py-1 rounded-md text-xs font-bold tracking-wide bg-emerald-100 text-emerald-800">
                      {ep.method}
                    </span>
                    <span className="font-mono text-sm font-semibold text-slate-800">
                      {ep.path}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleCopy(`${apiBaseUrl}${ep.path.replace('/api', '')}`, `req-${ep.id}`)}
                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-2xs transition-colors cursor-pointer"
                    >
                      {copiedId === `req-${ep.id}` ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="text-emerald-700">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy URL</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Endpoint Body */}
                <div className="p-6 space-y-5">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">{ep.title}</h3>
                    <p className="text-sm text-slate-600 mt-1">{ep.description}</p>
                  </div>

                  {/* Query / Path Parameters */}
                  {ep.params.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                        Parameters
                      </h4>
                      <div className="overflow-x-auto border border-slate-200 rounded-xl">
                        <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                          <thead className="bg-slate-50 font-semibold text-slate-600">
                            <tr>
                              <th className="px-3.5 py-2">Parameter</th>
                              <th className="px-3.5 py-2">Type</th>
                              <th className="px-3.5 py-2">Required</th>
                              <th className="px-3.5 py-2">Description</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 text-slate-700 bg-white">
                            {ep.params.map((p, i) => (
                              <tr key={i} className="hover:bg-slate-50/50">
                                <td className="px-3.5 py-2.5 font-mono font-semibold text-brand-700">
                                  {p.name}
                                </td>
                                <td className="px-3.5 py-2.5 font-mono text-slate-500">{p.type}</td>
                                <td className="px-3.5 py-2.5">
                                  {p.required ? (
                                    <span className="text-red-700 bg-red-50 px-1.5 py-0.5 rounded font-semibold text-2xs">
                                      Yes
                                    </span>
                                  ) : (
                                    <span className="text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded text-2xs">
                                      No
                                    </span>
                                  )}
                                </td>
                                <td className="px-3.5 py-2.5">
                                  {p.description}{' '}
                                  {p.example && (
                                    <span className="text-slate-400 font-mono text-2xs ml-1">
                                      (e.g. {p.example})
                                    </span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Real Response Example */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                        Response Schema Example (HTTP 200 OK)
                      </h4>
                      <button
                        onClick={() =>
                          handleCopy(JSON.stringify(ep.response, null, 2), `res-${ep.id}`)
                        }
                        className="inline-flex items-center space-x-1 text-xs text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
                      >
                        {copiedId === `res-${ep.id}` ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                            <span className="text-emerald-700">Copied JSON</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Copy JSON</span>
                          </>
                        )}
                      </button>
                    </div>

                    <div className="bg-slate-900 text-slate-100 p-4 rounded-xl text-xs font-mono overflow-x-auto max-h-72 shadow-inner">
                      <pre>{JSON.stringify(ep.response, null, 2)}</pre>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Integration Code Examples */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2">
                <Code2 className="w-5 h-5 text-brand-600" />
                <span>Integration Code Examples</span>
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 mt-1">
                Complete, production-tested examples demonstrating session fetching and error handling.
              </p>
            </div>

            {/* Code Tabs */}
            <div className="flex p-1 bg-slate-100 rounded-xl space-x-1 self-start sm:self-auto">
              <button
                onClick={() => setActiveCodeTab('javascript')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                  activeCodeTab === 'javascript'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                JavaScript (fetch)
              </button>
              <button
                onClick={() => setActiveCodeTab('python')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                  activeCodeTab === 'python'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Python (requests)
              </button>
              <button
                onClick={() => setActiveCodeTab('curl')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                  activeCodeTab === 'curl'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                cURL / REST
              </button>
            </div>
          </div>

          {/* Active Code Snippet */}
          <div className="relative">
            <div className="bg-slate-900 text-slate-100 p-5 rounded-xl font-mono text-xs sm:text-sm overflow-x-auto shadow-inner leading-relaxed">
              <pre>
                {activeCodeTab === 'javascript'
                  ? jsFetchExample
                  : activeCodeTab === 'python'
                  ? pythonExample
                  : curlExample}
              </pre>
            </div>

            <button
              onClick={() =>
                handleCopy(
                  activeCodeTab === 'javascript'
                    ? jsFetchExample
                    : activeCodeTab === 'python'
                    ? pythonExample
                    : curlExample,
                  'active-code'
                )
              }
              className="absolute top-4 right-4 inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition-colors shadow-sm cursor-pointer"
            >
              {copiedId === 'active-code' ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-300">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Code</span>
                </>
              )}
            </button>
          </div>
        </section>

        {/* Data Schema & Needs Review Explanation */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs space-y-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2">
              <Layers className="w-5 h-5 text-brand-600" />
              <span>Data Dictionary & Provenance Handling</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 mt-1">
              Field definitions for the atomic <code className="font-mono text-brand-700 bg-brand-50 px-1 py-0.5 rounded">TimetableSession</code> record.
            </p>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 font-semibold text-slate-600">
                <tr>
                  <th className="px-4 py-3">Field</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Description</th>
                  <th className="px-4 py-3">Example</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700 bg-white">
                <tr>
                  <td className="px-4 py-2.5 font-mono font-semibold text-brand-700">day</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">string</td>
                  <td className="px-4 py-2.5">Weekday name: Monday through Friday</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">"Friday"</td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 font-mono font-semibold text-brand-700">startTime</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">string</td>
                  <td className="px-4 py-2.5">24-hour normalized start time (HH:MM)</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">"08:30", "12:30"</td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 font-mono font-semibold text-brand-700">endTime</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">string</td>
                  <td className="px-4 py-2.5">24-hour normalized end time (HH:MM)</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">"09:30", "13:30"</td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 font-mono font-semibold text-brand-700">subjectCode</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">string | null</td>
                  <td className="px-4 py-2.5">Course identifier or department course code</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">"CMIS 2113", "ELPC 1+10"</td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 font-mono font-semibold text-brand-700">sessionType</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">string | null</td>
                  <td className="px-4 py-2.5">Teaching format: "Lecture", "Practical", "Tutorial"</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">"Lecture"</td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 font-mono font-semibold text-brand-700">group</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">string | null</td>
                  <td className="px-4 py-2.5">Practical lab group identifier if designated</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">"Gp. I", "Gp. ll"</td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 font-mono font-semibold text-brand-700">location</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">string | null</td>
                  <td className="px-4 py-2.5">Classroom, auditorium, or laboratory venue</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">"LR- 07", "ELTN Lab"</td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 font-mono font-semibold text-brand-700">rawCellText</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">string</td>
                  <td className="px-4 py-2.5">Exact unparsed text extracted from the PDF grid cell</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">"CMIS 2113 (L)\nLR- 07"</td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 font-mono font-semibold text-brand-700">validationStatus</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">string</td>
                  <td className="px-4 py-2.5">
                    <span className="font-semibold text-emerald-700">VALID</span> or{' '}
                    <span className="font-semibold text-amber-700">NEEDS_REVIEW</span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">"VALID"</td>
                </tr>
                <tr>
                  <td className="px-4 py-2.5 font-mono font-semibold text-brand-700">warnings</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">string[]</td>
                  <td className="px-4 py-2.5">Parser diagnostics explaining why validation was flagged</td>
                  <td className="px-4 py-2.5 font-mono text-slate-500">["Missing session type"]</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Deep dive on NEEDS_REVIEW */}
          <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-5 text-amber-900 text-xs sm:text-sm space-y-2">
            <h4 className="font-bold flex items-center space-x-2 text-amber-950">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>Displaying Review Warnings to Students (Do Not Silently Confirm)</span>
            </h4>
            <p className="leading-relaxed">
              Timetable notices published by the faculty occasionally contain non-standard course codes
              (e.g., <code className="bg-amber-100 px-1 py-0.5 rounded font-mono">ELPC 1+10</code>) or missing
              session format annotations. Rather than silently correcting or dropping these, the coordinate-aware parser
              retains them with <code className="bg-amber-100 px-1 py-0.5 rounded font-mono">validationStatus: "NEEDS_REVIEW"</code>{' '}
              and captures diagnostics in <code className="bg-amber-100 px-1 py-0.5 rounded font-mono">warnings</code>.
            </p>
            <p className="leading-relaxed font-medium">
              Client applications must display an unverified badge or warning indicator alongside these entries
              so students are alerted to verify room schedules directly with their department.
            </p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-1">
          <p className="font-semibold text-slate-700">
            FAS WUSL Timetable API • Faculty of Applied Sciences, Wayamba University of Sri Lanka
          </p>
          <p>
            Free and public read-only service for university students, faculty, and developers.
          </p>
        </div>
      </footer>
    </div>
  );
}
