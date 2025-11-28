/**
 * Panel Populator - Creates 3xN grid and populates with data
 */

// Configuration
const API_BASE_URL = window.location.origin;
const PANELS_PER_ROW = 3;

// State management
let allData = {
    news: [],
    claude: [],
    gpt: []
};

/**
 * Fetch data from all API endpoints
 */
async function fetchAllData() {
    try {
        updateStatus('Fetching data...');

        const [newsResponse, claudeResponse, gptResponse] = await Promise.all([
            fetch(`${API_BASE_URL}/api/data/news`),
            fetch(`${API_BASE_URL}/api/data/claude`),
            fetch(`${API_BASE_URL}/api/data/gpt`)
        ]);

        const newsData = await newsResponse.json();
        const claudeData = await claudeResponse.json();
        const gptData = await gptResponse.json();

        if (newsData.status === 'success') {
            allData.news = newsData.data;
        }

        if (claudeData.status === 'success') {
            allData.claude = claudeData.data;
        }

        if (gptData.status === 'success') {
            allData.gpt = gptData.data;
        }

        updateStatus('Ready');
        return true;

    } catch (error) {
        console.error('Error fetching data:', error);
        updateStatus('Error fetching data');
        return false;
    }
}

/**
 * Create NEWS list panel showing articles for a specific job
 */
function createNewsListPanel(newsItems, jobName) {
    const panel = document.createElement('div');
    panel.className = 'panel news';

    const header = document.createElement('div');
    header.className = 'panel-header';

    const typeLabel = document.createElement('span');
    typeLabel.className = 'panel-type';
    typeLabel.textContent = 'NEWS';

    const count = document.createElement('span');
    count.className = 'panel-count';
    count.textContent = `${newsItems.length} articles`;

    header.appendChild(typeLabel);
    header.appendChild(count);

    const content = document.createElement('div');
    content.className = 'panel-content';

    if (newsItems.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'empty-message';
        empty.textContent = 'No news articles collected yet';
        content.appendChild(empty);
    } else {
        const list = document.createElement('div');
        list.className = 'news-list';

        newsItems.forEach(article => {
            const item = document.createElement('div');
            item.className = 'news-item';

            const title = document.createElement('h4');
            title.className = 'news-title';
            title.textContent = article.title || 'Untitled';

            const date = document.createElement('p');
            date.className = 'news-date';
            date.textContent = formatTimestamp(article.publish_date);

            item.appendChild(title);
            item.appendChild(date);
            list.appendChild(item);
        });

        content.appendChild(list);
    }

    panel.appendChild(header);
    panel.appendChild(content);

    return panel;
}

/**
 * Create analysis panel (Claude or GPT)
 */
function createAnalysisPanel(type, data) {
    const panel = document.createElement('div');
    panel.className = `panel ${type}`;

    const header = document.createElement('div');
    header.className = 'panel-header';

    const typeLabel = document.createElement('span');
    typeLabel.className = 'panel-type';
    typeLabel.textContent = type === 'claude' ? 'CLAUDE ANALYSIS' : 'GPT ANALYSIS';

    const timestamp = document.createElement('span');
    timestamp.className = 'panel-timestamp';

    const content = document.createElement('div');
    content.className = 'panel-content';

    if (data.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'empty-message';
        empty.textContent = `No ${type} analysis available yet`;
        content.appendChild(empty);
    } else {
        // Show the most recent analysis
        const latest = data[0];
        timestamp.textContent = formatTimestamp(latest.created_at);

        const analysis = document.createElement('div');
        analysis.className = 'analysis-text';
        analysis.textContent = latest.analysis_text || 'No analysis available';

        content.appendChild(analysis);
    }

    header.appendChild(typeLabel);
    header.appendChild(timestamp);

    panel.appendChild(header);
    panel.appendChild(content);

    return panel;
}

/**
 * Create job-grouped layout: Each job gets its own row of NEWS | CLAUDE | GPT
 */
