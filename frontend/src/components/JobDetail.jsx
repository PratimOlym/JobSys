import React, { useState, useEffect } from 'react'
import { fetchJob, regenerateDocuments } from '../services/api'
import StatusBadge from './StatusBadge'

export default function JobDetail({ jobId, onBack }) {
    const [job, setJob] = useState(null)
    const [loading, setLoading] = useState(true)
    const [regenerating, setRegenerating] = useState(false)
    const [toast, setToast] = useState(null)

    useEffect(() => {
        loadJob()
    }, [jobId])

    async function loadJob() {
        try {
            setLoading(true)
            const data = await fetchJob(jobId)
            setJob(data)
        } catch (err) {
            console.error('Failed to load job:', err)
        } finally {
            setLoading(false)
        }
    }

    async function handleRegenerate() {
        try {
            setRegenerating(true)
            await regenerateDocuments(jobId)
            showToast('Document regeneration triggered!', 'success')
        } catch (err) {
            showToast('Failed: ' + err.message, 'error')
        } finally {
            setRegenerating(false)
        }
    }

    function showToast(message, type) {
        setToast({ message, type })
        setTimeout(() => setToast(null), 4000)
    }

    function scoreColor(score) {
        if (score >= 70) return 'var(--status-ready)'
        if (score >= 40) return 'var(--status-new)'
        return 'var(--status-error)'
    }

    if (loading) {
        return (
            <div className="loading">
                <div className="spinner" />
                Loading job details...
            </div>
        )
    }

    if (!job) {
        return (
            <div className="empty-state">
                <div className="empty-icon">❌</div>
                <h3>Job not found</h3>
                <button className="btn btn-secondary" onClick={onBack}>← Go Back</button>
            </div>
        )
    }

    const matchDetails = job.match_details || {}

    return (
        <div>
            <button className="back-link" onClick={onBack}>← Back to Jobs</button>

            <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h1>{job.job_title}</h1>
                    <p>
                        {job.company && <span>{job.company}</span>}
                        {job.location && <span> · {job.location}</span>}
                        {job.date_posted && <span> · Posted {job.date_posted}</span>}
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <StatusBadge status={job.status} />
                    {(job.status === 'resume-match-done' || job.status === 'documents-ready') && (
                        <button className="btn btn-teal" onClick={handleRegenerate} disabled={regenerating}>
                            {regenerating ? '⏳ Working...' : '🔄 Regenerate'}
                        </button>
                    )}
                </div>
            </div>

            <div className="detail-grid">
                {/* Left Column — JD and Details */}
                <div>
                    {/* Job Details */}
                    <div className="detail-section" style={{ marginBottom: 24 }}>
                        <h3>Job Details</h3>
                        <div className="detail-meta">
                            <div className="meta-item">
                                <span className="meta-label">Company</span>
                                <span className="meta-value">{job.company || '—'}</span>
                            </div>
                            <div className="meta-item">
                                <span className="meta-label">Location</span>
                                <span className="meta-value">{job.location || '—'}</span>
                            </div>
                            <div className="meta-item">
                                <span className="meta-label">Posted</span>
                                <span className="meta-value">{job.date_posted || '—'}</span>
                            </div>
                            <div className="meta-item">
                                <span className="meta-label">Source</span>
                                <span className="meta-value">
                                    {job.job_url ? (
                                        <a href={job.job_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.85rem' }}>
                                            View Original ↗
                                        </a>
                                    ) : '—'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Job Description */}
                    <div className="detail-section">
                        <h3>Job Description</h3>
                        <div className="jd-content">
                            {job.job_details || 'No description available.'}
                        </div>
                    </div>
                </div>

                {/* Right Column — Matching & Documents */}
                <div>
                    {/* Match Score */}
                    {job.match_score > 0 && (
                        <div className="detail-section" style={{ marginBottom: 24, textAlign: 'center' }}>
                            <h3>Match Score</h3>
                            <div className="score-ring">
                                <svg width="120" height="120" viewBox="0 0 120 120">
                                    <circle className="score-ring-bg" cx="60" cy="60" r="50" />
                                    <circle
                                        className="score-ring-fill"
                                        cx="60" cy="60" r="50"
                                        stroke={scoreColor(job.match_score)}
                                        strokeDasharray={`${2 * Math.PI * 50}`}
                                        strokeDashoffset={`${2 * Math.PI * 50 * (1 - job.match_score / 100)}`}
                                    />
                                </svg>
                                <span className="score-ring-text" style={{ color: scoreColor(job.match_score) }}>
                                    {job.match_score}%
                                </span>
                            </div>
                            {job.best_resume_name && (
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 8 }}>
                                    Best match: <strong style={{ color: 'var(--text-secondary)' }}>{job.best_resume_name}</strong>
                                </p>
                            )}
                        </div>
                    )}

                    {/* Matched Skills */}
                    {matchDetails.matched_skills?.length > 0 && (
                        <div className="detail-section" style={{ marginBottom: 24 }}>
                            <h3>Matched Skills</h3>
                            <div className="skill-tags">
                                {matchDetails.matched_skills.map((skill, i) => (
                                    <span key={i} className="skill-tag matched">{skill}</span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Missing Skills */}
                    {matchDetails.missing_skills?.length > 0 && (
                        <div className="detail-section" style={{ marginBottom: 24 }}>
                            <h3>Missing Skills</h3>
                            <div className="skill-tags">
                                {matchDetails.missing_skills.map((skill, i) => (
                                    <span key={i} className="skill-tag missing">{skill}</span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Recommendation */}
                    {matchDetails.recommendation && (
                        <div className="detail-section" style={{ marginBottom: 24 }}>
                            <h3>AI Recommendation</h3>
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                                {matchDetails.recommendation}
                            </p>
                        </div>
                    )}

                    {/* Documents */}
                    {(job.optimized_resume_url || job.cover_letter_url) && (
                        <div className="detail-section">
                            <h3>Documents</h3>
                            <div className="doc-actions">
                                {job.optimized_resume_url && (
                                    <a href={job.optimized_resume_url} target="_blank" rel="noopener noreferrer" className="doc-link">
                                        <span className="doc-icon">📄</span>
                                        <span className="doc-info">
                                            <span className="doc-label">Optimized Resume</span>
                                            <span className="doc-path">.docx · Click to download</span>
                                        </span>
                                        <span>↓</span>
                                    </a>
                                )}
                                {job.cover_letter_url && (
                                    <a href={job.cover_letter_url} target="_blank" rel="noopener noreferrer" className="doc-link">
                                        <span className="doc-icon">✉️</span>
                                        <span className="doc-info">
                                            <span className="doc-label">Cover Letter</span>
                                            <span className="doc-path">.docx · Click to download</span>
                                        </span>
                                        <span>↓</span>
                                    </a>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}
        </div>
    )
}
