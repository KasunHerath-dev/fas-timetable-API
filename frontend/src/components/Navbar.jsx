import React, { useState } from 'react';
import {
  Calendar,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Code2,
  FileText,
  Menu,
  X,
  ExternalLink,
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

export default function Navbar({
  health,
  onRefresh,
  loading,
  onNavigateToDevelopers,
  onNavigateToReadme,
  onNavigateToAcademicCalendar,
  currentPath = '/',
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const isConnected = health?.database === 'connected';

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-3.5 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16 sm:h-20">
          {/* Brand & Faculty Info */}
          <div className="flex items-center space-x-2.5 sm:space-x-3.5 min-w-0">
            <div className="w-9 h-9 sm:w-11 sm:h-11 rounded-xl bg-gradient-to-tr from-brand-700 to-indigo-600 flex items-center justify-center text-white shadow-sm ring-2 ring-brand-100 shrink-0">
              <Calendar className="w-5 h-5 sm:w-6 sm:h-6" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-1.5 sm:space-x-2">
                <span className="text-[10px] sm:text-xs font-bold uppercase tracking-wider text-brand-700 bg-brand-50 px-1.5 sm:px-2 py-0.5 rounded shrink-0">
                  FAS • WUSL
                </span>
                <span className="text-xs text-slate-500 hidden md:inline truncate">
                  Wayamba University of Sri Lanka
                </span>
              </div>
              <h1 className="text-sm sm:text-lg font-bold text-slate-900 tracking-tight leading-tight truncate">
                Academic Timetable Portal
              </h1>
            </div>
          </div>

          {/* Desktop Right Actions */}
          <div className="hidden md:flex items-center space-x-2 sm:space-x-2.5">
            {onNavigateToAcademicCalendar && (
              <button
                onClick={onNavigateToAcademicCalendar}
                className={`inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors cursor-pointer ${
                  currentPath === '/academic-calendar'
                    ? 'bg-brand-50 text-brand-700 border-brand-200'
                    : 'text-slate-700 bg-white hover:bg-slate-50 border-slate-300 shadow-2xs'
                }`}
                title="View Academic Calendar Explorer"
              >
                <Calendar className="w-3.5 h-3.5 text-brand-600" />
                <span>Academic Calendar</span>
              </button>
            )}

            {onNavigateToReadme && (
              <button
                onClick={onNavigateToReadme}
                className={`inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors cursor-pointer ${
                  currentPath === '/readme'
                    ? 'bg-brand-50 text-brand-700 border-brand-200'
                    : 'text-slate-700 bg-white hover:bg-slate-50 border-slate-300 shadow-2xs'
                }`}
                title="View Project README and Architecture"
              >
                <FileText className="w-3.5 h-3.5 text-brand-600" />
                <span>README</span>
              </button>
            )}

            {onNavigateToDevelopers && (
              <button
                onClick={onNavigateToDevelopers}
                className={`inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors cursor-pointer ${
                  currentPath === '/developers'
                    ? 'bg-brand-50 text-brand-700 border-brand-200'
                    : 'text-slate-700 bg-white hover:bg-slate-50 border-slate-300 shadow-2xs'
                }`}
                title="View Developer API Documentation"
              >
                <Code2 className="w-3.5 h-3.5 text-brand-600" />
                <span>Developer API</span>
              </button>
            )}

            <a
              href="https://github.com/KasunHerath-dev/fas-timetable-downloader"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-2xs transition-colors"
              title="View repository on GitHub"
            >
              <GithubIcon className="w-3.5 h-3.5 text-slate-800" />
              <span>GitHub</span>
            </a>

            {/* Health status */}
            <div
              className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
                isConnected
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}
              title={isConnected ? 'Connected to MongoDB Atlas' : 'Database Offline'}
            >
              {isConnected ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
              )}
              <span>{isConnected ? 'Atlas Connected' : 'Database Offline'}</span>
            </div>

            {/* Refresh */}
            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200 disabled:opacity-50 cursor-pointer"
              title="Refresh Timetable Data"
              aria-label="Refresh Timetable Data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-brand-600' : ''}`} />
            </button>
          </div>

          {/* Mobile Right Action Bar */}
          <div className="flex md:hidden items-center space-x-1 sm:space-x-1.5">
            {/* Status indicator on mobile */}
            <div
              className={`p-1.5 rounded-full border ${
                isConnected
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}
              title={isConnected ? 'Connected to MongoDB Atlas' : 'Database Offline'}
              aria-label={isConnected ? 'Atlas Connected' : 'Database Offline'}
            >
              {isConnected ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
              )}
            </div>

            {/* Refresh button */}
            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg border border-slate-200 disabled:opacity-50 cursor-pointer"
              title="Refresh Data"
              aria-label="Refresh Data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-brand-600' : ''}`} />
            </button>

            {/* Hamburger Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 text-slate-700 hover:bg-slate-100 rounded-lg border border-slate-200 cursor-pointer"
              aria-label="Toggle navigation menu"
              title="Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 py-3 space-y-2 shadow-lg animate-in slide-in-from-top-2 duration-150">
          <div className="grid grid-cols-3 gap-2 pb-2 border-b border-slate-100">
            {onNavigateToAcademicCalendar && (
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  onNavigateToAcademicCalendar();
                }}
                className="flex items-center space-x-1.5 px-2.5 py-2 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 rounded-lg border border-slate-200 cursor-pointer"
              >
                <Calendar className="w-3.5 h-3.5 text-brand-600 shrink-0" />
                <span className="truncate">Calendar</span>
              </button>
            )}

            {onNavigateToReadme && (
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  onNavigateToReadme();
                }}
                className="flex items-center space-x-1.5 px-2.5 py-2 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 rounded-lg border border-slate-200 cursor-pointer"
              >
                <FileText className="w-3.5 h-3.5 text-brand-600 shrink-0" />
                <span className="truncate">README</span>
              </button>
            )}

            {onNavigateToDevelopers && (
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  onNavigateToDevelopers();
                }}
                className="flex items-center space-x-1.5 px-2.5 py-2 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 rounded-lg border border-slate-200 cursor-pointer"
              >
                <Code2 className="w-3.5 h-3.5 text-brand-600 shrink-0" />
                <span className="truncate">API</span>
              </button>
            )}
          </div>

          <div className="flex flex-col space-y-2 pt-1 text-xs">
            <a
              href="https://github.com/KasunHerath-dev/fas-timetable-downloader"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between px-3 py-2 text-slate-700 hover:bg-slate-50 rounded-lg font-medium"
            >
              <span className="flex items-center space-x-2">
                <GithubIcon className="w-4 h-4 text-slate-800" />
                <span>GitHub Repository</span>
              </span>
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </a>

            <a
              href="https://github.com/KasunHerath-dev"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between px-3 py-2 text-slate-700 hover:bg-slate-50 rounded-lg font-medium"
            >
              <span className="flex items-center space-x-2">
                <GithubIcon className="w-4 h-4 text-slate-800" />
                <span>Maintainer: Kasun Herath</span>
              </span>
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
