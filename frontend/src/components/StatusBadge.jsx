import React from 'react'

const STATUS_CONFIG = {
    'new': { label: 'New', className: 'new' },
    'resume-match-done': { label: 'Matched', className: 'resume-match-done' },
    'documents-ready': { label: 'Ready', className: 'documents-ready' },
    'error': { label: 'Error', className: 'error' },
}

export default function StatusBadge({ status }) {
    const config = STATUS_CONFIG[status] || { label: status, className: 'new' }
    return (
        <span className={`status-badge ${config.className}`}>
            <span className="status-dot" />
            {config.label}
        </span>
    )
}
