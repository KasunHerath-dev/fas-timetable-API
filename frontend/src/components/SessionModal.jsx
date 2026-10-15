import React from 'react';
import { X, Clock, MapPin, Users, AlertTriangle, CheckCircle2, FileText, Calendar } from 'lucide-react';

export default function SessionModal({ session, onClose }) {
  if (!session) return null;

  const isReview = session.validationStatus === 'NEEDS_REVIEW';

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150 my-auto">
        {/* Modal Header */}
        <div className="px-4 sm:px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50 shrink-0">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-brand-700 bg-brand-100/60 px-2 py-0.5 rounded">
              Level {session.level}
            </span>
            <span className="text-xs text-slate-500 font-medium truncate max-w-[170px] sm:max-w-none">
              {session.academicYear} • {session.semester}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-1 rounded-lg hover:bg-slate-200/60 transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-6 space-y-4 sm:space-y-5 overflow-y-auto">
          {/* Main Subject & Type */}
          <div>
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-2xl font-bold text-slate-900 tracking-tight">
                {session.subjectCode || 'Unassigned Subject'}
              </h3>
              <span
                className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
                  session.sessionType === 'Lecture'
                    ? 'bg-blue-100 text-blue-800 border-blue-200'
                    : session.sessionType === 'Practical'
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                    : session.sessionType === 'Tutorial'
                    ? 'bg-amber-100 text-amber-800 border-amber-200'
                    : 'bg-purple-100 text-purple-800 border-purple-200'
                }`}
              >
                {session.sessionType || 'Unspecified Type'}
              </span>
            </div>
          </div>

          {/* Verification Status Alert */}
          {isReview ? (
            <div className="bg-amber-50 border border-amber-300 rounded-xl p-3.5 space-y-2">
              <div className="flex items-start space-x-2.5">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-amber-900">
                    Awaiting Faculty Verification (NEEDS_REVIEW)
                  </h4>
                  <p className="text-xs text-amber-800 mt-0.5">
                    This entry contains non-standard characters, ambiguous syntax, or omitted type annotations in the official timetable notice PDF.
                  </p>
                </div>
              </div>
              {session.warnings && session.warnings.length > 0 && (
                <div className="mt-2 pt-2 border-t border-amber-200/80">
                  <span className="text-[11px] font-semibold text-amber-900 block mb-1">
                    Parser Diagnostic Notes:
                  </span>
                  <ul className="list-disc list-inside text-xs text-amber-800 space-y-0.5">
                    {session.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex items-center space-x-2 text-xs text-emerald-800 font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Verified academic schedule entry matching Faculty PDF standard.</span>
            </div>
          )}

          {/* Details Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 text-sm bg-slate-50 p-3.5 sm:p-4 rounded-xl border border-slate-200/80">
            <div>
              <span className="text-xs text-slate-500 font-medium flex items-center space-x-1 mb-1">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span>Day</span>
              </span>
              <span className="font-semibold text-slate-800">{session.day}</span>
            </div>

            <div>
              <span className="text-xs text-slate-500 font-medium flex items-center space-x-1 mb-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>Time Slot</span>
              </span>
              <span className="font-semibold text-slate-800">
                {session.startTime} – {session.endTime}
              </span>
            </div>

            <div>
              <span className="text-xs text-slate-500 font-medium flex items-center space-x-1 mb-1">
                <Users className="w-3.5 h-3.5 text-slate-400" />
                <span>Practical Group</span>
              </span>
              <span className="font-semibold text-slate-800">
                {session.group || 'All Groups / Not Applicable'}
              </span>
            </div>

            <div>
              <span className="text-xs text-slate-500 font-medium flex items-center space-x-1 mb-1">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                <span>Classroom / Lab</span>
              </span>
              <span className="font-semibold text-slate-800">
                {session.location || 'Not Specified in Timetable'}
              </span>
            </div>
          </div>

          {/* Raw PDF Cell Text (Full Provenance) */}
          {session.rawCellText && (
            <div>
              <span className="text-xs font-semibold text-slate-500 flex items-center space-x-1 mb-1.5">
                <FileText className="w-3.5 h-3.5 text-slate-400" />
                <span>Raw Text from Source PDF Grid Cell:</span>
              </span>
              <pre className="text-xs bg-slate-900 text-slate-200 p-3 rounded-lg font-mono whitespace-pre-wrap overflow-x-auto border border-slate-800">
                {session.rawCellText}
              </pre>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-4 sm:px-6 py-3.5 bg-slate-50 border-t border-slate-100 flex justify-end shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
