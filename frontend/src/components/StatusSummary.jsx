import React from 'react';
import { ShieldCheck, AlertTriangle, FileText, CheckCircle } from 'lucide-react';

export default function StatusSummary({ metadata, status, selectedLevel }) {
  const total = status?.totalSessions ?? 0;
  const valid = status?.validSessions ?? 0;
  const needsReview = status?.needsReviewSessions ?? 0;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-xs mb-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Timetable metadata info */}
        <div>
          <div className="flex items-center space-x-2 flex-wrap gap-y-1">
            <span className="text-sm font-semibold text-slate-800">
              Level {selectedLevel} Schedule
            </span>
            {metadata?.revision && (
              <span className="bg-brand-50 text-brand-700 text-xs px-2.5 py-0.5 rounded-full font-medium border border-brand-200">
                {metadata.revision}
              </span>
            )}
            {(metadata?.publishedDate || metadata?.publicationDate) && (
              <span className="text-xs text-slate-500">
                Published: {metadata.publishedDate || metadata.publicationDate}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Academic Year {metadata?.academicYear || '2024/2025'} • {metadata?.semester || 'Semester I'}
            {metadata?.sourcePdfUrl && (
              <a
                href={metadata.sourcePdfUrl}
                target="_blank"
                rel="noreferrer"
                className="ml-2 inline-flex items-center text-brand-600 hover:text-brand-800 hover:underline"
              >
                <FileText className="w-3 h-3 mr-0.5" /> Source PDF
              </a>
            )}
          </p>
        </div>

        {/* Verification metrics & badges */}
        <div className="flex items-center space-x-2 sm:space-x-3 text-xs">
          <div className="flex items-center space-x-1.5 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg text-slate-700">
            <span className="text-slate-400 font-normal">Total:</span>
            <span className="font-bold text-slate-900">{total}</span>
          </div>

          <div className="flex items-center space-x-1.5 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-lg text-emerald-800">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
            <span className="text-emerald-700 font-normal">Confirmed:</span>
            <span className="font-bold">{valid}</span>
          </div>

          {needsReview > 0 ? (
            <div
              className="flex items-center space-x-1.5 bg-amber-50 border border-amber-300 px-3 py-1.5 rounded-lg text-amber-900 ring-1 ring-amber-200"
              title={`${needsReview} sessions have non-standard symbols or missing annotations in the source PDF and are awaiting faculty verification`}
            >
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 animate-pulse" />
              <span className="text-amber-800 font-normal">Needs Review:</span>
              <span className="font-bold text-amber-900">{needsReview}</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg text-slate-500">
              <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
              <span>All Verified</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
