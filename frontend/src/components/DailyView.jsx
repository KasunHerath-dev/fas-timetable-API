import React from 'react';
import SessionCard from './SessionCard';
import { Calendar, Clock, Utensils } from 'lucide-react';

export default function DailyView({ sessions, selectedDay, onSessionClick }) {
  // Filter sessions for the selected day and sort by start_time
  const daySessions = sessions
    .filter((s) => s.day === selectedDay)
    .sort((a, b) => a.startTime.localeCompare(b.startTime));

  // Group sessions by start time
  const groupedByTime = {};
  daySessions.forEach((s) => {
    if (!groupedByTime[s.startTime]) groupedByTime[s.startTime] = [];
    groupedByTime[s.startTime].push(s);
  });

  const sortedTimeSlots = Object.keys(groupedByTime).sort();

  return (
    <div className="space-y-4">
      {/* Day header */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 flex items-center justify-between shadow-xs">
        <div className="flex items-center space-x-2">
          <Calendar className="w-5 h-5 text-brand-600" />
          <h2 className="text-base font-bold text-slate-900">{selectedDay} Schedule</h2>
        </div>
        <span className="text-xs bg-slate-100 text-slate-700 px-2.5 py-1 rounded-full font-medium">
          {daySessions.length} {daySessions.length === 1 ? 'session' : 'sessions'}
        </span>
      </div>

      {/* Empty state */}
      {daySessions.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center shadow-xs">
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mx-auto mb-3">
            <Clock className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-semibold text-slate-700 mb-1">
            No teaching sessions scheduled
          </h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            There are no lecture, practical, or tutorial sessions scheduled for {selectedDay} in this timetable.
          </p>
        </div>
      ) : (
        /* Timeline slots */
        <div className="space-y-3">
          {sortedTimeSlots.map((startTime) => {
            const slotSessions = groupedByTime[startTime];
            const endTime = slotSessions[0]?.endTime || '';

            return (
              <div
                key={startTime}
                className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-col sm:flex-row sm:items-start gap-3 sm:gap-4"
              >
                {/* Time badge */}
                <div className="sm:w-32 shrink-0 flex items-center sm:flex-col sm:items-start space-x-2 sm:space-x-0 pt-0.5">
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-brand-800 bg-brand-50 px-2.5 py-1 rounded-md border border-brand-200/60">
                    <Clock className="w-3.5 h-3.5 text-brand-600" />
                    <span>
                      {startTime} – {endTime}
                    </span>
                  </div>
                </div>

                {/* Session cards in this slot */}
                <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {slotSessions.map((sess, idx) => (
                    <SessionCard
                      key={sess.id || idx}
                      session={sess}
                      onClick={onSessionClick}
                      compact={false}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
