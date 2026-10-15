import React, { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import readmeContent from 'virtual:readme';
import {
  BookOpen,
  ArrowLeft,
  Copy,
  Check,
  Share2,
  ExternalLink,
  Code2,
  Calendar,
  Search,
  ChevronRight,
  Menu,
  X,
  FileText,
} from 'lucide-react';

export function GithubIcon({ className = 'w-4 h-4' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      />
    </svg>
  );
}

// Helper to convert heading text to a clean URL-friendly ID
export function slugify(text) {
  return String(text)
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-');
}

// Parses markdown headings (H1-H3) into table of contents entries
export function extractHeadings(markdownText) {
  if (!markdownText) return [];
  const lines = markdownText.split('\n');
  const headings = [];
  lines.forEach((line) => {
    const match = line.match(/^(#{1,3})\s+(.+)$/);
    if (match) {
      const level = match[1].length;
      const rawTitle = match[2].trim();
      const text = rawTitle.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/[*`_]/g, '');
      headings.push({
        id: slugify(text),
        text,
        title: text,
        level,
      });
    }
  });
  return headings;
}

export default function ReadmeViewer({ onNavigateHome, onNavigateToDevelopers }) {
  const [copiedId, setCopiedId] = useState(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [showTocMobile, setShowTocMobile] = useState(false);

  const shareUrl =
    typeof window !== 'undefined'
      ? `${window.location.origin}/readme`
      : '/readme';

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

  // Extract table of contents (H2 headings) from the markdown content
  const tableOfContents = useMemo(() => {
    return extractHeadings(readmeContent).filter((h) => h.level === 2);
  }, []);

  const filteredToc = useMemo(() => {
    if (!searchFilter.trim()) return tableOfContents;
    const q = searchFilter.toLowerCase();
    return tableOfContents.filter((item) => item.title.toLowerCase().includes(q));
  }, [tableOfContents, searchFilter]);

  // Custom component renderers for react-markdown
  const markdownComponents = {
    h1: ({ children, ...props }) => {
      const text = String(children);
      const id = slugify(text);
      return (
        <h1
          id={id}
          className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mt-8 mb-4 border-b border-slate-200 pb-3 flex items-center group scroll-mt-24"
          {...props}
        >
          <span>{children}</span>
        </h1>
      );
    },
    h2: ({ children, ...props }) => {
      const text = String(children);
      const id = slugify(text);
      return (
        <h2
          id={id}
          className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight mt-8 mb-3.5 border-b border-slate-100 pb-2 flex items-center group scroll-mt-24"
          {...props}
        >
          <span className="text-brand-600 mr-2 opacity-0 group-hover:opacity-100 transition-opacity select-none text-base">
            #
          </span>
          <span>{children}</span>
        </h2>
      );
    },
    h3: ({ children, ...props }) => {
      const text = String(children);
      const id = slugify(text);
      return (
        <h3
          id={id}
          className="text-base sm:text-lg font-bold text-slate-800 tracking-tight mt-6 mb-2 flex items-center scroll-mt-24"
          {...props}
        >
          <span>{children}</span>
        </h3>
      );
    },
    h4: ({ children, ...props }) => (
      <h4 className="text-sm sm:text-base font-semibold text-slate-800 mt-4 mb-1.5" {...props}>
        {children}
      </h4>
    ),
    p: ({ children, ...props }) => (
      <p className="text-xs sm:text-sm text-slate-700 leading-relaxed mb-4" {...props}>
        {children}
      </p>
    ),
    ul: ({ children, ...props }) => (
      <ul className="list-disc pl-5 sm:pl-6 space-y-1.5 text-xs sm:text-sm text-slate-700 mb-4" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }) => (
      <ol className="list-decimal pl-5 sm:pl-6 space-y-1.5 text-xs sm:text-sm text-slate-700 mb-4" {...props}>
        {children}
      </ol>
    ),
    li: ({ children, ...props }) => (
      <li className="leading-relaxed" {...props}>
        {children}
      </li>
    ),
    blockquote: ({ children, ...props }) => (
      <blockquote
        className="border-l-4 border-brand-500 bg-slate-50 pl-4 pr-3 py-3 rounded-r-xl my-4 text-xs sm:text-sm text-slate-700 italic border border-slate-200"
        {...props}
      >
        {children}
      </blockquote>
    ),
    table: ({ children, ...props }) => (
      <div className="overflow-x-auto my-6 border border-slate-200 rounded-xl shadow-2xs bg-white">
        <table className="min-w-full divide-y divide-slate-200 text-left text-xs" {...props}>
          {children}
        </table>
      </div>
    ),
    thead: ({ children, ...props }) => (
      <thead className="bg-slate-50 font-semibold text-slate-700" {...props}>
        {children}
      </thead>
    ),
    tbody: ({ children, ...props }) => (
      <tbody className="divide-y divide-slate-100 bg-white" {...props}>
        {children}
      </tbody>
    ),
    th: ({ children, ...props }) => (
      <th className="px-3.5 sm:px-4 py-2.5 font-semibold text-slate-800 text-xs whitespace-nowrap" {...props}>
        {children}
      </th>
    ),
    td: ({ children, ...props }) => (
      <td className="px-3.5 sm:px-4 py-2.5 text-slate-700 text-xs" {...props}>
        {children}
      </td>
    ),
    pre: ({ children, ...props }) => {
      // Find the code content to allow copying
      let codeString = '';
      if (children && children.props && children.props.children) {
        codeString = String(children.props.children).replace(/\n$/, '');
      }
      const codeId = `code_${Math.random().toString(36).substring(2, 8)}`;

      return (
        <div className="relative group my-4">
          <pre
            className="bg-slate-900 text-slate-100 p-4 rounded-xl overflow-x-auto text-xs font-mono shadow-inner leading-relaxed border border-slate-800"
            {...props}
          >
            {children}
          </pre>
          {codeString && (
            <button
              onClick={() => handleCopy(codeString, codeId)}
              className="absolute top-2.5 right-2.5 inline-flex items-center space-x-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md text-[11px] font-medium transition-colors shadow-2xs opacity-80 group-hover:opacity-100 cursor-pointer"
              title="Copy code to clipboard"
            >
              {copiedId === codeId ? (
                <>
                  <Check className="w-3 h-3 text-emerald-400" />
                  <span className="text-emerald-300">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          )}
        </div>
      );
    },
    code: ({ node, inline, className, children, ...props }) => {
      if (inline || !className) {
        return (
          <code
            className="font-mono text-xs px-1.5 py-0.5 rounded bg-slate-100 text-brand-700 font-semibold border border-slate-200 break-words"
            {...props}
          >
            {children}
          </code>
        );
      }
      return <code className={className} {...props}>{children}</code>;
    },
    a: ({ href, children, ...props }) => {
      const isInternal = href && (href.startsWith('#') || href.startsWith('/'));
      return (
        <a
          href={href}
          target={isInternal ? undefined : '_blank'}
          rel={isInternal ? undefined : 'noopener noreferrer'}
          className="text-brand-600 hover:text-brand-800 font-medium underline underline-offset-2 break-words inline-flex items-center gap-0.5"
          {...props}
        >
          <span>{children}</span>
          {!isInternal && <ExternalLink className="w-3 h-3 inline-block ml-0.5 opacity-70" />}
        </a>
      );
    },
    hr: () => <hr className="my-8 border-slate-200" />,
    img: ({ src, alt, ...props }) => (
      <img
        src={src}
        alt={alt || 'Documentation diagram'}
        className="max-w-full h-auto rounded-xl shadow-xs border border-slate-200 my-4"
        loading="lazy"
        onError={(e) => {
          e.target.style.display = 'none';
        }}
        {...props}
      />
    ),
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      {/* Top Sticky Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16 sm:h-20">
            {/* Left: Branding & Back Button */}
            <div className="flex items-center space-x-2 sm:space-x-3">
              <button
                onClick={onNavigateHome}
                className="p-2 -ml-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                title="Return to Student Timetable Portal"
                aria-label="Back to Timetables"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>

              <div className="w-9 h-9 sm:w-11 sm:h-11 rounded-xl bg-gradient-to-tr from-brand-700 to-indigo-600 flex items-center justify-center text-white shadow-sm ring-2 ring-brand-100 shrink-0">
                <FileText className="w-5 h-5 sm:w-6 sm:h-6" />
              </div>

              <div>
                <div className="flex items-center space-x-1.5 sm:space-x-2">
                  <span className="text-[10px] sm:text-xs font-bold uppercase tracking-wider text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
                    Documentation
                  </span>
                  <span className="text-xs text-slate-500 hidden md:inline">
                    Faculty of Applied Sciences • WUSL
                  </span>
                </div>
                <h1 className="text-sm sm:text-lg font-bold text-slate-900 tracking-tight leading-tight truncate">
                  Project README
                </h1>
              </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center space-x-1.5 sm:space-x-2">
              <button
                onClick={() => handleCopy(shareUrl, 'share-readme')}
                className="inline-flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-2xs transition-colors cursor-pointer"
                title="Copy shareable link to this README viewer"
              >
                {copiedId === 'share-readme' ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="text-emerald-700 hidden sm:inline">Copied</span>
                  </>
                ) : (
                  <>
                    <Share2 className="w-3.5 h-3.5 text-slate-500" />
                    <span className="hidden sm:inline">Share</span>
                  </>
                )}
              </button>

              {onNavigateToDevelopers && (
                <button
                  onClick={onNavigateToDevelopers}
                  className="inline-flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-2xs transition-colors cursor-pointer"
                  title="View Developer API Documentation"
                >
                  <Code2 className="w-3.5 h-3.5 text-brand-600" />
                  <span className="hidden sm:inline">API Docs</span>
                  <span className="sm:hidden">API</span>
                </button>
              )}

              <a
                href="https://github.com/KasunHerath-dev/fas-timetable-downloader"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-2xs transition-colors"
                title="View repository on GitHub"
              >
                <GithubIcon className="w-3.5 h-3.5 text-slate-800" />
                <span className="hidden md:inline">GitHub</span>
              </a>

              <button
                onClick={onNavigateHome}
                className="inline-flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200 rounded-lg transition-colors cursor-pointer"
                aria-label="Student Timetable Portal"
              >
                <Calendar className="w-3.5 h-3.5 text-brand-600" />
                <span className="hidden sm:inline">Timetable</span>
                <span className="sm:hidden">App</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Layout */}
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 flex-1">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
          {/* Table of Contents Sidebar (Desktop) */}
          <aside className="hidden lg:block lg:col-span-1 sticky top-28 bg-white border border-slate-200 rounded-2xl p-4 shadow-xs max-h-[calc(100vh-8rem)] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center space-x-1.5">
                <BookOpen className="w-3.5 h-3.5 text-brand-600" />
                <span>Table of Contents</span>
              </h2>
              <span className="text-[10px] font-semibold text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                {tableOfContents.length} sections
              </span>
            </div>

            {/* TOC Search Input */}
            <div className="relative mb-3">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Filter sections..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white text-slate-800"
              />
            </div>

            <nav className="space-y-1">
              {filteredToc.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className="block px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-brand-700 hover:bg-brand-50/60 transition-colors truncate"
                  title={item.title}
                >
                  {item.title}
                </a>
              ))}
            </nav>

            {/* Developer Credit Card */}
            <div className="mt-6 pt-4 border-t border-slate-100 space-y-2">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Project Maintainer
              </div>
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/80">
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-xs">
                    KH
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-slate-900">Kasun Herath</h3>
                    <a
                      href="https://github.com/KasunHerath-dev"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-brand-600 hover:underline flex items-center gap-1 font-medium"
                    >
                      <GithubIcon className="w-3 h-3 text-slate-700" />
                      <span>@KasunHerath-dev</span>
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Markdown Body */}
          <main className="lg:col-span-3 bg-white rounded-2xl border border-slate-200 p-6 sm:p-10 shadow-xs overflow-hidden">
            {/* Mobile TOC Accordion Button */}
            <div className="lg:hidden mb-6 pb-4 border-b border-slate-200">
              <button
                onClick={() => setShowTocMobile(!showTocMobile)}
                className="w-full flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 transition-colors cursor-pointer"
              >
                <span className="flex items-center space-x-2">
                  <BookOpen className="w-4 h-4 text-brand-600" />
                  <span>Jump to Section ({tableOfContents.length} Sections)</span>
                </span>
                <ChevronRight
                  className={`w-4 h-4 text-slate-400 transition-transform ${
                    showTocMobile ? 'rotate-90' : ''
                  }`}
                />
              </button>

              {showTocMobile && (
                <div className="mt-2 p-3 bg-white border border-slate-200 rounded-xl max-h-64 overflow-y-auto space-y-1">
                  {tableOfContents.map((item) => (
                    <a
                      key={item.id}
                      href={`#${item.id}`}
                      onClick={() => setShowTocMobile(false)}
                      className="block px-2.5 py-1.5 text-xs text-slate-600 hover:text-brand-700 hover:bg-brand-50 rounded-lg truncate"
                    >
                      {item.title}
                    </a>
                  ))}
                </div>
              )}
            </div>

            {/* Rendered Markdown Output */}
            <article className="prose prose-slate max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {readmeContent}
              </ReactMarkdown>
            </article>

            {/* Bottom Developer Credits Section */}
            <div className="mt-12 pt-8 border-t border-slate-200 bg-slate-50/80 -mx-6 -mb-6 sm:-mx-10 sm:-mb-10 p-6 sm:p-8 rounded-b-2xl">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-brand-700 bg-brand-50 px-2 py-0.5 rounded border border-brand-200">
                    Open Source Project
                  </span>
                  <h3 className="text-base font-bold text-slate-900 mt-1">
                    FAS WUSL Timetable Downloader & Portal
                  </h3>
                  <p className="text-xs text-slate-600 mt-1 max-w-lg">
                    Created and maintained by <strong>Kasun Herath</strong>. Free and public tool for students, faculty, and developers of Wayamba University of Sri Lanka.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  <a
                    href="https://github.com/KasunHerath-dev"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 rounded-lg shadow-2xs transition-colors"
                  >
                    <GithubIcon className="w-3.5 h-3.5 text-slate-800" />
                    <span>Developer Profile</span>
                  </a>

                  <a
                    href="https://github.com/KasunHerath-dev/fas-timetable-downloader"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-2xs transition-colors"
                  >
                    <GithubIcon className="w-3.5 h-3.5" />
                    <span>View Repository</span>
                  </a>
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-2">
          <p className="font-semibold text-slate-700">
            FAS WUSL Timetable Downloader • Faculty of Applied Sciences, Wayamba University of Sri Lanka
          </p>
          <div className="flex items-center justify-center space-x-3 text-xs">
            <button
              onClick={onNavigateHome}
              className="text-brand-600 hover:underline cursor-pointer"
            >
              Student Portal
            </button>
            <span>•</span>
            {onNavigateToDevelopers && (
              <button
                onClick={onNavigateToDevelopers}
                className="text-brand-600 hover:underline cursor-pointer"
              >
                Developer API
              </button>
            )}
            <span>•</span>
            <a
              href="https://github.com/KasunHerath-dev/fas-timetable-downloader"
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-600 hover:underline inline-flex items-center gap-1"
            >
              <GithubIcon className="w-3 h-3" />
              <span>GitHub</span>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
