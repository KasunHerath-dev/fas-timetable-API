/**
 * API service for FAS WUSL Timetable Application
 */

const rawBase = (import.meta.env?.VITE_API_BASE_URL || '').trim();
const API_BASE = rawBase ? rawBase.replace(/\/+$/, '').replace(/\/api$/, '') : '';

/**
 * Fetch health status of API and database
 */
export async function getHealthStatus() {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error(`Health check failed with status ${res.status}`);
  return res.json();
}

/**
 * Fetch all available timetable metadata records
 * @param {number} [level]
 */
export async function getTimetables(level) {
  const url = level ? `${API_BASE}/api/timetables?level=${level}` : `${API_BASE}/api/timetables`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load timetables (${res.status})`);
  return res.json();
}

/**
 * Fetch timetable sessions for a level with optional filters
 * @param {number} level
 * @param {Object} [filters]
 * @param {string} [filters.academicYear]
 * @param {string} [filters.semester]
 * @param {string} [filters.day]
 * @param {string} [filters.subjectCode]
 */
export async function getSessions(level, filters = {}) {
  const params = new URLSearchParams();
  if (filters.academicYear) params.append('academicYear', filters.academicYear);
  if (filters.semester) params.append('semester', filters.semester);
  if (filters.day) params.append('day', filters.day);
  if (filters.subjectCode) params.append('subjectCode', filters.subjectCode);

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_BASE}/api/timetables/${level}/sessions${query}`);
  if (!res.ok) throw new Error(`Failed to load sessions (${res.status})`);
  return res.json();
}

/**
 * Fetch validation and session counts status for a level
 * @param {number} level
 * @param {string} [academicYear]
 * @param {string} [semester]
 */
export async function getLevelStatus(level, academicYear, semester) {
  const params = new URLSearchParams();
  if (academicYear) params.append('academicYear', academicYear);
  if (semester) params.append('semester', semester);

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_BASE}/api/timetables/${level}/status${query}`);
  if (!res.ok) throw new Error(`Failed to load level status (${res.status})`);
  return res.json();
}

/**
 * Fetch all available academic calendar records
 * @param {Object} [filters]
 * @param {string} [filters.academicYear]
 * @param {string} [filters.status]
 */
export async function getAcademicCalendars(filters = {}) {
  const params = new URLSearchParams();
  if (filters.academicYear) params.append('academicYear', filters.academicYear);
  if (filters.status) params.append('status', filters.status);

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_BASE}/api/academic-calendar${query}`);
  if (!res.ok) throw new Error(`Failed to load academic calendars (${res.status})`);
  return res.json();
}

/**
 * Fetch authoritative current academic calendar
 */
export async function getCurrentAcademicCalendar() {
  const res = await fetch(`${API_BASE}/api/academic-calendar/current`);
  if (!res.ok) throw new Error(`Failed to load current academic calendar (${res.status})`);
  return res.json();
}

/**
 * Fetch calendar by academic year
 * @param {string} academicYear
 */
export async function getAcademicCalendarByYear(academicYear) {
  const encoded = encodeURIComponent(academicYear);
  const res = await fetch(`${API_BASE}/api/academic-calendar/${encoded}`);
  if (!res.ok) throw new Error(`Failed to load academic calendar for year ${academicYear} (${res.status})`);
  return res.json();
}

/**
 * Fetch semester details for an academic year
 * @param {string} academicYear
 * @param {string} semester
 */
export async function getAcademicCalendarSemester(academicYear, semester) {
  const encYear = encodeURIComponent(academicYear);
  const encSem = encodeURIComponent(semester);
  const res = await fetch(`${API_BASE}/api/academic-calendar/${encYear}/semesters/${encSem}`);
  if (!res.ok) throw new Error(`Failed to load calendar semester (${res.status})`);
  return res.json();
}

/**
 * Fetch upcoming scheduled activities
 * @param {Object} [options]
 * @param {string} [options.referenceDate]
 * @param {number} [options.limit]
 * @param {string} [options.academicYear]
 */
export async function getUpcomingActivities(options = {}) {
  const params = new URLSearchParams();
  if (options.referenceDate) params.append('reference_date', options.referenceDate);
  if (options.limit) params.append('limit', options.limit.toString());
  if (options.academicYear) params.append('academicYear', options.academicYear);

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_BASE}/api/academic-calendar/upcoming${query}`);
  if (!res.ok) throw new Error(`Failed to load upcoming activities (${res.status})`);
  return res.json();
}

/**
 * Fetch academic calendar synchronization status
 */
export async function getAcademicCalendarStatus() {
  const res = await fetch(`${API_BASE}/api/academic-calendar/status`);
  if (!res.ok) throw new Error(`Failed to load calendar status (${res.status})`);
  return res.json();
}
