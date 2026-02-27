import React, { useState } from 'react'
import Dashboard from './components/Dashboard'
import JobTable from './components/JobTable'
import JobDetail from './components/JobDetail'
import ConfigPage from './components/ConfigPage'
import ResumesPage from './components/ResumesPage'

const PAGES = {
    dashboard: { icon: '📊', label: 'Dashboard' },
    resumes: { icon: '📄', label: 'Resumes' },
    jobs: { icon: '💼', label: 'Jobs' },
    config: { icon: '⚙️', label: 'Configuration' },
}

export default function App() {
    const [page, setPage] = useState('dashboard')
    const [selectedJobId, setSelectedJobId] = useState(null)

    function navigate(target, data = null) {
        if (target === 'job-detail' && data) {
            setSelectedJobId(data)
            setPage('job-detail')
        } else {
            setSelectedJobId(null)
            setPage(target)
        }
    }

    function renderPage() {
        switch (page) {
            case 'dashboard':
                return <Dashboard onNavigate={navigate} />
            case 'jobs':
                return <JobTable onSelectJob={(id) => navigate('job-detail', id)} />
            case 'job-detail':
                return <JobDetail jobId={selectedJobId} onBack={() => navigate('jobs')} />
            case 'resumes':
                return <ResumesPage />
            case 'config':
                return <ConfigPage />
            default:
                return <Dashboard onNavigate={navigate} />
        }
    }

    return (
        <div className="app-layout">
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="sidebar-logo">
                    <div className="logo-icon">⚡</div>
                    <span>JobSys</span>
                </div>
                <nav className="sidebar-nav">
                    {Object.entries(PAGES).map(([key, { icon, label }]) => (
                        <button
                            key={key}
                            className={`nav-link ${page === key || (key === 'jobs' && page === 'job-detail') ? 'active' : ''}`}
                            onClick={() => navigate(key)}
                        >
                            <span className="nav-icon">{icon}</span>
                            <span>{label}</span>
                        </button>
                    ))}
                </nav>
            </aside>

            {/* Main Content */}
            <main className="main-content">
                {renderPage()}
            </main>
        </div>
    )
}
