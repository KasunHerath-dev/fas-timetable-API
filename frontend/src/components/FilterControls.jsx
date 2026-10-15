import React from 'react';
import { Search, LayoutGrid, ListFilter, CalendarDays, X } from 'lucide-react';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const SESSION_TYPES = ['All', 'Lecture', 'Practical', 'Tutorial'];

export default function FilterControls({
  selectedLevel,
  onSelectLevel,
  academicYears,
  selectedYear,
  onSelectYear,
  semesters,
  selectedSemester,
  onSelectSemester,
  searchQuery,
  onSearchChange,
  selectedType,
  onSelectType,
  viewMode,
  onViewModeChange,
  selectedDay,
  onSelectDay,
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-xs mb-6 space-y-4">
      {/* Level Selection Bar & View Mode Switcher */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-100">
        {/* Level Tabs */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Academic Level
          </label>
          <div className="grid grid-cols-4 sm:flex gap-1.5 sm:gap-2">
            {[1, 2, 3, 4].map((lvl) => {
              const active = selectedLevel === lvl;
              return (
                <button
                  key={lvl}
                  onClick={() => onSelectLevel(lvl)}
                  className={`px-3.5 sm:px-5 py-2 sm:py-2.5 rounded-lg text-sm font-semibold transition-all cursor-pointer flex items-center justify-center ${
                    active
                      ? 'bg-brand-600 text-white shadow-sm shadow-brand-200 ring-2 ring-brand-600 ring-offset-1'
                      : 'bg-slate-50 text-slate-700 hover:bg-slate-100 border border-slate-200'
                  }`}
                >
                  <span>Level {lvl}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* View Mode Toggle (Grid vs Daily List) */}
        <div className="flex items-center space-x-2 self-start lg:self-end">
          <div className="bg-slate-100 p-1 rounded-lg flex items-center space-x-1 border border-slate-200">
            <button
              onClick={() => onViewModeChange('grid')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                viewMode === 'grid'
                  ? 'bg-white text-brand-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Weekly Grid</span>
            </button>
            <button
              onClick={() => onViewModeChange('daily')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                viewMode === 'daily'
                  ? 'bg-white text-brand-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <CalendarDays className="w-3.5 h-3.5" />
              <span>Daily View</span>
            </button>
          </div>
        </div>
      </div>

      {/* Dropdown Filters & Search */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Academic Year Selector */}
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Academic Year</label>
          <select
            value={selectedYear || ''}
            onChange={(e) => onSelectYear(e.target.value)}
            className="w-full px-3 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white text-slate-800"
          >
            {academicYears.map((yr) => (
              <option key={yr} value={yr}>
                {yr}
              </option>
            ))}
          </select>
        </div>

        {/* Semester Selector */}
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Semester</label>
          <select
            value={selectedSemester || ''}
            onChange={(e) => onSelectSemester(e.target.value)}
            className="w-full px-3 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white text-slate-800"
          >
            {semesters.map((sem) => (
              <option key={sem} value={sem}>
                {sem}
              </option>
            ))}
          </select>
        </div>

        {/* Session Type Filter */}
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Session Type</label>
          <select
            value={selectedType}
            onChange={(e) => onSelectType(e.target.value)}
            className="w-full px-3 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white text-slate-800"
          >
            {SESSION_TYPES.map((t) => (
              <option key={t} value={t}>
                {t === 'All' ? 'All Session Types' : `${t}s`}
              </option>
            ))}
          </select>
        </div>

        {/* Search by Subject Code */}
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Search Subject Code</label>
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="e.g. CMIS 1113, IMGT, ELTN"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-9 pr-8 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white text-slate-800 placeholder-slate-400"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Day Selector (Shown prominently in Daily view or when filtering) */}
      {viewMode === 'daily' && (
        <div className="pt-2">
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Select Day
          </label>
          <div className="flex flex-wrap gap-2">
            {DAYS.map((d) => (
              <button
                key={d}
                onClick={() => onSelectDay(d)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  selectedDay === d
                    ? 'bg-brand-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
