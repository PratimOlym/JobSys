import React, { useState, useEffect } from 'react'
import { fetchDashboardStats, triggerScan } from '../services/api'
import StatusBadge from './StatusBadge'

export default function Dashboard({ onNavigate }) {
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)
    const [scanning, setScanning] = useState(false)
    const [toast, setToast] = useState(null)

    useEffect(() => {
        loadStats()
    }, [])

    async function loadStats() {
        try {
            setLoading(true)
            const data = await fetchDashboardStats()
            setStats(data)
        } catch (err) {
            console.error('Failed to load stats:', err)
        } finally {
            setLoading(false)
        }
    }

    async function handleScan() {
        try {
            setScanning(true)
            await triggerScan()
            showToast('Job scan triggered successfully!', 'success')
        } catch (err) {
            showToast('Failed to trigger scan: ' + err.message, 'error')
        } finally {
            setScanning(false)
        }
    }

    function showToast(message, type) {
        setToast({ message, type })
        setTimeout(() => setToast(null), 4000)
    }

    if (loading) {
        return (
            <div className="loading">
                <div className="spinner" />
                Loading dashboard...
            </div>
        )
    }

    return (
        <div>
            <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h1>Dashboard</h1>
                    <p>Overview of your job application pipeline</p>
                </div>
                <button className="btn btn-primary" onClick={handleScan} disabled={scanning}>
                    {scanning ? '⏳ Scanning...' : '🔍 Scan Jobs'}
                </button>
            </div>

            {/* Stats Grid */}
            <div className="stats-grid">
                <div className="stat-card total">
                    <span className="stat-label">Total Jobs</span>
                    <span className="stat-value">{stats?.total_jobs || 0}</span>
                </div>
                <div className="stat-card new">
                    <span className="stat-label">New / Pending</span>
                    <span className="stat-value">{stats?.new || 0}</span>
                </div>
                <div className="stat-card matched">
                    <span className="stat-label">Matched</span>
                    <span className="stat-value">{stats?.resume_match_done || 0}</span>
                </div>
                <div className="stat-card ready">
                    <span className="stat-label">Documents Ready</span>
                    <span className="stat-value">{stats?.documents_ready || 0}</span>
                </div>
                <div className="stat-card error">
                    <span className="stat-label">Errors</span>
                    <span className="stat-value">{stats?.error || 0}</span>
                </div>
            </div>

            {/* Average Match Score */}
            {stats?.avg_match_score > 0 && (
                <div className="card" style={{ marginBottom: 24, maxWidth: 300 }}>
                    <div className="card-header">
                        <span className="card-title">Avg. Match Score</span>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div className="score-ring">
                            <svg width="120" height="120" viewBox="0 0 120 120">
                                <circle className="score-ring-bg" cx="60" cy="60" r="50" />
                                <circle
                                    className="score-ring-fill"
                                    cx="60" cy="60" r="50"
                                    stroke={stats.avg_match_score >= 70 ? 'var(--status-ready)' : stats.avg_match_score >= 40 ? 'var(--status-new)' : 'var(--status-error)'}
                                    strokeDasharray={`${2 * Math.PI * 50}`}
                                    strokeDashoffset={`${2 * Math.PI * 50 * (1 - stats.avg_match_score / 100)}`}
                                />
                            </svg>
                            <span className="score-ring-text" style={{ color: stats.avg_match_score >= 70 ? 'var(--status-ready)' : stats.avg_match_score >= 40 ? 'var(--status-new)' : 'var(--status-error)' }}>
                                {stats.avg_match_score}%
                            </span>
                        </div>
                    </div>
                </div>
            )}

            {/* Recent Jobs */}
            {stats?.recent_jobs?.length > 0 && (
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Recent Jobs</span>
                        <button className="btn btn-secondary" onClick={() => onNavigate('jobs')}>
                            View All →
                        </button>
                    </div>
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Title</th>
                                <th>Company</th>
                                <th>Status</th>
                                <th>Score</th>
                                <th>Added</th>
                            </tr>
                        </thead>
                        <tbody>
                            {stats.recent_jobs.map(job => (
                                <tr key={job.job_id} onClick={() => onNavigate('job-detail', job.job_id)}>
                                    <td>{job.job_title}</td>
                                    <td>{job.company || '—'}</td>
                                    <td><StatusBadge status={job.status} /></td>
                                    <td className={`score-cell ${job.match_score >= 70 ? 'score-high' : job.match_score >= 40 ? 'score-mid' : 'score-low'}`}>
                                        {job.match_score ? `${job.match_score}%` : '—'}
                                    </td>
                                    <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                                        {job.created_at ? new Date(job.created_at).toLocaleDateString() : '—'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}
        </div>
    )
}
