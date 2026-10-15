import React from 'react';
import { Calendar, Database, CheckCircle2, AlertCircle, RefreshCw, Code2 } from 'lucide-react';

export default function Navbar({ health, onRefresh, loading, onNavigateToDevelopers }) {
  const isConnected = health?.database === 'connected';

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16 sm:h-20">
          {/* Brand & Faculty Info */}
          <div className="flex items-center space-x-3 sm:space-x-4">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-tr from-brand-700 to-indigo-600 flex items-center justify-center text-white shadow-sm ring-2 ring-brand-100">
              <Calendar className="w-5 h-5 sm:w-6 sm:h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold uppercase tracking-wider text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
                  FAS • WUSL
                </span>
                <span className="text-xs text-slate-500 hidden sm:inline">
                  Wayamba University of Sri Lanka
                </span>
              </div>
              <h1 className="text-base sm:text-xl font-bold text-slate-900 tracking-tight leading-tight">
                Academic Timetable Portal
              </h1>
            </div>
          </div>

          {/* Right Actions: Developer API, System Health & Refresh */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            {onNavigateToDevelopers && (
              <button
                onClick={onNavigateToDevelopers}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-2xs transition-colors cursor-pointer"
                title="View Developer API Documentation"
              >
                <Code2 className="w-3.5 h-3.5 text-brand-600" />
                <span className="hidden sm:inline">Developer API</span>
                <span className="sm:hidden">API</span>
              </button>
            )}
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
              <span className="hidden sm:inline">
                {isConnected ? 'Atlas Connected' : 'Database Offline'}
              </span>
              <span className="sm:hidden">{isConnected ? 'Online' : 'Offline'}</span>
            </div>

            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200 disabled:opacity-50"
              title="Refresh Timetable Data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-brand-600' : ''}`} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
