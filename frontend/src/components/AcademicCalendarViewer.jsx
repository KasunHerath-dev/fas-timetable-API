import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Calendar,
  CheckCircle2,
  AlertCircle,
  Clock,
  ExternalLink,
  RefreshCw,
  ArrowLeft,
  FileText,
  ShieldCheck,
  AlertTriangle,
  History,
  Info,
  CalendarDays,
  Sparkles,
} from 'lucide-react';
import {
  getAcademicCalendars,
  getCurrentAcademicCalendar,
  getAcademicCalendarStatus,
  getUpcomingActivities,
} from '../services/api';

const CATEGORY_STYLES = {
  academic_session: {
    bg: 'bg-indigo-50 border-indigo-200 text-indigo-900',
    badge: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    label: 'Academic Session',
    dot: 'bg-indigo-600',
  },
  mid_semester_vacation: {
    bg: 'bg-emerald-50 border-emerald-200 text-emerald-900',
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    label: 'Mid Semester Vacation',
    dot: 'bg-emerald-600',
  },
  study_leave: {
    bg: 'bg-amber-50 border-amber-200 text-amber-900',
    badge: 'bg-amber-100 text-amber-800 border-amber-200',
    label: 'Study Leave',
    dot: 'bg-amber-600',
  },
  examination: {
    bg: 'bg-rose-50 border-rose-200 text-rose-900',
    badge: 'bg-rose-100 text-rose-800 border-rose-200',
    label: 'Examination Period',
    dot: 'bg-rose-600',
  },
  christmas_vacation: {
    bg: 'bg-teal-50 border-teal-200 text-teal-900',
    badge: 'bg-teal-100 text-teal-800 border-teal-200',
    label: 'Christmas Vacation',
    dot: 'bg-teal-600',
  },
  new_year_vacation: {
    bg: 'bg-purple-50 border-purple-200 text-purple-900',
    badge: 'bg-purple-100 text-purple-800 border-purple-200',
    label: 'New Year Vacation',
    dot: 'bg-purple-600',
  },
  vacation: {
    bg: 'bg-emerald-50 border-emerald-200 text-emerald-900',
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    label: 'Vacation',
    dot: 'bg-emerald-600',
  },
  other: {
    bg: 'bg-slate-50 border-slate-200 text-slate-800',
    badge: 'bg-slate-100 text-slate-700 border-slate-200',
    label: 'Official Activity',
    dot: 'bg-slate-500',
  },
};

function formatDate(isoStr) {
  if (!isoStr) return 'N/A';
  try {
    const [year, month, day] = isoStr.split('-');
    const dt = new Date(parseInt(year, 10), parseInt(month, 10) - 1, parseInt(day, 10));
    return dt.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return isoStr;
  }
}

