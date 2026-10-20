import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AcademicCalendarViewer from './components/AcademicCalendarViewer';
import * as api from './services/api';

vi.mock('./services/api');

describe('AcademicCalendarViewer Component', () => {
  const sampleCalendar = {
    id: 'cal_2024_2025_approved_123',
    calendarId: 'cal_2024_2025_approved_123',
    academicYear: '2024/2025',
    academicYearStart: 2024,
    academicYearEnd: 2025,
    documentTitle: 'CALENDAR OF DATES',
    documentStatus: 'approved',
    revision: 'Original',
    levels: [1, 2, 3, 4],
    semesters: ['Semester I', 'Semester II'],
    sourceUrl: 'https://fas.wyb.ac.lk/wp-content/uploads/2026/07/COD-2024-2025.pdf',
    signatureDate: '2026-07-03',
    publicationDate: '2026-07-17',
    sha256: '6ca12081e4b8948cc161e130503931060303a1982961e84c19698b80d983c964',
    isCurrent: true,
    isCurrentConfirmed: true,
    selectionReason: 'Verified official approved calendar for Academic Year 2024/2025',
    activitiesCount: 2,
    activities: [
      {
        activity: 'Academic Session',
        category: 'academic_session',
        semester: 'Semester I',
        startDate: '2026-08-03',
        endDate: '2026-09-27',
        durationRaw: '08 Weeks',
        durationWeeks: 8.0,
      },
      {
        activity: 'Examination',
        category: 'examination',
        semester: 'Semester II',
        startDate: '2027-05-24',
        endDate: '2027-06-20',
        durationRaw: '04 Weeks',
        durationWeeks: 4.0,
      },
    ],
    revisionHistory: [],
  };

  const sampleStatus = {
    lastCheckedAt: '2026-10-20T12:00:00+05:30',
    discoverySuccess: true,
    currentCalendarConfirmed: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    api.getAcademicCalendars.mockResolvedValue([sampleCalendar]);
    api.getCurrentAcademicCalendar.mockResolvedValue(sampleCalendar);
    api.getAcademicCalendarStatus.mockResolvedValue(sampleStatus);
    api.getUpcomingActivities.mockResolvedValue({
      activities: [
        {
          activity: 'Academic Session',
          category: 'academic_session',
          semester: 'Semester I',
          startDate: '2026-08-03',
          endDate: '2026-09-27',
          durationRaw: '08 Weeks',
          status: 'ongoing',
        },
      ],
    });
  });

  it('renders calendar details and verified official badge', async () => {
    render(<AcademicCalendarViewer onNavigateHome={vi.fn()} />);

    expect(screen.getByText(/Loading Official Academic Calendar.../i)).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /Academic Year 2024\/2025/i })
      ).toBeInTheDocument();
      expect(screen.getByText(/Official Verified Active/i)).toBeInTheDocument();
      expect(screen.getByText(/CALENDAR OF DATES • Levels 1, 2, 3, 4/i)).toBeInTheDocument();
    });
  });

  it('renders activities and duration pills', async () => {
    render(<AcademicCalendarViewer onNavigateHome={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getAllByText(/Academic Session/i).length).toBeGreaterThan(0);
      expect(screen.getByText('08 Weeks')).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Examination' })).toBeInTheDocument();
      expect(screen.getByText('04 Weeks')).toBeInTheDocument();
    });
  });

  it('switches between Semester Schedules and Upcoming & Ongoing tabs', async () => {
    render(<AcademicCalendarViewer onNavigateHome={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Upcoming & Ongoing/i })).toBeInTheDocument();
    });

    const upcomingBtn = screen.getByRole('button', { name: /Upcoming & Ongoing/i });
    fireEvent.click(upcomingBtn);

    await waitFor(() => {
      expect(screen.getByText(/Ongoing Now/i)).toBeInTheDocument();
    });
  });

  it('calls onNavigateHome when back arrow button is clicked', async () => {
    const handleHome = vi.fn();
    render(<AcademicCalendarViewer onNavigateHome={handleHome} />);

    const backBtn = screen.getByLabelText(/Back to Timetables/i);
    fireEvent.click(backBtn);

    expect(handleHome).toHaveBeenCalledTimes(1);
  });
});
