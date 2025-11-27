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
 * Create a panel element
 */
function createPanel(type, data) {
    const panel = document.createElement('div');
    panel.className = `panel ${type}`;

    const header = document.createElement('div');
    header.className = 'panel-header';

    const typeLabel = document.createElement('span');
    typeLabel.className = 'panel-type';
    typeLabel.textContent = type.toUpperCase();

    const timestamp = document.createElement('span');
    timestamp.className = 'panel-timestamp';

    const content = document.createElement('div');
    content.className = 'panel-content';

    // Build panel content based on type
    if (type === 'news') {
        timestamp.textContent = formatTimestamp(data.collected_at);

        const title = document.createElement('h3');
        title.textContent = data.title || 'No title';

        const summary = document.createElement('p');
        summary.className = 'summary';
        summary.textContent = data.summary || 'No summary available';

        const meta = document.createElement('div');
        meta.className = 'meta';

        if (data.publish_date) {
            const publishDate = document.createElement('p');
            publishDate.textContent = `Published: ${formatTimestamp(data.publish_date)}`;
            meta.appendChild(publishDate);
        }

        if (data.url) {
            const link = document.createElement('a');
            link.href = data.url;
            link.target = '_blank';
            link.textContent = 'Read full article →';
            meta.appendChild(link);
        }

        content.appendChild(title);
        content.appendChild(summary);
        content.appendChild(meta);

    } else if (type === 'claude') {
        timestamp.textContent = formatTimestamp(data.created_at);

        const title = document.createElement('h3');
        title.textContent = `Analysis: ${data.news_title || 'News Article'}`;

        const analysis = document.createElement('div');
        analysis.className = 'analysis';
        analysis.textContent = data.analysis_text || 'No analysis available';

        content.appendChild(title);
        content.appendChild(analysis);

    } else if (type === 'gpt') {
        timestamp.textContent = formatTimestamp(data.created_at);

        const title = document.createElement('h3');
        title.textContent = `Analysis: ${data.news_title || 'News Article'}`;

        const analysis = document.createElement('div');
        analysis.className = 'analysis';
        analysis.textContent = data.analysis_text || 'No analysis available';

        content.appendChild(title);
        content.appendChild(analysis);
    }

    header.appendChild(typeLabel);
    header.appendChild(timestamp);

    panel.appendChild(header);
    panel.appendChild(content);

    return panel;
}

/**
 * Create a 3xN grid with randomized panel order
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

    // Create array of all panels with their type
    const allPanels = [
        ...allData.news.map(item => ({ type: 'news', data: item })),
        ...allData.claude.map(item => ({ type: 'claude', data: item })),
        ...allData.gpt.map(item => ({ type: 'gpt', data: item }))
    ];

    // Shuffle panels randomly
    const shuffledPanels = shuffleArray(allPanels);

    // Calculate number of complete rows
    const numRows = Math.ceil(shuffledPanels.length / PANELS_PER_ROW);

    // Create rows with 3 panels each
    let panelIndex = 0;
    for (let row = 0; row < numRows; row++) {
        for (let col = 0; col < PANELS_PER_ROW && panelIndex < shuffledPanels.length; col++) {
            const panelData = shuffledPanels[panelIndex];
            const panel = createPanel(panelData.type, panelData.data);
            container.appendChild(panel);
            panelIndex++;
        }
    }
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
