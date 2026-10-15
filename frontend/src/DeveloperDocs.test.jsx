import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import DeveloperDocs, { getResolvedApiBaseUrl } from './components/DeveloperDocs';

describe('DeveloperDocs Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('resolves API base URL correctly based on window.location.origin', () => {
    const resolved = getResolvedApiBaseUrl();
    expect(resolved).toMatch(/\/api$/);
  });

  it('renders documentation header, canonical base URL, and read-only banner', () => {
    render(<DeveloperDocs onNavigateHome={vi.fn()} />);

    expect(
      screen.getByRole('heading', { name: /FAS Timetable API — Developer Documentation/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/Canonical API Base URL/i)).toBeInTheDocument();
    expect(screen.getByText(/Read-Only & Public/i)).toBeInTheDocument();
    expect(screen.getByText(/Provenance & Needs Review/i)).toBeInTheDocument();
    expect(screen.getByText(/Dynamic Term Discovery/i)).toBeInTheDocument();
  });

  it('documents all 4 verified endpoints with parameters and response schemas', () => {
    render(<DeveloperDocs onNavigateHome={vi.fn()} />);

    expect(screen.getByText('/api/health')).toBeInTheDocument();
    expect(screen.getAllByText('/api/timetables').length).toBeGreaterThan(0);
    expect(screen.getByText('/api/timetables/{level}/sessions')).toBeInTheDocument();
    expect(screen.getByText('/api/timetables/{level}/status')).toBeInTheDocument();

    // Check parameter documentation
    expect(screen.getAllByText('{level}').length).toBeGreaterThan(0);
    expect(screen.getAllByText('academicYear').length).toBeGreaterThan(0);
    expect(screen.getAllByText('semester').length).toBeGreaterThan(0);
    expect(screen.getAllByText('day').length).toBeGreaterThan(0);
    expect(screen.getAllByText('subjectCode').length).toBeGreaterThan(0);
  });

  it('handles copying the API base URL to clipboard with feedback', async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    render(<DeveloperDocs onNavigateHome={vi.fn()} />);

    const copyBaseUrlBtn = screen.getByRole('button', { name: /Copy API Base URL/i });
    fireEvent.click(copyBaseUrlBtn);

    expect(writeTextMock).toHaveBeenCalledWith(getResolvedApiBaseUrl());

    await waitFor(() => {
      expect(screen.getByText(/Copied Base URL!/i)).toBeInTheDocument();
    });
  });

  it('switches between JavaScript, Python, and cURL integration code examples', () => {
    render(<DeveloperDocs onNavigateHome={vi.fn()} />);

    // Default tab is JavaScript
    expect(screen.getByText(/fetchLevel2FridaySchedule/i)).toBeInTheDocument();

    // Switch to Python
    const pythonTab = screen.getByRole('button', { name: /Python \(requests\)/i });
    fireEvent.click(pythonTab);
    expect(screen.getByText(/def get_level2_friday_sessions\(\):/i)).toBeInTheDocument();

    // Switch to cURL
    const curlTab = screen.getByRole('button', { name: /cURL \/ REST/i });
    fireEvent.click(curlTab);
    expect(screen.getByText(/curl -X GET/i)).toBeInTheDocument();
  });

  it('displays the data dictionary including validationStatus and warnings', () => {
    render(<DeveloperDocs onNavigateHome={vi.fn()} />);

    expect(screen.getByText('rawCellText')).toBeInTheDocument();
    expect(screen.getByText('validationStatus')).toBeInTheDocument();
    expect(screen.getAllByText('warnings').length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Displaying Review Warnings to Students \(Do Not Silently Confirm\)/i)
    ).toBeInTheDocument();
  });

  it('calls onNavigateHome when return button or Student Timetable button is clicked', () => {
    const navigateHomeMock = vi.fn();
    render(<DeveloperDocs onNavigateHome={navigateHomeMock} />);

    const backButton = screen.getByRole('button', { name: /Back to Timetables/i });
    fireEvent.click(backButton);
    expect(navigateHomeMock).toHaveBeenCalledTimes(1);

    const studentTimetableBtn = screen.getByRole('button', { name: /Student Timetable Portal/i });
    fireEvent.click(studentTimetableBtn);
    expect(navigateHomeMock).toHaveBeenCalledTimes(2);
  });
});
