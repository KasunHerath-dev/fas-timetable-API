import React from 'react';
import { MapPin, Users, AlertTriangle, Clock } from 'lucide-react';

export default function SessionCard({ session, onClick, compact = false }) {
  const isReview = session.validationStatus === 'NEEDS_REVIEW';
  const type = session.sessionType || 'Unspecified';

  // Session type badge styling
  const getTypeBadgeClasses = (t) => {
    switch (t) {
      case 'Lecture':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'Practical':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'Tutorial':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-purple-100 text-purple-800 border-purple-200';
    }
  };

  // Card background styling based on type and review status
  const getCardClasses = (t, review) => {
    if (review) {
      return 'bg-amber-50/70 border-amber-300 hover:border-amber-400 hover:shadow-amber-100/50';
    }
    switch (t) {
      case 'Lecture':
        return 'bg-blue-50/50 border-blue-200 hover:border-blue-300 hover:shadow-blue-50';
      case 'Practical':
        return 'bg-emerald-50/50 border-emerald-200 hover:border-emerald-300 hover:shadow-emerald-50';
      case 'Tutorial':
        return 'bg-amber-50/50 border-amber-200 hover:border-amber-300 hover:shadow-amber-50';
      default:
        return 'bg-slate-50 border-slate-200 hover:border-slate-300';
    }
  };

  return (
    <div
      onClick={() => onClick && onClick(session)}
      className={`rounded-lg border p-2 sm:p-2.5 transition-all cursor-pointer relative shadow-2xs hover:shadow-md flex flex-col justify-between ${getCardClasses(
        type,
        isReview
      )}`}
    >
      <div>
        {/* Header row: Subject code & Session Type */}
        <div className="flex items-start justify-between gap-1 mb-1">
          <span className="font-bold text-slate-900 text-xs sm:text-sm tracking-tight leading-tight">
            {session.subjectCode || 'No Code'}
          </span>
          <span
            className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border leading-none shrink-0 ${getTypeBadgeClasses(
              type
            )}`}
          >
            {type === 'Lecture' ? 'L' : type === 'Practical' ? 'P' : type === 'Tutorial' ? 'T' : 'Other'}
          </span>
        </div>

        {/* Time slot */}
        <div
          className={`flex items-center space-x-1 font-medium ${
            compact ? 'text-[10px] text-slate-500 mb-1' : 'text-[11px] text-slate-600 mb-1.5'
          }`}
        >
          <Clock className={`${compact ? 'w-2.5 h-2.5 text-slate-400 shrink-0' : 'w-3 h-3 text-slate-400 shrink-0'}`} />
          <span>
            {session.startTime} - {session.endTime}
          </span>
        </div>

        {/* Practical Group & Location */}
        <div className="space-y-0.5 text-[11px]">
          {session.group && (
            <div className="flex items-center space-x-1 text-slate-700 font-medium">
              <Users className="w-3 h-3 text-slate-400 shrink-0" />
              <span className="truncate">{session.group}</span>
            </div>
          )}

          {session.location && (
            <div className="flex items-center space-x-1 text-slate-600 font-normal">
              <MapPin className="w-3 h-3 text-slate-400 shrink-0" />
              <span className="truncate">{session.location}</span>
            </div>
          )}
        </div>
      </div>

      {/* NEEDS_REVIEW Indicator */}
      {isReview && (
        <div className="mt-2 pt-1.5 border-t border-amber-200/60 flex items-center justify-between text-[10px] text-amber-800 font-medium">
          <div className="flex items-center space-x-1">
            <AlertTriangle className="w-3 h-3 text-amber-600 shrink-0" />
            <span className="truncate">Unverified (Review)</span>
          </div>
          <span className="text-amber-600 underline text-[9px] shrink-0 ml-1">info</span>
        </div>
      )}
    </div>
  );
}
