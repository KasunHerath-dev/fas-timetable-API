import React from 'react';
import SessionCard from './SessionCard';
import { Utensils } from 'lucide-react';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

// Hourly timetable slots commonly published by FAS WUSL
const TIME_SLOTS = [
  { start: '08:30', end: '09:30', label: '08:30 - 09:30' },
  { start: '09:30', end: '10:30', label: '09:30 - 10:30' },
  { start: '10:30', end: '11:30', label: '10:30 - 11:30' },
  { start: '11:30', end: '12:30', label: '11:30 - 12:30' },
  { start: '12:30', end: '13:30', label: '12:30 - 01:30', isLunch: true },
  { start: '13:30', end: '14:30', label: '01:30 - 02:30' },
  { start: '14:30', end: '15:30', label: '02:30 - 03:30' },
  { start: '15:30', end: '16:30', label: '03:30 - 04:30' },
  { start: '16:30', end: '17:30', label: '04:30 - 05:30' },
  { start: '17:30', end: '18:30', label: '05:30 - 06:30' },
];

export default function WeeklyGrid({ sessions, onSessionClick }) {
  // Index sessions by `day` and `startTime`
  const sessionMap = {};
  sessions.forEach((s) => {
    const key = `${s.day}_${s.startTime}`;
    if (!sessionMap[key]) sessionMap[key] = [];
    sessionMap[key].push(s);
  });

  // Get sessions that began in an earlier slot and continue through this slot
  const getContinuingSessions = (day, slot) => {
    return sessions.filter(
      (s) => s.day === day && s.startTime < slot.start && s.endTime > slot.start
    );
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
      {/* Mobile scroll hint */}
      <div className="sm:hidden flex items-center justify-between px-3.5 py-2 bg-slate-50 border-b border-slate-200 text-[11px] text-slate-500 font-medium">
        <span>👉 Swipe horizontally to view all days</span>
        <span className="text-brand-700 font-semibold">5 Days</span>
      </div>

      <div className="overflow-x-auto touch-pan-x">
        <table className="w-full min-w-[850px] border-collapse text-left">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="py-3.5 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider w-28 text-center border-r border-slate-200 shrink-0">
                Time
              </th>
              {DAYS.map((day) => (
                <th
                  key={day}
                  className="py-3.5 px-3 text-xs font-bold text-slate-800 uppercase tracking-wider text-center border-r border-slate-200 last:border-r-0"
                >
                  {day}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 text-xs">
            {TIME_SLOTS.map((slot) => {
              if (slot.isLunch) {
                // Check if any day has scheduled sessions during lunch
                const hasSessionsInLunchSlot = DAYS.some(
                  (day) =>
                    (sessionMap[`${day}_${slot.start}`] || []).length > 0 ||
                    getContinuingSessions(day, slot).length > 0
                );

                if (!hasSessionsInLunchSlot) {
                  return (
                    <tr key={slot.start} className="bg-amber-50/40 border-y border-amber-200/60">
                      <td className="py-2.5 px-3 font-semibold text-amber-900/80 text-center border-r border-slate-200 bg-amber-100/30 whitespace-nowrap">
                        {slot.label}
                      </td>
                      <td
                        colSpan={DAYS.length}
                        className="py-2.5 px-4 text-center font-bold tracking-widest uppercase text-amber-800 text-xs bg-amber-50/60"
                      >
                        <div className="flex items-center justify-center space-x-2">
                          <Utensils className="w-3.5 h-3.5 text-amber-600" />
                          <span>L U N C H &nbsp; B R E A K</span>
                        </div>
                      </td>
                    </tr>
                  );
                }

                // If any day has sessions (e.g. Friday), render each day cell individually
                return (
                  <tr key={slot.start} className="border-y border-amber-200/60 bg-amber-50/10">
                    <td className="py-2.5 px-3 font-semibold text-amber-900/80 text-center border-r border-slate-200 bg-amber-100/30 whitespace-nowrap">
                      {slot.label}
                    </td>
                    {DAYS.map((day) => {
                      const cellSessions = sessionMap[`${day}_${slot.start}`] || [];
                      const continuing = getContinuingSessions(day, slot);

                      if (cellSessions.length === 0 && continuing.length === 0) {
                        return (
                          <td
                            key={day}
                            className="p-1.5 align-middle border-r border-slate-200 last:border-r-0 w-[18%] bg-amber-50/30 text-center"
                          >
                            <div className="flex items-center justify-center space-x-1.5 py-3 text-amber-700/80 font-medium text-[11px]">
                              <Utensils className="w-3 h-3 text-amber-600/70" />
                              <span>Lunch Break</span>
                            </div>
                          </td>
                        );
                      }

                      return (
                        <td
                          key={day}
                          className="p-1.5 align-top border-r border-slate-200 last:border-r-0 w-[18%] min-h-[75px] bg-white"
                        >
                          <div className="space-y-1.5">
                            {cellSessions.map((sess, idx) => (
                              <SessionCard
                                key={sess.id || idx}
                                session={sess}
                                onClick={onSessionClick}
                                compact={true}
                              />
                            ))}
                            {continuing.map((sess, idx) => (
                              <div
                                key={`cont_${sess.id || idx}`}
                                onClick={() => onSessionClick && onSessionClick(sess)}
                                className="rounded border border-dashed border-emerald-300 bg-emerald-50/50 p-1.5 text-xs text-emerald-800 cursor-pointer hover:bg-emerald-100/50 transition-colors flex items-center justify-between"
                                title={`${sess.subjectCode} continuing from previous slot`}
                              >
                                <span className="font-semibold">{sess.subjectCode}</span>
                                <span className="text-[10px] text-emerald-600 font-medium">
                                  Cont. to {sess.endTime}
                                </span>
                              </div>
                            ))}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                );
              }

              return (
                <tr key={slot.start} className="hover:bg-slate-50/40 transition-colors">
                  {/* Time column */}
                  <td className="py-3 px-2 text-center font-medium text-slate-500 border-r border-slate-200 bg-slate-50/50 whitespace-nowrap">
                    {slot.label}
                  </td>

                  {/* Weekday cells */}
                  {DAYS.map((day) => {
                    const cellSessions = sessionMap[`${day}_${slot.start}`] || [];
                    const continuing = getContinuingSessions(day, slot);
                    const hasContent = cellSessions.length > 0 || continuing.length > 0;

                    return (
                      <td
                        key={day}
                        className="p-1.5 align-top border-r border-slate-200 last:border-r-0 w-[18%] min-h-[75px]"
                      >
                        {hasContent ? (
                          <div className="space-y-1.5">
                            {cellSessions.map((sess, idx) => (
                              <SessionCard
                                key={sess.id || idx}
                                session={sess}
                                onClick={onSessionClick}
                                compact={true}
                              />
                            ))}
                            {continuing.map((sess, idx) => (
                              <div
                                key={`cont_${sess.id || idx}`}
                                onClick={() => onSessionClick && onSessionClick(sess)}
                                className="rounded border border-dashed border-emerald-300 bg-emerald-50/50 p-1.5 text-xs text-emerald-800 cursor-pointer hover:bg-emerald-100/50 transition-colors flex items-center justify-between"
                                title={`${sess.subjectCode} continuing from previous slot`}
                              >
                                <span className="font-semibold">{sess.subjectCode}</span>
                                <span className="text-[10px] text-emerald-600 font-medium">
                                  Cont. to {sess.endTime}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="h-full min-h-[50px] flex items-center justify-center text-slate-300">
                            <span className="text-[11px] select-none">—</span>
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
