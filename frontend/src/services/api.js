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
