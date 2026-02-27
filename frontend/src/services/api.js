/**
 * API service for communicating with the JobSys backend.
 *
 * Update API_BASE_URL after deploying the API Gateway.
 */

const API_BASE_URL = 'https://h4g134wudj.execute-api.ap-south-1.amazonaws.com/prod';

async function request(path, options = {}) {
    const url = `${API_BASE_URL}${path}`;
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    };

    const response = await fetch(url, config);
    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: response.statusText }));
        throw new Error(error.error || `API error: ${response.status}`);
    }
    return response.json();
}

// ── Jobs ─────────────────────────────────────────────────────────────────────

export async function fetchJobs(status = null) {
    const params = status ? `?status=${status}` : '';
    return request(`/jobs${params}`);
}

export async function fetchJob(jobId) {
    return request(`/jobs/${jobId}`);
}

export async function triggerScan(sourceUrls = null) {
    return request('/jobs/scan', {
        method: 'POST',
        body: JSON.stringify(sourceUrls ? { source_urls: sourceUrls } : {}),
    });
}

export async function regenerateDocuments(jobId) {
    return request(`/jobs/${jobId}/regenerate`, {
        method: 'POST',
    });
}

// ── Configuration ────────────────────────────────────────────────────────────

export async function fetchConfig() {
    return request('/config');
}

export async function updateConfig(configData) {
    return request('/config', {
        method: 'PUT',
        body: JSON.stringify(configData),
    });
}

// ── Dashboard ────────────────────────────────────────────────────────────────

export async function fetchDashboardStats() {
    return request('/dashboard/stats');
}

// ── Documents ────────────────────────────────────────────────────────────────

export async function getDocumentUrl(s3Key) {
    return request(`/documents/${encodeURIComponent(s3Key)}`);
}

// ── Resumes ──────────────────────────────────────────────────────────────────

export async function fetchResumes() {
    return request('/resumes');
}

export async function uploadResume(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = async () => {
            try {
                // Remove the data:application/...;base64, prefix
                const base64Content = reader.result.split(',')[1];
                const result = await request('/resumes', {
                    method: 'POST',
                    body: JSON.stringify({
                        filename: file.name,
                        content: base64Content,
                    }),
                });
                resolve(result);
            } catch (error) {
                reject(error);
            }
        };
        reader.onerror = error => reject(error);
    });
}

export async function deleteResume(s3Key) {
    return request(`/resumes?key=${encodeURIComponent(s3Key)}`, {
        method: 'DELETE',
    });
}

export async function fetchResumeSummaries() {
    return request('/resumes/summaries');
}

export async function generateResumeSummaries() {
    return request('/resumes/summarize', { method: 'POST' });
}

export async function matchResumesToJd(jdText, jobMeta = {}) {
    return request('/resumes/match', {
        method: 'POST',
        body: JSON.stringify({ jd_text: jdText, job_meta: jobMeta }),
    });
}
