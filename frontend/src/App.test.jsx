import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import App from './App';
import * as api from './services/api';

vi.mock('./services/api');

describe('FAS WUSL Timetable App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    // Return unresolved promises to test loading state
    api.getHealthStatus.mockReturnValue(new Promise(() => {}));
    api.getTimetables.mockReturnValue(new Promise(() => {}));
    api.getSessions.mockReturnValue(new Promise(() => {}));
    api.getLevelStatus.mockReturnValue(new Promise(() => {}));

    render(<App />);
    expect(screen.getByText(/Loading Level 1 Timetable.../i)).toBeInTheDocument();
  });

  it('renders error state and retry button on API failure', async () => {
    api.getHealthStatus.mockRejectedValue(new Error('Network offline'));
    api.getTimetables.mockRejectedValue(new Error('Network offline'));
    api.getSessions.mockRejectedValue(new Error('Network offline'));
    api.getLevelStatus.mockRejectedValue(new Error('Network offline'));

    render(<App />);

    await waitFor(() => {
      expect(
        screen.getByText(/Failed to retrieve timetable sessions|Unable to reach the timetable backend/i)
      ).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
    });
  });

  it('renders sessions and shows NEEDS_REVIEW unverified indicator when present', async () => {
    api.getHealthStatus.mockResolvedValue({ status: 'ok', database: 'connected' });
    api.getTimetables.mockResolvedValue([
      {
        id: 't1',
        level: 1,
        academicYear: '2024/2025',
        semester: 'Semester I',
        revision: 'Revised 02',
        publicationDate: '2026-10-05',
      },
    ]);
    api.getSessions.mockResolvedValue({
      level: 1,
      academicYear: '2024/2025',
      semester: 'Semester I',
      totalSessions: 2,
      sessions: [
        {
          id: 's1',
          day: 'Monday',
          startTime: '08:30',
          endTime: '09:30',
          subjectCode: 'CMIS 1113',
          sessionType: 'Lecture',
          group: null,
          location: 'MH',
          rawCellText: 'CMIS 1113 (L)\nMH',
          validationStatus: 'VALID',
          warnings: [],
        },
        {
          id: 's2',
          day: 'Monday',
          startTime: '10:30',
          endTime: '11:30',
          subjectCode: 'ELPC 1+10',
          sessionType: null,
          group: null,
          location: 'Mini Auditorium',
          rawCellText: 'ELPC 1+10\nMini Auditorium',
          validationStatus: 'NEEDS_REVIEW',
          warnings: ["Unusual character in subject code: 'ELPC 1+10'"],
        },
      ],
    });
    api.getLevelStatus.mockResolvedValue({
      level: 1,
      academicYear: '2024/2025',
      semester: 'Semester I',
      totalSessions: 2,
      validSessions: 1,
      needsReviewSessions: 1,
      sessionTypes: { Lecture: 1, Unspecified: 1 },
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('CMIS 1113')).toBeInTheDocument();
      expect(screen.getByText('ELPC 1+10')).toBeInTheDocument();
      // Verify NEEDS_REVIEW label is rendered and not silently omitted
      expect(screen.getByText(/Unverified \(Review\)/i)).toBeInTheDocument();
    });
  });

  it('renders empty state when search finds no sessions and allows reset', async () => {
    api.getHealthStatus.mockResolvedValue({ status: 'ok', database: 'connected' });
    api.getTimetables.mockResolvedValue([
      {
        id: 't1',
        level: 1,
        academicYear: '2024/2025',
        semester: 'Semester I',
        revision: 'Revised 02',
      },
    ]);
    api.getSessions.mockResolvedValue({
      level: 1,
      academicYear: '2024/2025',
      semester: 'Semester I',
      totalSessions: 1,
      sessions: [
        {
          id: 's1',
          day: 'Monday',
          startTime: '08:30',
          endTime: '09:30',
          subjectCode: 'CMIS 1113',
          sessionType: 'Lecture',
          location: 'MH',
          validationStatus: 'VALID',
          warnings: [],
        },
      ],
    });
    api.getLevelStatus.mockResolvedValue({
      level: 1,
      totalSessions: 1,
      validSessions: 1,
      needsReviewSessions: 0,
      sessionTypes: { Lecture: 1 },
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('CMIS 1113')).toBeInTheDocument();
    });

    // Enter a search query that matches nothing
    const searchInput = screen.getByPlaceholderText(/e.g. CMIS 1113/i);
    fireEvent.change(searchInput, { target: { value: 'NONEXISTENT999' } });

    await waitFor(() => {
      expect(screen.getByText(/No matching sessions found/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Reset Filters/i })).toBeInTheDocument();
    });

    // Click Reset Filters
    fireEvent.click(screen.getByRole('button', { name: /Reset Filters/i }));

    await waitFor(() => {
      expect(screen.getByText('CMIS 1113')).toBeInTheDocument();
    });
  });

  it('renders Friday lunch session CMIS 2113 visibly on Weekly Grid without being hidden by lunch break', async () => {
    api.getHealthStatus.mockResolvedValue({ status: 'ok', database: 'connected' });
    api.getTimetables.mockResolvedValue([
      {
        id: 't2',
        level: 2,
        academicYear: '2024/2025',
        semester: 'Semester I',
        revision: 'Revised 01',
      },
    ]);
    api.getSessions.mockResolvedValue({
      level: 2,
      academicYear: '2024/2025',
      semester: 'Semester I',
      totalSessions: 1,
      sessions: [
        {
          id: 'cmis-2113-gp4',
          day: 'Friday',
          startTime: '12:30',
          endTime: '14:30',
          subjectCode: 'CMIS 2113',
          sessionType: 'Practical',
          group: 'Gp. lV',
          location: null,
          rawCellText: 'CMIS 2113 (P)\nGp. lV | 12.30 p.m. – 2.30 p.m.',
          validationStatus: 'VALID',
          warnings: [],
        },
      ],
    });
    api.getLevelStatus.mockResolvedValue({
      level: 2,
      totalSessions: 1,
      validSessions: 1,
      needsReviewSessions: 0,
      sessionTypes: { Practical: 1 },
    });

    render(<App />);

    await waitFor(() => {
      // CMIS 2113 must appear in the document
      const cmisElements = screen.getAllByText('CMIS 2113');
      expect(cmisElements.length).toBeGreaterThan(0);
      // Group label Gp. lV must be displayed
      expect(screen.getByText('Gp. lV')).toBeInTheDocument();
      // Time badge 12:30 - 14:30 must be displayed
      expect(screen.getByText('12:30 - 14:30')).toBeInTheDocument();
    });
  });

  it('navigates to Developer API page when Developer API button is clicked, and returns home', async () => {
    window.history.pushState({}, '', '/');
    api.getHealthStatus.mockResolvedValue({ status: 'ok', database: 'connected' });
    api.getTimetables.mockResolvedValue([]);
    api.getSessions.mockResolvedValue({ level: 1, sessions: [] });
    api.getLevelStatus.mockResolvedValue({ level: 1, totalSessions: 0 });

    render(<App />);

    const devApiButton = screen.getByRole('button', { name: /Developer API/i });
    fireEvent.click(devApiButton);

    expect(
      screen.getByRole('heading', { name: /FAS Timetable API — Developer Documentation/i })
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/developers');

    // Click Student Timetable to return
    const studentBtn = screen.getByRole('button', { name: /Student Timetable Portal/i });
    fireEvent.click(studentBtn);

    await waitFor(() => {
      expect(screen.getByText('Academic Timetable Portal')).toBeInTheDocument();
      expect(window.location.pathname).toBe('/');
    });
  });

  it('renders Developer API page directly when pathname is /developers', () => {
    window.history.pushState({}, '', '/developers');
    render(<App />);

    expect(
      screen.getByRole('heading', { name: /FAS Timetable API — Developer Documentation/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/Canonical API Base URL/i)).toBeInTheDocument();
  });

  it('navigates to Project README viewer when README button is clicked, and returns home', async () => {
    window.history.pushState({}, '', '/');
    api.getHealthStatus.mockResolvedValue({ status: 'ok', database: 'connected' });
    api.getTimetables.mockResolvedValue([]);
    api.getSessions.mockResolvedValue({ level: 1, sessions: [] });
    api.getLevelStatus.mockResolvedValue({ level: 1, totalSessions: 0 });

    render(<App />);

    const readmeButtons = screen.getAllByRole('button', { name: /README/i });
    fireEvent.click(readmeButtons[0]);

    expect(
      screen.getByRole('heading', { name: /Project README/i })
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/readme');

    // Click back to timetable button to return
    const returnBtn = screen.getByRole('button', { name: /Back to Timetables/i });
    fireEvent.click(returnBtn);

    await waitFor(() => {
      expect(screen.getByText('Academic Timetable Portal')).toBeInTheDocument();
      expect(window.location.pathname).toBe('/');
    });
  });

  it('renders Project README page directly when pathname is /readme', () => {
    window.history.pushState({}, '', '/readme');
    render(<App />);

    expect(
      screen.getByRole('heading', { name: /Project README/i })
    ).toBeInTheDocument();
  });

  it('renders footer with Kasun Herath maintainer credits and GitHub repository link', async () => {
    window.history.pushState({}, '', '/');
    api.getHealthStatus.mockResolvedValue({ status: 'ok', database: 'connected' });
    api.getTimetables.mockResolvedValue([]);
    api.getSessions.mockResolvedValue({ level: 1, sessions: [] });
    api.getLevelStatus.mockResolvedValue({ level: 1, totalSessions: 0 });

    render(<App />);

    const maintainerLink = screen.getByRole('link', { name: /Kasun Herath/i });
    expect(maintainerLink).toBeInTheDocument();
    expect(maintainerLink).toHaveAttribute('href', 'https://github.com/KasunHerath-dev');
    expect(maintainerLink).toHaveAttribute('target', '_blank');
    expect(maintainerLink).toHaveAttribute('rel', 'noopener noreferrer');

    const githubRepoLink = screen.getByRole('link', { name: /GitHub Repository/i });
    expect(githubRepoLink).toBeInTheDocument();
    expect(githubRepoLink).toHaveAttribute(
      'href',
      'https://github.com/KasunHerath-dev/fas-timetable-downloader'
    );
  });
});
