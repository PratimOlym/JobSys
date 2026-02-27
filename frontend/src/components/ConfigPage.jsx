import React, { useState, useEffect } from 'react'
import { fetchConfig, updateConfig } from '../services/api'

export default function ConfigPage() {
    const [config, setConfig] = useState(null)
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [toast, setToast] = useState(null)

    // Form state
    const [urls, setUrls] = useState('')
    const [userName, setUserName] = useState('')
    const [email, setEmail] = useState('')
    const [phone, setPhone] = useState('')
    const [linkedin, setLinkedin] = useState('')

    useEffect(() => {
        loadConfig()
    }, [])

    async function loadConfig() {
        try {
            setLoading(true)
            const data = await fetchConfig()
            setConfig(data)

            // Populate form
            const sources = data.job_sources || {}
            setUrls((sources.urls || []).join('\n'))

            const profile = data.user_profile || {}
            setUserName(profile.name || '')
            setEmail(profile.email || '')
            setPhone(profile.phone || '')
            setLinkedin(profile.linkedin || '')
        } catch (err) {
            console.error('Failed to load config:', err)
        } finally {
            setLoading(false)
        }
    }

    async function handleSave() {
        try {
            setSaving(true)
            const urlList = urls.split('\n').map(u => u.trim()).filter(Boolean)

            await updateConfig({
                job_sources: { urls: urlList },
                user_profile: {
                    name: userName,
                    email: email,
                    phone: phone,
                    linkedin: linkedin,
                },
            })

            showToast('Configuration saved!', 'success')
        } catch (err) {
            showToast('Failed to save: ' + err.message, 'error')
        } finally {
            setSaving(false)
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
                Loading configuration...
            </div>
        )
    }

    return (
        <div>
            <div className="page-header">
                <h1>Configuration</h1>
                <p>Manage your job sources and profile settings</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                {/* Job Sources */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Job Source URLs</span>
                    </div>
                    <div className="form-group">
                        <label className="form-label">URLs (one per line)</label>
                        <textarea
                            className="form-textarea"
                            value={urls}
                            onChange={e => setUrls(e.target.value)}
                            placeholder={"https://example.com/careers\nhttps://jobs.company.com/listings"}
                            rows={8}
                        />
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: -12 }}>
                        Add job listing page URLs or direct job posting links. The scanner will
                        extract job details automatically.
                    </p>
                </div>

                {/* User Profile */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">User Profile</span>
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 16 }}>
                        Used in resume filenames and cover letter generation.
                    </p>

                    <div className="form-group">
                        <label className="form-label">Full Name</label>
                        <input
                            className="form-input"
                            value={userName}
                            onChange={e => setUserName(e.target.value)}
                            placeholder="Your Name"
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Email</label>
                        <input
                            className="form-input"
                            type="email"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            placeholder="you@email.com"
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Phone</label>
                        <input
                            className="form-input"
                            value={phone}
                            onChange={e => setPhone(e.target.value)}
                            placeholder="+91 98765 43210"
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">LinkedIn URL</label>
                        <input
                            className="form-input"
                            value={linkedin}
                            onChange={e => setLinkedin(e.target.value)}
                            placeholder="https://linkedin.com/in/yourprofile"
                        />
                    </div>
                </div>
            </div>

            <div style={{ marginTop: 24, display: 'flex', gap: 12 }}>
                <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                    {saving ? '⏳ Saving...' : '💾 Save Configuration'}
                </button>
                <button className="btn btn-secondary" onClick={loadConfig}>
                    ↻ Reset
                </button>
            </div>

            {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}
        </div>
    )
}
