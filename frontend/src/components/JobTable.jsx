import React, { useState, useEffect } from 'react'
import { fetchJobs } from '../services/api'
import StatusBadge from './StatusBadge'

const FILTERS = [
    { label: 'All', value: null },
    { label: 'New', value: 'new' },
    { label: 'Matched', value: 'resume-match-done' },
    { label: 'Ready', value: 'documents-ready' },
    { label: 'Error', value: 'error' },
]

export default function JobTable({ onSelectJob }) {
    const [jobs, setJobs] = useState([])
    const [loading, setLoading] = useState(true)
    const [activeFilter, setActiveFilter] = useState(null)
    const [sortField, setSortField] = useState('created_at')
    const [sortDir, setSortDir] = useState('desc')

    useEffect(() => {
        loadJobs()
    }, [activeFilter])

    async function loadJobs() {
        try {
            setLoading(true)
            const data = await fetchJobs(activeFilter)
            setJobs(data.jobs || [])
        } catch (err) {
            console.error('Failed to load jobs:', err)
        } finally {
            setLoading(false)
        }
    }

    function handleSort(field) {
        if (sortField === field) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc')
        } else {
            setSortField(field)
            setSortDir('desc')
        }
    }

    const sortedJobs = [...jobs].sort((a, b) => {
        const av = a[sortField] || ''
        const bv = b[sortField] || ''
        const cmp = typeof av === 'number' ? av - bv : String(av).localeCompare(String(bv))
        return sortDir === 'asc' ? cmp : -cmp
    })

    return (
        <div>
            <div className="page-header">
                <h1>Job Listings</h1>
                <p>{jobs.length} jobs tracked</p>
            </div>

            {/* Filter Chips */}
            <div className="filters-bar">
                {FILTERS.map(f => (
                    <button
                        key={f.label}
                        className={`filter-chip ${activeFilter === f.value ? 'active' : ''}`}
                        onClick={() => setActiveFilter(f.value)}
                    >
                        {f.label}
                    </button>
                ))}
                <button className="btn btn-secondary" onClick={loadJobs} style={{ marginLeft: 'auto' }}>
                    ↻ Refresh
                </button>
            </div>

            {loading ? (
                <div className="loading">
                    <div className="spinner" />
                    Loading jobs...
                </div>
            ) : sortedJobs.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">📋</div>
                    <h3>No jobs found</h3>
                    <p>Try scanning for new jobs or adjusting your filters.</p>
                </div>
            ) : (
                <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('job_title')}>
                                    Title {sortField === 'job_title' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                                </th>
                                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('company')}>
                                    Company {sortField === 'company' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                                </th>
                                <th>Location</th>
                                <th>Status</th>
                                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('match_score')}>
                                    Score {sortField === 'match_score' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                                </th>
                                <th>Best Resume</th>
                                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('created_at')}>
                                    Added {sortField === 'created_at' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedJobs.map(job => (
                                <tr key={job.job_id} onClick={() => onSelectJob(job.job_id)}>
                                    <td title={job.job_title}>{job.job_title}</td>
                                    <td>{job.company || '—'}</td>
                                    <td>{job.location || '—'}</td>
                                    <td><StatusBadge status={job.status} /></td>
                                    <td className={`score-cell ${job.match_score >= 70 ? 'score-high' : job.match_score >= 40 ? 'score-mid' : 'score-low'}`}>
                                        {job.match_score ? `${job.match_score}%` : '—'}
                                    </td>
                                    <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                        {job.best_resume_name || '—'}
                                    </td>
                                    <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                        {job.created_at ? new Date(job.created_at).toLocaleDateString() : '—'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}
