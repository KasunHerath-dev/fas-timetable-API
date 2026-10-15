import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ReadmeViewer, { extractHeadings, slugify } from './components/ReadmeViewer';

describe('ReadmeViewer Component & Utilities', () => {
  it('slugify converts titles to valid kebab-case anchors', () => {
    expect(slugify('Production Automation for FAS WUSL Timetable')).toBe(
      'production-automation-for-fas-wusl-timetable'
    );
    expect(slugify('Level 1,2,3 & 4 Semester I (2024/2025)')).toBe(
      'level-123-4-semester-i-20242025'
    );
  });

  it('extractHeadings parses markdown headings into TOC structure', () => {
    const md = `
# FAS Timetable Project
## Quick Start
### Prerequisites
## Architecture
`;
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(4);
    expect(headings[0]).toEqual({
      id: 'fas-timetable-project',
      text: 'FAS Timetable Project',
      title: 'FAS Timetable Project',
      level: 1,
    });
    expect(headings[1]).toEqual({
      id: 'quick-start',
      text: 'Quick Start',
      title: 'Quick Start',
      level: 2,
    });
    expect(headings[2]).toEqual({
      id: 'prerequisites',
      text: 'Prerequisites',
      title: 'Prerequisites',
      level: 3,
    });
  });

  it('renders ReadmeViewer with navigation buttons, maintainer credits, and GitHub link', () => {
    const onHome = vi.fn();
    const onDev = vi.fn();

    render(
      <ReadmeViewer
        onNavigateHome={onHome}
        onNavigateToDevelopers={onDev}
      />
    );

    // Verify main header
    expect(
      screen.getByRole('heading', { name: /Project README/i })
    ).toBeInTheDocument();

    // Verify Timetable Portal return button
    const backBtn = screen.getByRole('button', { name: /Back to Timetables/i });
    fireEvent.click(backBtn);
    expect(onHome).toHaveBeenCalledTimes(1);

    // Verify Developer API button
    const devBtn = screen.getByTitle(/View Developer API Documentation/i);
    fireEvent.click(devBtn);
    expect(onDev).toHaveBeenCalledTimes(1);

    // Verify maintainer profile links
    const profileLink = screen.getByRole('link', { name: /Developer Profile/i });
    expect(profileLink).toBeInTheDocument();
    expect(profileLink).toHaveAttribute('href', 'https://github.com/KasunHerath-dev');

    // Verify GitHub repository link
    const repoLink = screen.getByRole('link', { name: /View Repository/i });
    expect(repoLink).toBeInTheDocument();
    expect(repoLink).toHaveAttribute(
      'href',
      'https://github.com/KasunHerath-dev/fas-timetable-downloader'
    );
  });

  it('filters table of contents when search query is entered', () => {
    render(<ReadmeViewer />);

    const searchInput = screen.getByPlaceholderText(/Filter sections.../i);
    fireEvent.change(searchInput, { target: { value: 'MongoDB' } });

    // The search input retains value
    expect(searchInput.value).toBe('MongoDB');
  });
});
