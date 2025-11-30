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
    gpt: [],
    search_queries: [],
    serpapi_collections: []
};

/**
 * Fetch data from all API endpoints
 */
async function fetchAllData() {
    try {
        updateStatus('Fetching data...');

        const [newsResponse, claudeResponse, gptResponse, queriesResponse, serpapiResponse] = await Promise.all([
            fetch(`${API_BASE_URL}/api/data/news`),
            fetch(`${API_BASE_URL}/api/data/claude`),
            fetch(`${API_BASE_URL}/api/data/gpt`),
            fetch(`${API_BASE_URL}/api/data/search_queries`),
            fetch(`${API_BASE_URL}/api/data/collections?type=serpapi`)
        ]);

        const newsData = await newsResponse.json();
        const claudeData = await claudeResponse.json();
        const gptData = await gptResponse.json();
        const queriesData = await queriesResponse.json();
        const serpapiData = await serpapiResponse.json();

        if (newsData.status === 'success') {
            allData.news = newsData.data;
        }

        if (claudeData.status === 'success') {
            allData.claude = claudeData.data;
        }

        if (gptData.status === 'success') {
            allData.gpt = gptData.data;
        }

        if (queriesData.status === 'success') {
            allData.search_queries = queriesData.data;
        }

        if (serpapiData.status === 'success') {
            allData.serpapi_collections = serpapiData.data;
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
 * Create INPUT ANALYSIS panel for Deep Dive (shows parent analysis)
 */
function createInputAnalysisPanel(claudeAnalyses, jobName) {
    const panel = document.createElement('div');
    panel.className = 'panel input-analysis';

    const header = document.createElement('div');
    header.className = 'panel-header';

    const typeLabel = document.createElement('span');
    typeLabel.className = 'panel-type';
    typeLabel.textContent = 'INPUT ANALYSIS';

    const timestamp = document.createElement('span');
    timestamp.className = 'panel-timestamp';

    header.appendChild(typeLabel);
    header.appendChild(timestamp);

    const content = document.createElement('div');
    content.className = 'panel-content';

    if (claudeAnalyses.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'empty-message';
        empty.textContent = 'No input analysis available';
        content.appendChild(empty);
    } else {
        const latest = claudeAnalyses[0];
        timestamp.textContent = formatTimestamp(latest.created_at);

        const analysis = document.createElement('div');
        analysis.className = 'analysis-text';
        analysis.textContent = latest.analysis_text || 'No analysis available';

        content.appendChild(analysis);
    }

    panel.appendChild(header);
    panel.appendChild(content);

    return panel;
}

/**
 * Create SEARCH QUERIES panel for Deep Dive
 */
function createSearchQueriesPanel(searchQueries, jobName) {
    const panel = document.createElement('div');
    panel.className = 'panel search-queries';

    const header = document.createElement('div');
    header.className = 'panel-header';

    const typeLabel = document.createElement('span');
    typeLabel.className = 'panel-type';
    typeLabel.textContent = 'SEARCH QUERIES';

    const count = document.createElement('span');
    count.className = 'panel-count';

    header.appendChild(typeLabel);
    header.appendChild(count);

    const content = document.createElement('div');
    content.className = 'panel-content';

    if (searchQueries.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'empty-message';
        empty.textContent = 'No search queries generated yet';
        content.appendChild(empty);
    } else {
        const latest = searchQueries[0];
        const queries = latest.queries || [];
        count.textContent = `${queries.length} queries`;

        // Justification
        if (latest.justification) {
            const justDiv = document.createElement('div');
            justDiv.className = 'query-justification';
            justDiv.innerHTML = `<strong>Strategy:</strong> ${latest.justification}`;
            content.appendChild(justDiv);
        }

        // Queries list
        const list = document.createElement('div');
        list.className = 'queries-list';

        queries.forEach((q, idx) => {
            const item = document.createElement('div');
            item.className = 'query-item';

            const queryText = document.createElement('h4');
            queryText.className = 'query-text';
            queryText.textContent = `${idx + 1}. ${q.query}`;

            const reason = document.createElement('p');
            reason.className = 'query-reason';
            reason.textContent = q.reason;

            item.appendChild(queryText);
            item.appendChild(reason);
            list.appendChild(item);
        });

        content.appendChild(list);
    }

    panel.appendChild(header);
    panel.appendChild(content);

    return panel;
}

/**
 * Create SEARCH RESULTS panel for Deep Dive
 */
function createSearchResultsPanel(serpapiCollections, jobName) {
    const panel = document.createElement('div');
    panel.className = 'panel search-results';

    const header = document.createElement('div');
    header.className = 'panel-header';

    const typeLabel = document.createElement('span');
    typeLabel.className = 'panel-type';
    typeLabel.textContent = 'SEARCH RESULTS';

    const count = document.createElement('span');
    count.className = 'panel-count';
    count.textContent = `${serpapiCollections.length} results`;

    header.appendChild(typeLabel);
    header.appendChild(count);

    const content = document.createElement('div');
    content.className = 'panel-content';

    if (serpapiCollections.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'empty-message';
        empty.textContent = 'No search results yet';
        content.appendChild(empty);
    } else {
        const list = document.createElement('div');
        list.className = 'results-list';

        serpapiCollections.forEach(collection => {
            const data = collection.data || {};
            const item = document.createElement('div');
            item.className = 'result-item';

            const title = document.createElement('h4');
            title.className = 'result-title';
            title.textContent = data.title || 'Untitled';

            const snippet = document.createElement('p');
            snippet.className = 'result-snippet';
            snippet.textContent = data.snippet || '';

            const link = document.createElement('a');
            link.className = 'result-link';
            link.href = data.url || '#';
            link.textContent = data.displayed_link || data.url || '';
            link.target = '_blank';

            item.appendChild(title);
            item.appendChild(snippet);
            item.appendChild(link);
            list.appendChild(item);
        });

        content.appendChild(list);
    }

    panel.appendChild(header);
    panel.appendChild(content);

    return panel;
}

/**
 * Create tabbed layout: Each job gets its own tab with 3-column grid
 */
function createGrid() {
    const tabNav = document.getElementById('tabNav');
    const tabContent = document.getElementById('tabContent');

    // Defensive null checks for cached page compatibility
    if (!tabNav || !tabContent) {
        console.error('Missing tabNav or tabContent elements - please hard refresh (Ctrl+F5)');
        alert('⚠️ Page cache issue detected.\n\nPlease hard refresh:\n• Windows: Ctrl+F5\n• Mac: Cmd+Shift+R');
        return;
    }

    tabNav.innerHTML = '';
    tabContent.innerHTML = '';

    // Check if we have any data
    const totalPanels = allData.news.length + allData.claude.length + allData.gpt.length;

    if (totalPanels === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        emptyState.innerHTML = `
            <h2>⚠ NO DATA AVAILABLE</h2>
            <p>Jobs haven't executed yet or no data has been collected.</p>
            <p>Try refreshing in a few moments.</p>
        `;
        tabContent.appendChild(emptyState);
        tabContent.style.display = 'block';
        return;
    }

    // Group all data by job_id
    const jobGroups = groupDataByJob();
    const jobIds = Object.keys(jobGroups);

    // Create tabs and panels for each job
    jobIds.forEach((jobId, index) => {
        const jobData = jobGroups[jobId];

        // Create tab button
        const tabBtn = document.createElement('button');
        tabBtn.className = 'tab-btn' + (index === 0 ? ' active' : '');
        tabBtn.textContent = jobData.jobName;
        tabBtn.dataset.jobId = jobId;
        tabBtn.addEventListener('click', () => switchTab(jobId));
        tabNav.appendChild(tabBtn);

        // Create tab panel
        const tabPanel = document.createElement('div');
        tabPanel.className = 'tab-panel' + (index === 0 ? ' active' : '');
        tabPanel.dataset.jobId = jobId;

        // Create 3-column grid for this job
        const panelGrid = document.createElement('div');
        panelGrid.className = 'panel-grid';

        // Check if this is a Deep Dive job
        if (jobData.jobName === 'Deep Dive') {
            // Special layout for Deep Dive: Input Analysis, Search Queries, Search Results
            const inputPanel = createInputAnalysisPanel(jobData.claude, jobData.jobName);
            panelGrid.appendChild(inputPanel);

            const queriesPanel = createSearchQueriesPanel(jobData.search_queries, jobData.jobName);
            panelGrid.appendChild(queriesPanel);

            const resultsPanel = createSearchResultsPanel(jobData.serpapi_collections, jobData.jobName);
            panelGrid.appendChild(resultsPanel);
        } else {
            // Standard layout for other jobs: News, Claude, GPT
            const newsPanel = createNewsListPanel(jobData.news, jobData.jobName);
            panelGrid.appendChild(newsPanel);

            const claudePanel = createAnalysisPanel('claude', jobData.claude);
            panelGrid.appendChild(claudePanel);

            const gptPanel = createAnalysisPanel('gpt', jobData.gpt);
            panelGrid.appendChild(gptPanel);
        }

        tabPanel.appendChild(panelGrid);
        tabContent.appendChild(tabPanel);
    });

    tabContent.style.display = 'block';
}

/**
 * Switch between tabs
 */
function switchTab(jobId) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        if (btn.dataset.jobId === jobId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Update tab panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        if (panel.dataset.jobId === jobId) {
            panel.classList.add('active');
        } else {
            panel.classList.remove('active');
        }
    });
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
                gpt: [],
                search_queries: [],
                serpapi_collections: []
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
                gpt: [],
                search_queries: [],
                serpapi_collections: []
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
                gpt: [],
                search_queries: [],
                serpapi_collections: []
            };
        }
        groups[jobId].gpt.push(item);
    });

    // Group search queries by job_id
    allData.search_queries.forEach(item => {
        const jobId = item.job_id;
        if (!groups[jobId]) {
            groups[jobId] = {
                jobName: item.job_name || `Job ${jobId}`,
                news: [],
                claude: [],
                gpt: [],
                search_queries: [],
                serpapi_collections: []
            };
        }
        groups[jobId].search_queries.push(item);
    });

    // Group SerpAPI collections by job_id
    allData.serpapi_collections.forEach(item => {
        const jobId = item.job_id;
        if (!groups[jobId]) {
            groups[jobId] = {
                jobName: item.job_name || `Job ${jobId}`,
                news: [],
                claude: [],
                gpt: [],
                search_queries: [],
                serpapi_collections: []
            };
        }
        groups[jobId].serpapi_collections.push(item);
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
    if (!statusEl) {
        console.warn('Status element not found - page may need hard refresh');
        return;
    }
    statusEl.textContent = message.toUpperCase();
}

/**
 * Update last update timestamp
 */
function updateLastUpdateTime() {
    const lastUpdateEl = document.getElementById('lastUpdate');
    if (!lastUpdateEl) {
        console.warn('Last update element not found - page may need hard refresh');
        return;
    }
    lastUpdateEl.textContent = new Date().toLocaleTimeString();
}

/**
 * Show/hide loading spinner
 */
function setLoading(isLoading) {
    const loadingEl = document.getElementById('loading');
    const tabContent = document.getElementById('tabContent');

    // Defensive null checks for cached page compatibility
    if (!loadingEl || !tabContent) {
        console.warn('Missing DOM elements - please hard refresh (Ctrl+F5)');
        return;
    }

    if (isLoading) {
        loadingEl.style.display = 'block';
        tabContent.style.display = 'none';
    } else {
        loadingEl.style.display = 'none';
        tabContent.style.display = 'block';
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
        const container = document.getElementById('tabContent');
        container.innerHTML = `
            <div class="empty-state">
                <h2>⚠ ERROR LOADING DATA</h2>
                <p>Please check the API connection and try again.</p>
            </div>
        `;
        container.style.display = 'block';
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
