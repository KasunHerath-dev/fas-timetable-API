import React, { useState, useEffect, useMemo, useCallback } from 'react';
import Navbar, { GithubIcon } from './components/Navbar';
import StatusSummary from './components/StatusSummary';
import FilterControls from './components/FilterControls';
import WeeklyGrid from './components/WeeklyGrid';
import DailyView from './components/DailyView';
import SessionModal from './components/SessionModal';
import DeveloperDocs from './components/DeveloperDocs';
import ReadmeViewer from './components/ReadmeViewer';
import { getHealthStatus, getTimetables, getSessions, getLevelStatus } from './services/api';
import { AlertCircle, RefreshCw, Calendar, Search } from 'lucide-react';

export default function App() {
  // Client-side route state
  const [currentPath, setCurrentPath] = useState(() => {
    if (typeof window !== 'undefined' && window.location?.pathname) {
      return window.location.pathname;
    }
    return '/';
  });

  const navigateTo = useCallback((path) => {
    if (typeof window !== 'undefined') {
      window.history.pushState({}, '', path);
      setCurrentPath(path);
      window.scrollTo(0, 0);
    }
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Navigation & Level State
  const [selectedLevel, setSelectedLevel] = useState(1);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'daily'
  const [selectedDay, setSelectedDay] = useState('Monday');

  // Academic Term Selection
  const [timetables, setTimetables] = useState([]);
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedSemester, setSelectedSemester] = useState('');

  // Filtering State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('All');

  // Data State
  const [sessions, setSessions] = useState([]);
  const [status, setStatus] = useState(null);
  const [health, setHealth] = useState(null);

  // UI State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeModalSession, setActiveModalSession] = useState(null);

  // Initial Load: Health check & Timetables list
  const loadInitialData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthData, ttsData] = await Promise.all([
        getHealthStatus().catch(() => ({ status: 'ok', database: 'offline' })),
        getTimetables(),
      ]);

      setHealth(healthData);
      setTimetables(ttsData || []);

      // Determine initial academic year & semester
      if (ttsData && ttsData.length > 0) {
        const lvl1 = ttsData.find((t) => t.level === 1) || ttsData[0];
        setSelectedYear(lvl1.academicYear);
        setSelectedSemester(lvl1.semester);
      }
    } catch (err) {
      console.error('Initial data load error:', err);
      setError('Unable to reach the timetable backend. Please ensure the API service is running.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (
      currentPath === '/developers' ||
      currentPath.startsWith('/developers') ||
      currentPath === '/readme' ||
      currentPath.startsWith('/readme')
    ) {
      return;
    }
    loadInitialData();
  }, [loadInitialData, currentPath]);

  // Load Sessions & Status whenever Level, Year, or Semester change
  const loadLevelData = useCallback(async () => {
    if (!selectedLevel) return;
    setLoading(true);
    setError(null);

    try {
      const [sessionsData, statusData] = await Promise.all([
        getSessions(selectedLevel, {
          academicYear: selectedYear,
          semester: selectedSemester,
        }),
        getLevelStatus(selectedLevel, selectedYear, selectedSemester),
      ]);

      setSessions(sessionsData.sessions || []);
      setStatus(statusData);

      // Keep year and semester in sync if resolved by backend
      if (sessionsData.academicYear && !selectedYear) {
        setSelectedYear(sessionsData.academicYear);
      }
      if (sessionsData.semester && !selectedSemester) {
        setSelectedSemester(sessionsData.semester);
      }
    } catch (err) {
      console.error('Level data load error:', err);
      setError(`Failed to retrieve timetable sessions for Level ${selectedLevel}.`);
    } finally {
      setLoading(false);
    }
  }, [selectedLevel, selectedYear, selectedSemester]);

  useEffect(() => {
    if (
      currentPath === '/developers' ||
      currentPath.startsWith('/developers') ||
      currentPath === '/readme' ||
      currentPath.startsWith('/readme')
    ) {
      return;
    }
    loadLevelData();
  }, [loadLevelData, currentPath]);

  // Derive unique academic years and semesters available for the selected level
  const { academicYears, semesters, currentMetadata } = useMemo(() => {
    const levelTts = timetables.filter((t) => t.level === selectedLevel);
    const yrs = Array.from(new Set(levelTts.map((t) => t.academicYear))).filter(Boolean);
    const sems = Array.from(new Set(levelTts.map((t) => t.semester))).filter(Boolean);

    // Fallbacks if empty
    if (yrs.length === 0) yrs.push('2024/2025');
    if (sems.length === 0) sems.push('Semester I');

    const meta = levelTts.find(
      (t) =>
        (!selectedYear || t.academicYear === selectedYear) &&
        (!selectedSemester || t.semester === selectedSemester)
    ) || levelTts[0];

    return {
      academicYears: yrs,
      semesters: sems,
      currentMetadata: meta,
    };
  }, [timetables, selectedLevel, selectedYear, selectedSemester]);

  // Filtered Sessions (by subject code search and session type)
  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      // Filter by subject code search
      if (searchQuery.trim()) {
        const query = searchQuery.trim().toLowerCase();
        const code = (s.subjectCode || '').toLowerCase();
        const loc = (s.location || '').toLowerCase();
        if (!code.includes(query) && !loc.includes(query)) return false;
      }

      // Filter by session type
      if (selectedType !== 'All') {
        if (s.sessionType !== selectedType) return false;
      }

      return true;
    });
  }, [sessions, searchQuery, selectedType]);

  // Handle switching level
  const handleSelectLevel = (lvl) => {
    setSelectedLevel(lvl);
    setSearchQuery('');
    setSelectedType('All');

    // Auto-update term for the new level
    const lvlTts = timetables.filter((t) => t.level === lvl);
    if (lvlTts.length > 0) {
      setSelectedYear(lvlTts[0].academicYear);
      setSelectedSemester(lvlTts[0].semester);
    }
  };

  // Route switch: Project README Viewer
  if (currentPath === '/readme' || currentPath.startsWith('/readme')) {
    return (
      <ReadmeViewer
        onNavigateHome={() => navigateTo('/')}
        onNavigateToDevelopers={() => navigateTo('/developers')}
      />
    );
  }

  // Route switch: Developer API Documentation
  if (currentPath === '/developers' || currentPath.startsWith('/developers')) {
    return (
      <DeveloperDocs
        onNavigateHome={() => navigateTo('/')}
        onNavigateToReadme={() => navigateTo('/readme')}
      />
    );
  }

  return (
    <div className="min-h-screen bg-slate-100/70 text-slate-800 flex flex-col font-sans">
      {/* Top Navbar */}
      <Navbar
        health={health}
        onRefresh={loadLevelData}
        loading={loading}
        onNavigateToDevelopers={() => navigateTo('/developers')}
        onNavigateToReadme={() => navigateTo('/readme')}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-xl flex items-center justify-between mb-6 shadow-xs">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
              <span className="text-sm font-medium">{error}</span>
            </div>
            <button
              onClick={loadLevelData}
              className="text-xs bg-red-100 hover:bg-red-200 text-red-900 px-3 py-1.5 rounded-lg font-semibold transition-colors cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* Timetable Status Summary Bar */}
        <StatusSummary
          metadata={currentMetadata}
          status={status}
          selectedLevel={selectedLevel}
        />

        {/* Filter & Control Bar */}
        <FilterControls
          selectedLevel={selectedLevel}
          onSelectLevel={handleSelectLevel}
          academicYears={academicYears}
          selectedYear={selectedYear}
          onSelectYear={setSelectedYear}
          semesters={semesters}
          selectedSemester={selectedSemester}
          onSelectSemester={setSelectedSemester}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          selectedType={selectedType}
          onSelectType={setSelectedType}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          selectedDay={selectedDay}
          onSelectDay={setSelectedDay}
        />

        {/* Content Body: Loading, Empty, or Timetable View */}
        {loading && sessions.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
            <RefreshCw className="w-8 h-8 text-brand-600 animate-spin mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-800">
              Loading Level {selectedLevel} Timetable...
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Retrieving parsed schedule sessions from MongoDB Atlas
            </p>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mx-auto mb-3">
              <Search className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-semibold text-slate-800 mb-1">
              No matching sessions found
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">
              {searchQuery
                ? `No sessions matched "${searchQuery}". Check the subject code spelling or clear the search filter.`
                : 'There are no sessions for the selected filters.'}
            </p>
            {(searchQuery || selectedType !== 'All') && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedType('All');
                }}
                className="px-3.5 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold rounded-lg transition-colors cursor-pointer"
              >
                Reset Filters
              </button>
            )}
          </div>
        ) : viewMode === 'grid' ? (
          <WeeklyGrid
            sessions={filteredSessions}
            onSessionClick={(session) => setActiveModalSession(session)}
          />
        ) : (
          <DailyView
            sessions={filteredSessions}
            selectedDay={selectedDay}
            onSessionClick={(session) => setActiveModalSession(session)}
          />
        )}
      </main>

      {/* Session Details Modal */}
      <SessionModal
        session={activeModalSession}
        onClose={() => setActiveModalSession(null)}
      />

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-8 text-center text-xs text-slate-500 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-3">
          <p className="font-semibold text-slate-700">
            Faculty of Applied Sciences • Wayamba University of Sri Lanka (WUSL)
          </p>
          <p>
            Data synchronized from official timetable PDF releases via coordinate-aware parsing.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-slate-600 pt-1">
            <a
              href="/developers"
              onClick={(e) => {
                e.preventDefault();
                navigateTo('/developers');
              }}
              className="text-brand-600 hover:text-brand-800 font-medium underline inline-flex items-center space-x-1"
            >
              <span>Developer API Documentation</span>
            </a>
            <span className="text-slate-300">•</span>
            <a
              href="/readme"
              onClick={(e) => {
                e.preventDefault();
                navigateTo('/readme');
              }}
              className="text-brand-600 hover:text-brand-800 font-medium underline inline-flex items-center space-x-1"
            >
              <span>Project README</span>
            </a>
            <span className="text-slate-300">•</span>
            <a
              href="https://github.com/KasunHerath-dev/fas-timetable-downloader"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-600 hover:text-slate-900 font-medium inline-flex items-center space-x-1.5"
            >
              <GithubIcon className="w-3.5 h-3.5" />
              <span>GitHub Repository</span>
            </a>
          </div>
          <p className="text-[11px] text-slate-400 pt-1">
            Maintained by{' '}
            <a
              href="https://github.com/KasunHerath-dev"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-slate-600 hover:text-brand-600 underline"
            >
              Kasun Herath
            </a>{' '}
            • Open Source Under MIT License
          </p>
        </div>
      </footer>
    </div>
  );
}