export default function AcademicCalendarViewer({ onNavigateHome, onNavigateToDevelopers }) {
  const [calendars, setCalendars] = useState([]);
  const [selectedCalendarId, setSelectedCalendarId] = useState('');
  const [syncStatus, setSyncStatus] = useState(null);
  const [upcoming, setUpcoming] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('semesters'); // 'semesters' | 'upcoming' | 'revisions'
  const [activeSemester, setActiveSemester] = useState('All');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cals, currentCal, statusData, upcomingData] = await Promise.all([
        getAcademicCalendars().catch(() => []),
        getCurrentAcademicCalendar().catch(() => null),
        getAcademicCalendarStatus().catch(() => null),
        getUpcomingActivities({ limit: 10 }).catch(() => ({ activities: [] })),
      ]);

      const calendarList = cals.length > 0 ? cals : currentCal ? [currentCal] : [];
      setCalendars(calendarList);
      setSyncStatus(statusData);
      setUpcoming(upcomingData?.activities || []);

      if (currentCal) {
        setSelectedCalendarId(currentCal.calendarId || currentCal.id);
      } else if (calendarList.length > 0) {
        setSelectedCalendarId(calendarList[0].calendarId || calendarList[0].id);
      }
    } catch (err) {
      console.error('Failed to load academic calendars:', err);
      setError('Unable to load official academic calendar records. Please check API connectivity.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const activeCalendar = useMemo(() => {
    if (!selectedCalendarId) return calendars[0] || null;
    return (
      calendars.find((c) => (c.calendarId || c.id) === selectedCalendarId) ||
      calendars[0] ||
      null
    );
  }, [calendars, selectedCalendarId]);

  const semestersAvailable = useMemo(() => {
    if (!activeCalendar?.activities) return [];
    return Array.from(new Set(activeCalendar.activities.map((a) => a.semester))).filter(Boolean);
  }, [activeCalendar]);

  const filteredActivities = useMemo(() => {
    if (!activeCalendar?.activities) return [];
    if (activeSemester === 'All') return activeCalendar.activities;
    return activeCalendar.activities.filter((a) => a.semester === activeSemester);
  }, [activeCalendar, activeSemester]);

  return (
    <div className="min-h-screen bg-slate-100/70 text-slate-800 flex flex-col font-sans">
      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16 sm:h-20">
            <div className="flex items-center space-x-3 min-w-0">
              <button
                onClick={onNavigateHome}
                className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200 cursor-pointer"
                title="Back to Timetable Explorer"
                aria-label="Back to Timetables"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-700 to-indigo-600 flex items-center justify-center text-white shadow-sm ring-2 ring-brand-100 shrink-0">
                <CalendarDays className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] sm:text-xs font-bold uppercase tracking-wider text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
                    Official Calendar
                  </span>
                  <span className="text-xs text-slate-500 hidden sm:inline">
                    Faculty of Applied Sciences • WUSL
                  </span>
                </div>
                <h1 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight leading-tight truncate">
                  Academic Calendar Explorer
                </h1>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {onNavigateToDevelopers && (
                <button
                  onClick={onNavigateToDevelopers}
                  className="hidden sm:inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-2xs transition-colors cursor-pointer"
                >
                  <FileText className="w-3.5 h-3.5 text-brand-600" />
                  <span>API Docs</span>
                </button>
              )}
              <button
                onClick={loadData}
                disabled={loading}
                className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200 disabled:opacity-50 cursor-pointer"
                title="Refresh Calendar"
                aria-label="Refresh Calendar Data"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-brand-600' : ''}`} />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-xl flex items-center justify-between mb-6 shadow-xs">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
              <span className="text-sm font-medium">{error}</span>
            </div>
            <button
              onClick={loadData}
              className="text-xs bg-red-100 hover:bg-red-200 text-red-900 px-3 py-1.5 rounded-lg font-semibold transition-colors cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading && !activeCalendar ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
            <RefreshCw className="w-8 h-8 text-brand-600 animate-spin mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-800">
              Loading Official Academic Calendar...
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Checking official FAS WUSL publication records
            </p>
          </div>
        ) : !activeCalendar ? (
          /* Empty State */
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mx-auto mb-3">
              <Calendar className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-semibold text-slate-800 mb-1">
              No Academic Calendar Records Available
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto mb-4">
              The automated synchronization system has not yet indexed official calendar records.
              Run the sync worker or trigger the workflow to discover notices from the FAS website.
            </p>
          </div>
        ) : (
          /* Calendar Details */
          <div className="space-y-6">
            {/* Top Overview & Selector Card */}
            <div className="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-slate-100">
                <div>
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    {activeCalendar.isCurrentConfirmed ? (
                      <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Official Verified Active</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                        <span>Unconfirmed Selection</span>
                      </span>
                    )}

                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-brand-50 text-brand-700 border border-brand-200">
                      Status: {activeCalendar.documentStatus?.toUpperCase()}
                    </span>

                    {activeCalendar.revision && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                        {activeCalendar.revision}
                      </span>
                    )}
                  </div>

                  <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                    Academic Year {activeCalendar.academicYear}
                  </h2>
                  <p className="text-xs sm:text-sm text-slate-500 mt-1">
                    {activeCalendar.documentTitle} • Levels {activeCalendar.levels?.join(', ')}
                  </p>
                </div>

                {/* Calendar switcher if multiple exist */}
                {calendars.length > 1 && (
                  <div className="flex items-center space-x-2">
                    <label className="text-xs font-medium text-slate-600">Select Term:</label>
                    <select
                      value={selectedCalendarId}
                      onChange={(e) => setSelectedCalendarId(e.target.value)}
                      className="text-xs bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 font-medium text-slate-800 hover:bg-slate-100 focus:outline-hidden focus:ring-2 focus:ring-brand-500 cursor-pointer"
                    >
                      {calendars.map((c) => (
                        <option key={c.calendarId || c.id} value={c.calendarId || c.id}>
                          {c.academicYear} — {c.documentStatus?.toUpperCase()} {c.isCurrent ? '(Current)' : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {/* Selection reason notice */}
              {activeCalendar.selectionReason && (
                <div className="mt-4 p-3 bg-slate-50 border border-slate-200/70 rounded-xl flex items-start space-x-2 text-xs text-slate-600">
                  <Info className="w-4 h-4 text-brand-600 shrink-0 mt-0.5" />
                  <span>
                    <strong>Selection Policy:</strong> {activeCalendar.selectionReason}
                  </span>
                </div>
              )}

              {/* Metadata strip */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-4 border-t border-slate-100 text-xs">
                <div>
                  <span className="text-slate-400 block font-medium">Signature / Approval</span>
                  <span className="text-slate-800 font-semibold">
                    {formatDate(activeCalendar.signatureDate)}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block font-medium">Notice Published</span>
                  <span className="text-slate-800 font-semibold">
                    {formatDate(activeCalendar.publicationDate)}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block font-medium">Semesters Covered</span>
                  <span className="text-slate-800 font-semibold">
                    {activeCalendar.semesters?.join(', ') || 'Semester I'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block font-medium">Official Source Document</span>
                  {activeCalendar.sourceUrl ? (
                    <a
                      href={activeCalendar.sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center space-x-1 text-brand-600 hover:text-brand-800 font-semibold"
                    >
                      <span>Download PDF</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    <span className="text-slate-500">Not linked</span>
                  )}
                </div>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex border-b border-slate-200 space-x-4">
              <button
                onClick={() => setActiveTab('semesters')}
                className={`pb-3 text-sm font-semibold border-b-2 transition-colors cursor-pointer flex items-center space-x-2 ${
                  activeTab === 'semesters'
                    ? 'border-brand-600 text-brand-600'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <Calendar className="w-4 h-4" />
                <span>Semester Schedules</span>
              </button>

              <button
                onClick={() => setActiveTab('upcoming')}
                className={`pb-3 text-sm font-semibold border-b-2 transition-colors cursor-pointer flex items-center space-x-2 ${
                  activeTab === 'upcoming'
                    ? 'border-brand-600 text-brand-600'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <Sparkles className="w-4 h-4" />
                <span>Upcoming & Ongoing ({upcoming.length})</span>
              </button>

              {activeCalendar.revisionHistory?.length > 0 && (
                <button
                  onClick={() => setActiveTab('revisions')}
                  className={`pb-3 text-sm font-semibold border-b-2 transition-colors cursor-pointer flex items-center space-x-2 ${
                    activeTab === 'revisions'
                      ? 'border-brand-600 text-brand-600'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
                >
                  <History className="w-4 h-4" />
                  <span>Revision History ({activeCalendar.revisionHistory.length})</span>
                </button>
              )}
            </div>

            {/* Tab: Semesters */}
            {activeTab === 'semesters' && (
              <div className="space-y-4">
                {/* Semester Filter Pills */}
                {semestersAvailable.length > 1 && (
                  <div className="flex items-center space-x-2 pb-2">
                    <span className="text-xs font-medium text-slate-500">Filter Semester:</span>
                    <button
                      onClick={() => setActiveSemester('All')}
                      className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors cursor-pointer ${
                        activeSemester === 'All'
                          ? 'bg-brand-600 text-white border-brand-600'
                          : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      All Semesters
                    </button>
                    {semestersAvailable.map((sem) => (
                      <button
                        key={sem}
                        onClick={() => setActiveSemester(sem)}
                        className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors cursor-pointer ${
                          activeSemester === sem
                            ? 'bg-brand-600 text-white border-brand-600'
                            : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
                        }`}
                      >
                        {sem}
                      </button>
                    ))}
                  </div>
                )}

                {/* Activities Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  {filteredActivities.map((act, idx) => {
                    const style = CATEGORY_STYLES[act.category] || CATEGORY_STYLES.other;
                    return (
                      <div
                        key={idx}
                        className={`p-4 rounded-xl border ${style.bg} transition-all shadow-2xs hover:shadow-xs flex flex-col justify-between`}
                      >
                        <div>
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                              {act.semester}
                            </span>
                            <span
                              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${style.badge}`}
                            >
                              {style.label}
                            </span>
                          </div>

                          <h3 className="text-sm font-bold text-slate-900 leading-snug">
                            {act.activity}
                          </h3>
                        </div>

                        <div className="mt-3 pt-3 border-t border-slate-200/60 flex items-center justify-between text-xs">
                          <div className="flex items-center space-x-1.5 font-medium text-slate-700">
                            <Clock className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                            <span>
                              {formatDate(act.startDate)} – {formatDate(act.endDate)}
                            </span>
                          </div>

                          {act.durationRaw && (
                            <span className="text-[11px] font-semibold text-slate-600 bg-white/80 px-2 py-0.5 rounded-md border border-slate-200/80">
                              {act.durationRaw}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Tab: Upcoming Activities */}
            {activeTab === 'upcoming' && (
              <div className="space-y-3">
                {upcoming.length === 0 ? (
                  <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-xs text-slate-500">
                    No upcoming activities found for this academic period.
                  </div>
                ) : (
                  upcoming.map((act, idx) => {
                    const style = CATEGORY_STYLES[act.category] || CATEGORY_STYLES.other;
                    const isOngoing = act.status === 'ongoing';
                    return (
                      <div
                        key={idx}
                        className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                      >
                        <div className="flex items-start space-x-3">
                          <div
                            className={`w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${
                              isOngoing ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
                            }`}
                          />
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="text-xs font-semibold text-slate-900">
                                {act.activity}
                              </span>
                              {isOngoing && (
                                <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-1.5 py-0.5 rounded uppercase">
                                  Ongoing Now
                                </span>
                              )}
                            </div>
                            <span className="text-xs text-slate-500">
                              {act.semester} • {style.label}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center space-x-3 text-xs shrink-0 pl-5.5 sm:pl-0">
                          <span className="text-slate-700 font-medium">
                            {formatDate(act.startDate)} – {formatDate(act.endDate)}
                          </span>
                          {act.durationRaw && (
                            <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-semibold text-[11px]">
                              {act.durationRaw}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* Tab: Revisions */}
            {activeTab === 'revisions' && (
              <div className="bg-white rounded-xl border border-slate-200 p-5 divide-y divide-slate-100">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                  Historical Document Versions Preserved
                </h3>
                {activeCalendar.revisionHistory.map((rev, idx) => (
                  <div key={idx} className="py-3 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-semibold text-slate-800 block">
                        {rev.documentTitle} ({rev.documentStatus?.toUpperCase()})
                      </span>
                      <span className="text-slate-400 text-[11px]">
                        Recorded at {formatDate(rev.recordedAt?.split('T')[0])} • SHA-256:{' '}
                        {rev.sha256?.substring(0, 12)}...
                      </span>
                    </div>
                    {rev.sourceUrl && (
                      <a
                        href={rev.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-brand-600 hover:text-brand-800 font-medium"
                      >
                        View Source
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Sync Status Footer Bar */}
            {syncStatus && (
              <div className="bg-white rounded-xl border border-slate-200/80 p-4 text-xs text-slate-500 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>
                    Official Source last verified at{' '}
                    <strong>{formatDate(syncStatus.lastCheckedAt?.split('T')[0])}</strong>
                  </span>
                </div>
                <div className="flex items-center space-x-3 text-[11px]">
                  <span>SHA-256: {activeCalendar.sha256?.substring(0, 16)}...</span>
                  <span>Parser v{activeCalendar.parserVersion || '1.0.0'}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