function createGrid() {
    const container = document.getElementById('gridContainer');
    container.innerHTML = '';

    // Check if we have any data
    const totalPanels = allData.news.length + allData.claude.length + allData.gpt.length;

    if (totalPanels === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        emptyState.innerHTML = `
            <h2>No data available</h2>
            <p>Jobs haven't run yet or no data has been collected.</p>
            <p>Try refreshing in a few moments.</p>
        `;
        container.appendChild(emptyState);
        return;
    }

    // Group all data by job_id
    const jobGroups = groupDataByJob();

    // Create a row for each job
    for (const [jobId, jobData] of Object.entries(jobGroups)) {
        // Job header
        const jobHeader = document.createElement('div');
        jobHeader.className = 'job-header';
        jobHeader.innerHTML = `<h2>${jobData.jobName}</h2>`;
        container.appendChild(jobHeader);

        // Create NEWS panel for this job
        const newsPanel = createNewsListPanel(jobData.news, jobData.jobName);
        container.appendChild(newsPanel);

        // Create CLAUDE analysis panel for this job
        const claudePanel = createAnalysisPanel('claude', jobData.claude);
        container.appendChild(claudePanel);

        // Create GPT analysis panel for this job
        const gptPanel = createAnalysisPanel('gpt', jobData.gpt);
        container.appendChild(gptPanel);
    }
}

/**
 * Group all data by job_id
 */
function groupDataByJob() {
    const groups = {};

    // Group news by job_id
    allData.news.forEach(item => {
        const jobId = item.job_id;
        if (!groups[jobId]) {
            groups[jobId] = {
                jobName: item.job_name || `Job ${jobId}`,
                news: [],
                claude: [],
                gpt: []
            };
        }
        groups[jobId].news.push(item);
    });

    // Group Claude analyses by job_id
    allData.claude.forEach(item => {
        const jobId = item.job_id;
        if (!groups[jobId]) {
            groups[jobId] = {
                jobName: item.job_name || `Job ${jobId}`,
                news: [],
                claude: [],
                gpt: []
            };
        }
        groups[jobId].claude.push(item);
    });

    // Group GPT analyses by job_id
    allData.gpt.forEach(item => {
        const jobId = item.job_id;
        if (!groups[jobId]) {
            groups[jobId] = {
                jobName: item.job_name || `Job ${jobId}`,
                news: [],
                claude: [],
                gpt: []
            };
        }
        groups[jobId].gpt.push(item);
    });

    return groups;
}

/**
 * Shuffle array using Fisher-Yates algorithm
 */
function shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Unknown';

    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

/**
 * Update status text
 */
function updateStatus(message) {
    const statusEl = document.getElementById('status');
    if (statusEl) {
        statusEl.textContent = message;
    }
}

/**
 * Update last update timestamp
 */
function updateLastUpdateTime() {
    const lastUpdateEl = document.getElementById('lastUpdate');
    if (lastUpdateEl) {
        lastUpdateEl.textContent = new Date().toLocaleTimeString();
    }
}

/**
 * Show/hide loading spinner
 */
function setLoading(isLoading) {
    const loadingEl = document.getElementById('loading');
    const gridEl = document.getElementById('gridContainer');

    if (isLoading) {
        loadingEl.style.display = 'block';
        gridEl.style.display = 'none';
    } else {
        loadingEl.style.display = 'none';
        gridEl.style.display = 'grid';
    }
}

/**
 * Load and display data
 */
async function loadAndDisplayData() {
    setLoading(true);

    const success = await fetchAllData();

    if (success) {
        createGrid();
        updateLastUpdateTime();
    } else {
        const container = document.getElementById('gridContainer');
        container.innerHTML = `
            <div class="empty-state">
                <h2>Error loading data</h2>
                <p>Please check the API connection and try again.</p>
            </div>
        `;
    }

    setLoading(false);
}

/**
 * Initialize the dashboard
 */
function init() {
    // Initial load
    loadAndDisplayData();

    // Set up refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadAndDisplayData();
        });
    }

    // Auto-refresh every 5 minutes
    setInterval(loadAndDisplayData, 5 * 60 * 1000);
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
