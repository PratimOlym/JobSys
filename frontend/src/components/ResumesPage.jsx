import React, { useState, useEffect } from 'react'
import {
    fetchResumes,
    uploadResume,
    deleteResume,
    fetchResumeSummaries,
    generateResumeSummaries,
    matchResumesToJd,
} from '../services/api'

export default function ResumesPage() {
    const [resumes, setResumes] = useState([])
    const [summaries, setSummaries] = useState([])
    const [matchResults, setMatchResults] = useState([])
    const [loadingResumes, setLoadingResumes] = useState(true)
    const [loadingSummaries, setLoadingSummaries] = useState(true)
    const [generating, setGenerating] = useState(false)
    const [matching, setMatching] = useState(false)
    const [uploading, setUploading] = useState(false)
    const [deletingKey, setDeletingKey] = useState(null)
    const [toast, setToast] = useState(null)
    const [jdInput, setJdInput] = useState('')
    const [jobTitle, setJobTitle] = useState('')
    const [company, setCompany] = useState('')
    const [activeTab, setActiveTab] = useState('resumes')
    const [expandedCard, setExpandedCard] = useState(null)

    useEffect(() => { loadResumes(); loadSummaries() }, [])

    // ── Data ──────────────────────────────────────────────────────────────────
    async function loadResumes() {
        try {
            setLoadingResumes(true)
            const data = await fetchResumes()
            setResumes(data.resumes || [])
        } catch (err) {
            showToast('Failed to load resumes: ' + err.message, 'error')
        } finally {
            setLoadingResumes(false)
        }
    }

    async function loadSummaries() {
        try {
            setLoadingSummaries(true)
            const data = await fetchResumeSummaries()
            setSummaries(data.summaries || [])
        } catch {
            // Summaries may not exist yet — silently ignore
        } finally {
            setLoadingSummaries(false)
        }
    }

    // ── Actions ───────────────────────────────────────────────────────────────
    async function handleGenerateSummaries() {
        try {
            setGenerating(true)
            showToast('⏳ Gemini is analysing your resumes…', 'info')
            const data = await generateResumeSummaries()
            setSummaries(data.summaries || [])
            setMatchResults([])
            const errCount = data.errors?.length || 0
            showToast(
                `✅ ${data.summaries?.length || 0} summaries generated${errCount ? ` (${errCount} errors)` : ''}`,
                'success'
            )
            setActiveTab('summaries')
        } catch (err) {
            showToast('Generation failed: ' + err.message, 'error')
        } finally {
            setGenerating(false)
        }
    }

    async function handleMatch() {
        if (!jdInput.trim()) { showToast('Paste a job description first.', 'error'); return }
        if (summaries.length === 0) { showToast('Generate summaries first!', 'error'); return }
        try {
            setMatching(true)
            showToast('🤖 Gemini is scoring all resumes…', 'info')
            const jobMeta = { job_title: jobTitle, company, location: '' }
            const data = await matchResumesToJd(jdInput, jobMeta)
            setMatchResults(data.results || [])
            showToast(
                `✅ Scored ${data.total} resume${data.total !== 1 ? 's' : ''}. Best match: ${data.best_match?.resume_name || '—'}`,
                'success'
            )
        } catch (err) {
            showToast('Matching failed: ' + err.message, 'error')
        } finally {
            setMatching(false)
        }
    }

    async function handleUpload(e) {
        const file = e.target.files[0]
        if (!file) return
        try {
            setUploading(true)
            await uploadResume(file)
            showToast('Resume uploaded!', 'success')
            loadResumes()
        } catch (err) {
            showToast('Upload failed: ' + err.message, 'error')
        } finally {
            setUploading(false)
            e.target.value = ''
        }
    }

    async function handleDelete(key) {
        if (!window.confirm('Delete this resume?')) return
        try {
            setDeletingKey(key)
            await deleteResume(key)
            showToast('Deleted.', 'success')
            loadResumes()
        } catch (err) {
            showToast('Delete failed: ' + err.message, 'error')
        } finally {
            setDeletingKey(null)
        }
    }

    function showToast(message, type = 'success') {
        setToast({ message, type })
        setTimeout(() => setToast(null), 5000)
    }

    // ── Sub-components ────────────────────────────────────────────────────────
    function scoreColor(score) {
        if (score >= 70) return 'var(--status-ready)'
        if (score >= 45) return 'var(--status-new)'
        return 'var(--status-error)'
    }

    function ScoreRing({ score, size = 80, label }) {
        const r = (size - 12) / 2
        const circ = 2 * Math.PI * r
        const pct = Math.min(100, Math.max(0, score))
        const offset = circ - (pct / 100) * circ
        const col = scoreColor(pct)
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                <div style={{ width: size, height: size, position: 'relative', flexShrink: 0 }}>
                    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
                        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
                            stroke="var(--border)" strokeWidth={8} />
                        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
                            stroke={col} strokeWidth={8} strokeLinecap="round"
                            strokeDasharray={circ} strokeDashoffset={offset}
                            style={{ transition: 'stroke-dashoffset 0.9s ease' }} />
                    </svg>
                    <div style={{
                        position: 'absolute', top: '50%', left: '50%',
                        transform: 'translate(-50%,-50%)',
                        fontSize: size < 72 ? '0.8rem' : '1.1rem',
                        fontWeight: 700, color: col,
                    }}>
                        {Math.round(pct)}
                    </div>
                </div>
                {label && (
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                        {label}
                    </span>
                )}
            </div>
        )
    }

    function MiniBar({ value, label, color }) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.78rem' }}>
                <span style={{ width: 90, color: 'var(--text-muted)', flexShrink: 0 }}>{label}</span>
                <div style={{ flex: 1, height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{
                        height: '100%', width: `${Math.round(value)}%`,
                        background: color,
                        borderRadius: 3,
                        transition: 'width 0.8s ease',
                    }} />
                </div>
                <span style={{ width: 28, textAlign: 'right', fontWeight: 600, color }}>{Math.round(value)}</span>
            </div>
        )
    }

    function MatchResultCard({ r, rank }) {
        const isExpanded = expandedCard === r.resume_name
        const toggle = () => setExpandedCard(isExpanded ? null : r.resume_name)
        const rankMedal = rank === 0 ? '🥇' : rank === 1 ? '🥈' : rank === 2 ? '🥉' : `#${rank + 1}`
        return (
            <div
                onClick={toggle}
                style={{
                    background: rank === 0 ? 'linear-gradient(135deg,rgba(108,99,255,0.08),rgba(100,255,218,0.04))' : 'var(--bg-card)',
                    border: `1px solid ${rank === 0 ? 'rgba(108,99,255,0.4)' : isExpanded ? 'var(--accent-primary)' : 'var(--border)'}`,
                    borderRadius: 'var(--radius)',
                    padding: '20px 24px',
                    cursor: 'pointer',
                    transition: 'all 0.25s',
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = rank === 0 ? 'rgba(108,99,255,0.4)' : isExpanded ? 'var(--accent-primary)' : 'var(--border)'}
            >
                {/* Header row */}
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
                    {/* Rank + Overall score ring */}
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                        <div style={{ fontSize: rank <= 2 ? '1.6rem' : '0.85rem', fontWeight: 700, color: 'var(--text-muted)' }}>
                            {rankMedal}
                        </div>
                    </div>
                    <ScoreRing score={r.overall_score} size={80} label="Overall" />

                    {/* Info */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text-primary)', marginBottom: 2 }}>
                            {r.resume_name}
                        </div>
                        {/* Score bars */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                            <MiniBar value={r.keyword_score ?? 0} label="Keyword" color="var(--accent-primary)" />
                            <MiniBar value={r.semantic_score ?? 0} label="Semantic" color="var(--accent-teal)" />
                        </div>
                    </div>

                    {/* Arrow */}
                    <div style={{ color: 'var(--text-muted)', fontSize: '1.1rem', alignSelf: 'center', marginLeft: 8 }}>
                        {isExpanded ? '▲' : '▼'}
                    </div>
                </div>

                {/* Expanded detail section */}
                {isExpanded && (
                    <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                        {/* Recommendation */}
                        {r.recommendation && (
                            <div style={{
                                background: 'rgba(108,99,255,0.08)',
                                border: '1px solid rgba(108,99,255,0.2)',
                                borderRadius: 'var(--radius-sm)',
                                padding: '10px 14px',
                                marginBottom: 14,
                                fontSize: '0.84rem',
                                color: 'var(--text-secondary)',
                                lineHeight: 1.6,
                            }}>
                                💡 <strong style={{ color: 'var(--accent-primary)' }}>Recommendation:</strong> {r.recommendation}
                            </div>
                        )}

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            {/* Matched skills */}
                            <div>
                                <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 8 }}>
                                    ✅ Matched Skills ({(r.matched_skills || []).length})
                                </div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                                    {(r.matched_skills || []).map((sk, i) => (
                                        <span key={i} className="skill-tag matched" style={{ fontSize: '0.7rem' }}>{sk}</span>
                                    ))}
                                    {(r.matched_skills || []).length === 0 && (
                                        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>—</span>
                                    )}
                                </div>
                            </div>
                            {/* Missing skills */}
                            <div>
                                <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 8 }}>
                                    ❌ Missing Skills ({(r.missing_skills || []).length})
                                </div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                                    {(r.missing_skills || []).map((sk, i) => (
                                        <span key={i} className="skill-tag missing" style={{ fontSize: '0.7rem' }}>{sk}</span>
                                    ))}
                                    {(r.missing_skills || []).length === 0 && (
                                        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>—</span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        )
    }

    function SummaryCard({ s }) {
        const isExpanded = expandedCard === `summary-${s.resume_name}`
        return (
            <div
                onClick={() => setExpandedCard(isExpanded ? null : `summary-${s.resume_name}`)}
                style={{
                    background: 'var(--bg-card)',
                    border: `1px solid ${isExpanded ? 'var(--accent-primary)' : 'var(--border)'}`,
                    borderRadius: 'var(--radius)',
                    padding: '18px 22px',
                    cursor: 'pointer',
                    transition: 'all 0.25s',
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = isExpanded ? 'var(--accent-primary)' : 'var(--border)'}
            >
                <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
                    <div style={{
                        width: 40, height: 40, borderRadius: '50%',
                        background: 'linear-gradient(135deg,var(--accent-primary),var(--accent-teal))',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '1.2rem', flexShrink: 0,
                    }}>📄</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.92rem' }}>{s.resume_name}</div>
                        <div style={{ color: 'var(--accent-teal)', fontSize: '0.8rem', margin: '2px 0 6px' }}>{s.headline}</div>
                        <div style={{ display: 'flex', gap: 12 }}>
                            <span style={{ fontSize: '0.73rem', color: 'var(--text-muted)' }}>🕐 {s.total_experience_years} yrs</span>
                            <span style={{ fontSize: '0.73rem', color: 'var(--text-muted)' }}>🎓 {s.education || 'N/A'}</span>
                        </div>
                    </div>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', alignSelf: 'center' }}>{isExpanded ? '▲' : '▼'}</span>
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 10 }}>
                    {(s.skills || []).slice(0, isExpanded ? 999 : 8).map((sk, i) => (
                        <span key={i} className="skill-tag matched" style={{ fontSize: '0.68rem' }}>{sk}</span>
                    ))}
                    {!isExpanded && (s.skills || []).length > 8 && (
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', padding: '4px 8px' }}>
                            +{s.skills.length - 8} more
                        </span>
                    )}
                </div>

                {isExpanded && (
                    <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: 1.65, marginBottom: 10 }}>
                            {s.summary_text}
                        </p>
                        {(s.key_strengths || []).length > 0 && (
                            <>
                                <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 6 }}>
                                    Key Strengths
                                </div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                                    {s.key_strengths.map((st, i) => (
                                        <span key={i} style={{
                                            padding: '3px 9px', borderRadius: 20,
                                            fontSize: '0.7rem',
                                            background: 'rgba(108,99,255,0.12)',
                                            color: 'var(--accent-primary)',
                                        }}>{st}</span>
                                    ))}
                                </div>
                            </>
                        )}
                    </div>
                )}
            </div>
        )
    }

    // ── Main render ───────────────────────────────────────────────────────────
    return (
        <div>
            {/* ── Page Header ── */}
            <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h1>Base Resumes</h1>
                    <p>Manage templates · Generate AI summaries · Test JD matching with Gemini</p>
                </div>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    <button
                        id="btn-generate-summaries"
                        className={`btn btn-teal ${generating ? 'disabled' : ''}`}
                        onClick={handleGenerateSummaries}
                        disabled={generating}
                        title="Use Gemini AI to summarise all resumes and save to S3"
                    >
                        {generating
                            ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Generating…</>
                            : <>✨ Generate Summaries</>}
                    </button>
                    <label
                        id="btn-upload-resume"
                        className={`btn btn-primary ${uploading ? 'disabled' : ''}`}
                        style={{ cursor: uploading ? 'not-allowed' : 'pointer' }}
                    >
                        {uploading ? '⏳ Uploading…' : '📤 Upload Resume'}
                        <input type="file" style={{ display: 'none' }}
                            onChange={handleUpload} disabled={uploading} accept=".pdf,.docx,.txt" />
                    </label>
                </div>
            </div>

            {/* ── Tab Bar ── */}
            <div className="filters-bar" style={{ marginBottom: 24 }}>
                {[
                    { key: 'resumes', label: `📂 Files (${resumes.length})` },
                    { key: 'summaries', label: `🧠 AI Summaries (${summaries.length})` },
                    { key: 'test', label: `🔬 Test JD Match${matchResults.length ? ` · ${matchResults.length} results` : ''}` },
                ].map(t => (
                    <button
                        key={t.key}
                        id={`tab-${t.key}`}
                        className={`filter-chip ${activeTab === t.key ? 'active' : ''}`}
                        onClick={() => setActiveTab(t.key)}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {/* ══════ TAB: FILES ══════ */}
            {activeTab === 'resumes' && (
                loadingResumes
                    ? <div className="loading"><div className="spinner" /> Loading resumes…</div>
                    : <div className="card">
                        <div className="card-header">
                            <span className="card-title">Resume Files</span>
                            <span style={{ background: 'var(--accent-glow)', color: 'var(--accent-primary)', padding: '2px 10px', borderRadius: 12, fontSize: '0.75rem', fontWeight: 600 }}>
                                {resumes.length} total
                            </span>
                        </div>
                        {resumes.length === 0
                            ? <div className="empty-state">
                                <div className="empty-icon">📁</div>
                                <h3>No resumes yet</h3>
                                <p>Upload a PDF, DOCX, or TXT file above.</p>
                            </div>
                            : <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Filename</th>
                                        <th>S3 Path</th>
                                        <th style={{ textAlign: 'right' }}>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {resumes.map((r, i) => (
                                        <tr key={i}>
                                            <td style={{ fontWeight: 600 }}>{r.filename}</td>
                                            <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--text-muted)' }}>{r.s3_key}</td>
                                            <td style={{ textAlign: 'right' }}>
                                                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                                                    <a href={r.url} target="_blank" rel="noopener noreferrer"
                                                        className="btn btn-secondary"
                                                        style={{ padding: '5px 12px', fontSize: '0.75rem', textDecoration: 'none' }}>
                                                        View
                                                    </a>
                                                    <button className="btn btn-danger"
                                                        style={{ padding: '5px 12px', fontSize: '0.75rem' }}
                                                        disabled={deletingKey === r.s3_key}
                                                        onClick={() => handleDelete(r.s3_key)}>
                                                        {deletingKey === r.s3_key ? '…' : 'Delete'}
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        }

                        {resumes.length > 0 && summaries.length === 0 && (
                            <div style={{
                                marginTop: 20, padding: '14px 16px',
                                background: 'var(--accent-teal-dim)',
                                border: '1px solid rgba(100,255,218,0.2)',
                                borderRadius: 'var(--radius-sm)',
                                display: 'flex', alignItems: 'center', gap: 12,
                            }}>
                                <span style={{ fontSize: '1.2rem' }}>💡</span>
                                <div style={{ flex: 1 }}>
                                    <strong style={{ color: 'var(--accent-teal)' }}>Ready to generate summaries?</strong>
                                    <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                        Generate them once — they're stored in S3 and reused for all future job matching.
                                    </p>
                                </div>
                                <button className="btn btn-teal" style={{ padding: '7px 14px', fontSize: '0.78rem', flexShrink: 0 }}
                                    onClick={handleGenerateSummaries} disabled={generating}>
                                    ✨ Generate Now
                                </button>
                            </div>
                        )}
                    </div>
            )}

            {/* ══════ TAB: SUMMARIES ══════ */}
            {activeTab === 'summaries' && (
                loadingSummaries
                    ? <div className="loading"><div className="spinner" /> Loading summaries…</div>
                    : summaries.length === 0
                        ? <div className="card">
                            <div className="empty-state">
                                <div className="empty-icon">🧠</div>
                                <h3>No summaries generated yet</h3>
                                <p>Click <strong>Generate Summaries</strong> to let Gemini analyse your resumes.</p>
                                <button className="btn btn-teal" style={{ marginTop: 16 }}
                                    onClick={handleGenerateSummaries} disabled={generating}>
                                    {generating ? '⏳ Generating…' : '✨ Generate Now'}
                                </button>
                            </div>
                        </div>
                        : <div>
                            <div style={{
                                display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16,
                                padding: '10px 16px',
                                background: 'var(--bg-card)', border: '1px solid var(--border)',
                                borderRadius: 'var(--radius-sm)',
                            }}>
                                <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', flex: 1 }}>
                                    <strong style={{ color: 'var(--text-primary)' }}>{summaries.length}</strong> AI summaries stored in S3 · Click a card to expand details
                                </span>
                                <button className="btn btn-secondary" style={{ padding: '5px 12px', fontSize: '0.75rem' }}
                                    onClick={handleGenerateSummaries} disabled={generating}>
                                    {generating ? '⏳…' : '🔄 Regenerate'}
                                </button>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                {summaries.map((s, i) => <SummaryCard key={i} s={s} />)}
                            </div>
                        </div>
            )}

            {/* ══════ TAB: TEST JD MATCH ══════ */}
            {activeTab === 'test' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: 24, alignItems: 'start' }}>

                    {/* Left — Input */}
                    <div className="card">
                        <div className="card-header" style={{ marginBottom: 20 }}>
                            <span className="card-title">📋 Job Description</span>
                            {summaries.length > 0 && (
                                <span style={{ fontSize: '0.75rem', color: 'var(--accent-teal)' }}>
                                    {summaries.length} summaries loaded
                                </span>
                            )}
                        </div>

                        <div className="form-group">
                            <label className="form-label">Job Title (optional)</label>
                            <input id="jd-title-input" className="form-input"
                                placeholder="e.g. Senior Backend Engineer"
                                value={jobTitle} onChange={e => setJobTitle(e.target.value)} />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Company (optional)</label>
                            <input id="jd-company-input" className="form-input"
                                placeholder="e.g. Acme Corp"
                                value={company} onChange={e => setCompany(e.target.value)} />
                        </div>

                        <div className="form-group" style={{ marginBottom: 0 }}>
                            <label className="form-label">Job Description Text *</label>
                            <textarea
                                id="jd-test-input"
                                className="form-textarea"
                                style={{ minHeight: 240, fontSize: '0.84rem' }}
                                placeholder="Paste the full job description here…"
                                value={jdInput}
                                onChange={e => setJdInput(e.target.value)}
                            />
                        </div>

                        <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                            <button
                                id="btn-match-jd"
                                className={`btn btn-primary ${matching ? 'disabled' : ''}`}
                                style={{ flex: 1 }}
                                onClick={handleMatch}
                                disabled={matching || summaries.length === 0}
                            >
                                {matching
                                    ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Scoring with Gemini…</>
                                    : summaries.length === 0
                                        ? '⚠️ Generate summaries first'
                                        : '🤖 Match with Gemini AI'}
                            </button>
                            {matchResults.length > 0 && (
                                <button className="btn btn-secondary"
                                    onClick={() => { setMatchResults([]); setJdInput(''); setJobTitle(''); setCompany('') }}>
                                    Clear
                                </button>
                            )}
                        </div>

                        {summaries.length === 0 && (
                            <div style={{
                                marginTop: 12, padding: '10px 12px',
                                background: 'rgba(239,71,111,0.08)',
                                border: '1px solid rgba(239,71,111,0.2)',
                                borderRadius: 'var(--radius-sm)',
                                fontSize: '0.78rem', color: 'var(--status-error)',
                            }}>
                                ⚠️ No summaries found. Go to <strong>AI Summaries</strong> tab and click Generate first.
                            </div>
                        )}
                    </div>

                    {/* Right — Results */}
                    <div>
                        {matchResults.length === 0
                            ? <div className="card">
                                <div className="empty-state">
                                    <div className="empty-icon" style={{ fontSize: '2.5rem' }}>📊</div>
                                    <h3>Awaiting Match</h3>
                                    <p>Fill in the JD form and click <em>"Match with Gemini AI"</em></p>
                                </div>
                            </div>
                            : <div>
                                {/* Best match banner */}
                                <div style={{
                                    marginBottom: 16, padding: '12px 18px',
                                    background: 'linear-gradient(135deg,rgba(108,99,255,0.12),rgba(100,255,218,0.06))',
                                    border: '1px solid rgba(108,99,255,0.3)',
                                    borderRadius: 'var(--radius)',
                                    display: 'flex', alignItems: 'center', gap: 10,
                                }}>
                                    <span style={{ fontSize: '1.5rem' }}>🏆</span>
                                    <div>
                                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Best Match</div>
                                        <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.95rem' }}>
                                            {matchResults[0]?.resume_name}
                                            <span style={{ marginLeft: 10, color: scoreColor(matchResults[0]?.overall_score), fontWeight: 700 }}>
                                                {matchResults[0]?.overall_score}%
                                            </span>
                                        </div>
                                    </div>
                                    <div style={{ flex: 1 }} />
                                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                        {matchResults.length} resume{matchResults.length !== 1 ? 's' : ''} scored
                                    </span>
                                </div>

                                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                    {matchResults.map((r, i) => (
                                        <MatchResultCard key={i} r={r} rank={i} />
                                    ))}
                                </div>
                            </div>
                        }
                    </div>
                </div>
            )}

            {/* ── Toast ── */}
            {toast && (
                <div className={`toast ${toast.type === 'info' ? '' : toast.type}`}
                    style={toast.type === 'info' ? {
                        background: 'rgba(108,99,255,0.15)',
                        color: 'var(--accent-primary)',
                        border: '1px solid rgba(108,99,255,0.3)',
                        position: 'fixed', bottom: 24, right: 24,
                        padding: '14px 20px', borderRadius: 'var(--radius-sm)',
                        fontSize: '0.85rem', fontWeight: 500, zIndex: 1000,
                        animation: 'slideIn 0.3s ease-out',
                        boxShadow: 'var(--shadow-lg)',
                    } : {}}>
                    {toast.message}
                </div>
            )}
        </div>
    )
}
