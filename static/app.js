/**
 * HN GitHub Agents - Frontend Application
 * Handles trend search, repository analysis, and general chat functionality
 */

class TrendTracker {
    constructor() {
        this.apiBase = '';
        this.lastQuery = '';
        this.detectedRepos = [];
        this.availableFiles = [];
        this.fileAutocompleteVisible = false;
        this.mode = 'trends';
        
        this.initializeElements();
        this.bindEvents();
        this.checkStatus();
        this.setupMarkdown();
        this.loadAvailableFiles();
    }

    toggleMode() {
        this.mode = this.mode === 'trends' ? 'chat' : 'trends';
        if (this.mode === 'chat') {
            this.chatToggleBtn.innerHTML = '<i class="fas fa-chart-line"></i> Back to Trends';
            // subtle cue in main input
            this.searchInput.placeholder = 'Ask anything... Use @filename to include data files';
        } else {
            this.chatToggleBtn.innerHTML = '<i class="fas fa-comments"></i> Ask anything else?';
            this.searchInput.placeholder = 'What trends do you want to explore? Try @filename to include data files';
        }
    }

    displayChatResult(query, answerMarkdown) {
        // Title + meta
        this.resultsTitle.innerHTML = `<i class="fas fa-comments" style="color:#c084fc; margin-right:8px;"></i>General AI: "${this.escapeHtml(query)}"`;
        this.resultsMeta.innerHTML = '<span class="direct-answer-badge"><i class="fas fa-robot"></i> Direct answer</span>';
        // Clear grids and hide repos
        this.trendsGrid.innerHTML = '';
        this.reposGrid.innerHTML = '';
        this.reposContainer.style.display = 'none';
        // Summary header and content
        const summaryHeader = document.querySelector('#summaryContainer h3');
        if (summaryHeader) summaryHeader.innerHTML = '<i class="fas fa-brain"></i> General AI Assistant Analysis';
        const prettyText = this.prettifyAssistantText(answerMarkdown || '');
        this.summaryContent.innerHTML = this.renderMarkdown(prettyText);
        this.summaryContent.className = 'summary-content markdown-content';
        this.applySyntaxHighlighting(this.summaryContent);
        this.summaryContainer.style.display = 'block';
        this.summaryContainer.classList.add('chat-summary');
        // Reveal section
        this.resultsSection.style.display = 'block';
        this.resultsSection.classList.add('chat-mode');
        this.resultsSection.scrollIntoView({ behavior: 'smooth' });

        // Add a copy button next to export for convenience (chat-only)
        const metaWrap = document.querySelector('.results-meta');
        if (metaWrap && !document.getElementById('copyAnswerBtn')) {
            const copyBtn = document.createElement('button');
            copyBtn.id = 'copyAnswerBtn';
            copyBtn.className = 'copy-btn';
            copyBtn.title = 'Copy Answer';
            copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            copyBtn.addEventListener('click', async () => {
                try {
                    const plain = this.summaryContent.innerText || '';
                    await navigator.clipboard.writeText(plain);
                    copyBtn.classList.add('copied');
                    setTimeout(() => copyBtn.classList.remove('copied'), 1000);
                } catch (e) {
                    console.warn('Copy failed', e);
                }
            });
            metaWrap.appendChild(copyBtn);
        }
    }
    setupMarkdown() {
        // Configure marked.js for better markdown rendering
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                breaks: true,
                gfm: true,
                sanitize: false,
                smartLists: true,
                smartypants: true,
                headerIds: false,
                mangle: false
            });

            // Custom renderer for better formatting
            const renderer = new marked.Renderer();
            
            // Improve paragraph rendering with better spacing
            renderer.paragraph = function(text) {
                return '<p>' + text + '</p>\n';
            };
            
            // Improve list rendering
            renderer.list = function(body, ordered, start) {
                const type = ordered ? 'ol' : 'ul';
                const startatt = (ordered && start !== 1) ? (' start="' + start + '"') : '';
                return '<' + type + startatt + '>\n' + body + '</' + type + '>\n';
            };
            
            // Improve list item rendering
            renderer.listitem = function(text) {
                return '<li>' + text + '</li>\n';
            };

            marked.setOptions({ renderer: renderer });
        }
    }

    initializeElements() {
        // Search elements
        this.searchInput = document.getElementById('searchInput');
        this.searchBtn = document.getElementById('searchBtn');
        this.includeHN = document.getElementById('includeHN');
        this.includeBrave = document.getElementById('includeBrave');
        
        // Results elements
        this.resultsSection = document.getElementById('resultsSection');
        this.resultsTitle = document.getElementById('resultsTitle');
        this.resultsMeta = document.getElementById('resultsMeta');
        this.trendsGrid = document.getElementById('trendsGrid');
        this.summaryContainer = document.getElementById('summaryContainer');
        this.summaryContent = document.getElementById('summaryContent');
        this.reposContainer = document.getElementById('reposContainer');
        this.reposGrid = document.getElementById('reposGrid');
        this.analyzeReposBtn = document.getElementById('analyzeReposBtn');
        this.exportBtn = document.getElementById('exportBtn');
        // Show-more state
        this.trendsShownLimit = 6;
        this.showMoreBtn = null;
        
        // Chat elements
        this.chatToggleBtn = document.getElementById('chatToggleBtn');
        this.chatContainer = document.getElementById('chatContainer');
        this.chatSection = document.querySelector('.chat-section');
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.chatSendBtn = document.getElementById('chatSendBtn');
        
        // UI elements
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.errorModal = document.getElementById('errorModal');
        this.statusDot = document.getElementById('status-dot');
        this.statusText = document.getElementById('status-text');
        // Sidebar history elements
        this.sidebar = document.querySelector('.sidebar-inner');
        this.sidebarList = null;
        
        // Suggestion tags
        this.suggestionTags = document.querySelectorAll('.suggestion-tag');
    }

    bindEvents() {
        // Search functionality
        this.searchBtn.addEventListener('click', () => this.performSearch());
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.fileAutocompleteVisible) this.performSearch();
        });
        this.searchInput.addEventListener('input', (e) => this.handleInputChange(e));
        this.searchInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        
        // Suggestion tags
        this.suggestionTags.forEach(tag => {
            tag.addEventListener('click', () => {
                const query = tag.dataset.query;
                this.searchInput.value = query;
                this.performSearch();
            });
        });
        
        // Repository analysis
        this.analyzeReposBtn.addEventListener('click', () => this.analyzeRepositories());
        
        // Export functionality
        this.exportBtn.addEventListener('click', () => this.exportResults());
        
        // Repurpose chat button to switch mode and reuse the main input
        this.chatToggleBtn.addEventListener('click', () => this.toggleMode());
        
        // Error modal
        document.getElementById('closeErrorBtn').addEventListener('click', () => this.hideError());
        document.getElementById('retryBtn').addEventListener('click', () => {
            this.hideError();
            if (this.lastQuery) this.performSearch();
        });

        // Load history on start
        this.renderHistorySidebar();
    }

    async checkStatus() {
        try {
            const response = await fetch('/health');
            const data = await response.json();
            
            this.updateStatus(data.status, `System ${data.status}`);
            
            // Log MCP server status for debugging
            console.log('MCP Servers:', data.mcp_servers);
            console.log('Agents:', data.agents_status);
            
        } catch (error) {
            console.error('Status check failed:', error);
            this.updateStatus('error', 'Connection failed');
        }
    }

    updateStatus(status, text) {
        this.statusDot.className = `status-dot ${status}`;
        this.statusText.textContent = text;
    }

    async performSearch() {
        const query = this.searchInput.value.trim();
        if (!query) {
            this.showError('Please enter a search query');
            return;
        }

        this.lastQuery = query;
        this.showLoading(this.mode === 'chat' ? 'Thinking...' : 'Analyzing trends...');
        
        try {
            // Use unified assistant endpoint that classifies and routes
            const response = await fetch('/api/v1/assistant', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    input: query,
                    limit: 15,
                    include_hn: this.includeHN.checked,
                    include_brave: this.includeBrave.checked
                })
            });
            if (!response.ok) throw new Error(`Assistant failed: ${response.status} ${response.statusText}`);
            const routed = await response.json();
            if (routed.route === 'chat') {
                const payload = routed.data || {};
                this.displayChatResult(query, payload.response || '');
                await this.renderHistorySidebar();
            } else {
                const payload = routed.data || {};
                this.displayResults(payload);
                await this.renderHistorySidebar();
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showError(`Search failed: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    async renderHistorySidebar() {
        // Ensure list container exists and remove placeholder once
        if (!this.sidebarList) {
            const placeholder = this.sidebar.querySelector('.sidebar-placeholder');
            if (placeholder) placeholder.remove();
            this.sidebarList = document.createElement('div');
            this.sidebarList.className = 'history-list';
            this.sidebar.appendChild(this.sidebarList);
        }

        try {
            const res = await fetch(`/api/v1/history?t=${Date.now()}`);
            if (!res.ok) {
                this.sidebarList.innerHTML = '<div class="history-time">Unable to load history.</div>';
                return;
            }
            const data = await res.json();
            const items = (data.items || []);
            if (items.length === 0) {
                this.sidebarList.innerHTML = '<div class="history-time">No history yet. Run an analysis or ask a question.</div>';
                return;
            }
            this.sidebarList.innerHTML = items.map(item => `
                <button class="history-item" data-id="${item.id}" data-type="${item.type}">
                    <div class="history-title">${this.escapeHtml(item.title)}</div>
                    <div class="history-time">${new Date(item.timestamp).toLocaleString()}</div>
                </button>
            `).join('');
            // Bind clicks
            this.sidebarList.querySelectorAll('.history-item').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id = btn.getAttribute('data-id');
                    const type = btn.getAttribute('data-type');
                    const r = await fetch(`/api/v1/history/${id}`);
                    if (!r.ok) return;
                    const payload = await r.json();
                    if (type === 'chat') {
                        const answer = (payload.data && payload.data.response) || (payload.data && payload.data.data && payload.data.data.response) || '';
                        const input = payload.item.input || '';
                        this.displayChatResult(input, answer);
                    } else {
                        this.displayResults(payload.data);
                    }
                });
            });
        } catch (e) {
            console.warn('Failed to load history', e);
            this.sidebarList.innerHTML = '<div class="history-time">Unable to load history.</div>';
        }
    }

    displayResults(data) {
        // Clean and format the query for beautiful display
        this.resultsSection.classList.remove('chat-mode');
        this.summaryContainer.classList.remove('chat-summary');
        if (this.showMoreBtn) {
            this.showMoreBtn.remove();
            this.showMoreBtn = null;
        }
        const cleanQuery = this.formatQueryForDisplay(data.query);
        
        // Update results header with beautiful formatting
        this.resultsTitle.innerHTML = cleanQuery.title;
        this.resultsMeta.innerHTML = cleanQuery.meta + ` • Found ${data.total_items} trends from ${data.sources.join(', ')}`;
        
        // Clear previous results
        this.trendsGrid.innerHTML = '';
        this.reposGrid.innerHTML = '';
        
        // Display trends (collapsed: first 6 + 2 preview placeholders)
        if (data.trends && data.trends.length > 0) {
            this.renderCollapsedTrends(data.trends);
        } else {
            this.trendsGrid.innerHTML = '<div class="no-results">No trends found for your query. Try adjusting your search terms.</div>';
        }
        
        // Display AI summary with markdown rendering
        if (data.summary) {
            this.summaryContent.innerHTML = this.renderMarkdown(data.summary);
            this.summaryContent.className = 'summary-content markdown-content';
            this.applySyntaxHighlighting(this.summaryContent);
            this.summaryContainer.style.display = 'block';
        } else {
            this.summaryContainer.style.display = 'none';
        }
        
        // Display detected repositories
        if (data.detected_repositories && data.detected_repositories.length > 0) {
            this.detectedRepos = data.detected_repositories;
            this.displayDetectedRepos(data.detected_repositories);
            this.reposContainer.style.display = 'block';
        } else {
            this.reposContainer.style.display = 'none';
        }
        
        // Show results section
        this.resultsSection.style.display = 'block';
        this.resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    addShowMoreToggle(allTrends) {
        if (this.showMoreBtn) {
            this.showMoreBtn.remove();
            this.showMoreBtn = null;
        }
        const wrap = document.createElement('div');
        wrap.className = 'show-more-wrap';
        const btn = document.createElement('button');
        btn.className = 'show-more-btn';
        btn.innerHTML = '<i class="fas fa-chevron-down"></i><span> Show all ' + allTrends.length + '</span>';
        let expanded = false;
        btn.addEventListener('click', () => {
            if (!expanded) {
                // Expand to show all (remove previews and rerender all)
                this.trendsGrid.innerHTML = '';
                allTrends.forEach(trend => this.trendsGrid.appendChild(this.createTrendCard(trend)));
                btn.innerHTML = '<i class="fas fa-chevron-up"></i><span> Show less</span>';
                expanded = true;
            } else {
                // Collapse back to 6 + previews
                this.renderCollapsedTrends(allTrends);
                btn.innerHTML = '<i class="fas fa-chevron-down"></i><span> Show all ' + allTrends.length + '</span>';
                expanded = false;
            }
        });
        wrap.appendChild(btn);
        const trendsContainer = this.trendsGrid.parentElement;
        trendsContainer.appendChild(wrap);
        this.showMoreBtn = btn;
    }

    renderCollapsedTrends(allTrends) {
        this.trendsGrid.innerHTML = '';
        const initial = allTrends.slice(0, this.trendsShownLimit);
        initial.forEach(trend => this.trendsGrid.appendChild(this.createTrendCard(trend)));
        const previews = allTrends.slice(this.trendsShownLimit, this.trendsShownLimit + 2);
        previews.forEach(trend => {
            const preview = this.createTrendCard(trend);
            preview.classList.add('preview');
            preview.style.pointerEvents = 'none';
            this.trendsGrid.appendChild(preview);
        });
        if (allTrends.length > this.trendsShownLimit) {
            this.addShowMoreToggle(allTrends);
        }
    }

    createTrendCard(trend) {
        const card = document.createElement('div');
        card.className = 'trend-card';
        
        const sourceIcon = trend.source === 'hacker_news' ? 'fab fa-hacker-news' : 'fas fa-search';
        const sourceLabel = trend.source === 'hacker_news' ? 'Hacker News' : 'Web Search';
        
        // Determine score class based on relevance ranges
        const score = trend.score || 0;
        let scoreClass = 'score-very-low'; // < 30 (red)
        if (score >= 70) {
            scoreClass = 'score-high'; // 70+ (vibrant green)
        } else if (score >= 50) {
            scoreClass = 'score-medium'; // 50-69 (pale green)
        } else if (score >= 30) {
            scoreClass = 'score-low'; // 30-49 (orange)
        }
        
        // Get HN points if available, otherwise use score
        const displayPoints = trend.metadata?.hn_points || score;
        const isHN = trend.source === 'hacker_news';
        
        card.innerHTML = `
            <div class="trend-header">
                <div class="trend-source ${isHN ? 'hn-source' : 'web-source'}">
                    <i class="${sourceIcon}"></i>
                    ${sourceLabel}
                </div>
                <div class="trend-score ${scoreClass}">${score}</div>
            </div>
            <h3 class="trend-title">${this.cleanDisplayText(trend.title || 'No title')}</h3>
            <p class="trend-description">${this.cleanDisplayText(trend.description || 'No description available')}</p>
            ${trend.tags && trend.tags.length > 0 ? `
                <div class="trend-tags">
                    ${trend.tags.map(tag => `<span class="trend-tag">${this.escapeHtml(tag)}</span>`).join('')}
                </div>
            ` : ''}
            <div class="trend-footer">
                <span>${new Date(trend.timestamp).toLocaleDateString()}</span>
                ${isHN ? `<div class="hn-points"><strong>${displayPoints}</strong> post pts</div>` : ''}
                ${trend.url ? `<a href="${trend.url}" target="_blank" rel="noopener">View Source <i class="fas fa-external-link-alt"></i></a>` : ''}
            </div>
        `;
        
        if (trend.url) {
            card.style.cursor = 'pointer';
            card.addEventListener('click', () => {
                window.open(trend.url, '_blank', 'noopener');
            });
        }
        
        return card;
    }

    displayDetectedRepos(repos) {
        this.reposGrid.innerHTML = repos.map(repo => `
            <a href="https://github.com/${repo}" target="_blank" class="repo-card" rel="noopener">
                <i class="fab fa-github"></i>
                ${this.escapeHtml(repo)}
            </a>
        `).join('');
        
        this.analyzeReposBtn.style.display = repos.length > 0 ? 'flex' : 'none';
    }

    async analyzeRepositories() {
        if (this.detectedRepos.length === 0) return;
        
        this.showLoading('Analyzing repositories...');
        
        try {
            const requestData = {
                repositories: this.detectedRepos,
                include_metrics: true,
                include_recent_activity: true
            };

            const response = await fetch('/api/v1/repositories', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`Repository analysis failed: ${response.status}`);
            }

            const data = await response.json();
            this.displayRepositoryAnalysis(data);
            
        } catch (error) {
            console.error('Repository analysis error:', error);
            this.showError(`Repository analysis failed: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    displayRepositoryAnalysis(data) {
        // This could be expanded to show detailed repository metrics
        // For now, we'll show the insights
        if (data.insights) {
            const insightsDiv = document.createElement('div');
            insightsDiv.className = 'repo-insights';
            insightsDiv.innerHTML = `
                <h4><i class="fas fa-lightbulb"></i> Repository Insights</h4>
                <p>${this.escapeHtml(data.insights)}</p>
            `;
            
            this.reposContainer.appendChild(insightsDiv);
        }
    }

    toggleChat() {
        const isVisible = this.chatContainer.style.display !== 'none';
        this.chatContainer.style.display = isVisible ? 'none' : 'block';
        if (this.chatSection) {
            this.chatSection.style.display = 'block';
        }
        
        if (!isVisible) {
            this.chatToggleBtn.innerHTML = '<i class="fas fa-times"></i> Close Chat';
            this.chatContainer.scrollIntoView({ behavior: 'smooth' });
        } else {
            this.chatToggleBtn.innerHTML = '<i class="fas fa-comments"></i> Ask anything else?';
        }
    }

    async sendChatMessage() {
        const message = this.chatInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        this.addChatMessage(message, 'user');
        this.chatInput.value = '';
        
        // Show thinking indicator
        const thinkingId = this.addChatMessage('Thinking...', 'ai');
        
        try {
            const response = await fetch('/api/v1/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: message })
            });

            if (!response.ok) {
                throw new Error(`Chat failed: ${response.status}`);
            }

            const data = await response.json();
            
            // Remove thinking indicator and add actual response
            const thinkingElement = document.getElementById(thinkingId);
            if (thinkingElement) {
                thinkingElement.remove();
            }
            
            // Handle error responses gracefully
            if (data.message_type === 'error') {
                this.addChatMessage('I apologize, but I\'m having trouble with chat right now. Please try using the "Analyze Trends" feature above for tech-related questions, or try your general question again later.', 'ai');
            } else {
                this.addChatMessage(data.response, 'ai');
            }
            
        } catch (error) {
            console.error('Chat error:', error);
            const thinkingElement = document.getElementById(thinkingId);
            if (thinkingElement) {
                // Update the thinking message to show error with markdown support
                const markdownContainer = document.createElement('div');
                markdownContainer.className = 'markdown-content';
                markdownContainer.innerHTML = this.renderMarkdown('Sorry, I encountered an error. For tech questions, please use the **"Analyze Trends"** feature above.');
                thinkingElement.innerHTML = '';
                thinkingElement.appendChild(markdownContainer);
                this.applySyntaxHighlighting(markdownContainer);
            }
        }
    }

    addChatMessage(content, sender) {
        const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}`;
        messageDiv.id = messageId;
        
        // Render markdown for AI responses, plain text for user messages
        if (sender === 'ai') {
            const markdownContainer = document.createElement('div');
            markdownContainer.className = 'markdown-content';
            markdownContainer.innerHTML = this.renderMarkdown(content);
            messageDiv.appendChild(markdownContainer);
            this.applySyntaxHighlighting(markdownContainer);
        } else {
            messageDiv.textContent = content;
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        
        return messageId;
    }

    exportResults() {
        if (!this.lastQuery) return;
        
        const results = {
            query: this.lastQuery,
            timestamp: new Date().toISOString(),
            trends: Array.from(this.trendsGrid.children).map(card => {
                // Get the source class to determine the proper label
                const sourceElement = card.querySelector('.trend-source');
                const isHN = sourceElement?.classList.contains('hn-source');
                const cleanSource = isHN ? 'Hacker News' : 'Web Search';
                
                return {
                    title: card.querySelector('.trend-title')?.textContent || '',
                    source: cleanSource,
                    url: card.querySelector('.trend-footer a')?.href || ''
                };
            }),
            summary: this.summaryContent.textContent || '',
            repositories: this.detectedRepos
        };
        
        const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `trend-analysis-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    showLoading(text = 'Loading...') {
        document.getElementById('loadingText').textContent = text;
        this.loadingOverlay.style.display = 'flex';
    }

    hideLoading() {
        this.loadingOverlay.style.display = 'none';
    }

    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        this.errorModal.style.display = 'flex';
    }

    hideError() {
        this.errorModal.style.display = 'none';
    }

    async loadAvailableFiles() {
        try {
            const response = await fetch('/api/v1/files');
            if (response.ok) {
                const data = await response.json();
                this.availableFiles = data.files || [];
                console.log('Loaded available files:', this.availableFiles);
            }
        } catch (error) {
            console.warn('Failed to load available files:', error);
            // Fallback files
            this.availableFiles = [
                { name: 'repository_metrics.json', description: 'Sample GitHub repository metrics' },
                { name: 'tech_trends_sample.json', description: 'Sample technology trends data' },
                { name: 'mcp_servers.json', description: 'MCP server configuration' }
            ];
        }
    }

    handleInputChange(e) {
        this.handleFileAutocomplete(e.target, 'search');
    }

    handleChatInputChange(e) {
        this.handleFileAutocomplete(e.target, 'chat');
    }

    handleKeyDown(e) {
        this.handleAutocompleteKeyDown(e, 'search');
    }

    handleChatKeyDown(e) {
        this.handleAutocompleteKeyDown(e, 'chat');
    }

    handleFileAutocomplete(input, context) {
        const value = input.value;
        const cursorPos = input.selectionStart;
        
        // Find @ symbol before cursor
        const beforeCursor = value.substring(0, cursorPos);
        const atMatch = beforeCursor.match(/@([a-zA-Z0-9_.-]*)$/);
        
        if (atMatch) {
            const prefix = atMatch[1];
            const filteredFiles = this.availableFiles.filter(file => 
                file.name.toLowerCase().includes(prefix.toLowerCase())
            );
            
            if (filteredFiles.length > 0) {
                this.showFileAutocomplete(input, filteredFiles, atMatch.index + 1, context);
                return;
            }
        }
        
        this.hideFileAutocomplete();
    }

    showFileAutocomplete(input, files, atPosition, context) {
        this.hideFileAutocomplete();
        
        const autocomplete = document.createElement('div');
        autocomplete.id = `file-autocomplete-${context}`;
        autocomplete.className = 'file-autocomplete';
        
        files.forEach((file, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            if (index === 0) item.classList.add('selected');
            
            item.innerHTML = `
                <div class="file-name">📄 ${file.name}</div>
                <div class="file-description">${file.description}</div>
            `;
            
            item.addEventListener('click', () => {
                this.insertFile(input, file.name, atPosition);
                this.hideFileAutocomplete();
            });
            
            autocomplete.appendChild(item);
        });
        
        // Position autocomplete
        const rect = input.getBoundingClientRect();
        autocomplete.style.position = 'absolute';
        autocomplete.style.top = `${rect.bottom + window.scrollY}px`;
        autocomplete.style.left = `${rect.left + window.scrollX}px`;
        autocomplete.style.width = `${rect.width}px`;
        autocomplete.style.zIndex = '1000';
        
        document.body.appendChild(autocomplete);
        this.fileAutocompleteVisible = true;
        this.currentAutocomplete = autocomplete;
        this.currentInput = input;
        this.currentAtPosition = atPosition;
        this.currentFiles = files;
        this.selectedIndex = 0;
    }

    hideFileAutocomplete() {
        const existing = document.querySelector('.file-autocomplete');
        if (existing) {
            existing.remove();
        }
        this.fileAutocompleteVisible = false;
        this.currentAutocomplete = null;
    }

    handleAutocompleteKeyDown(e, context) {
        if (!this.fileAutocompleteVisible) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = (this.selectedIndex + 1) % this.currentFiles.length;
                this.updateAutocompleteSelection();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = (this.selectedIndex - 1 + this.currentFiles.length) % this.currentFiles.length;
                this.updateAutocompleteSelection();
                break;
            case 'Enter':
                e.preventDefault();
                const selectedFile = this.currentFiles[this.selectedIndex];
                this.insertFile(this.currentInput, selectedFile.name, this.currentAtPosition);
                this.hideFileAutocomplete();
                break;
            case 'Escape':
                e.preventDefault();
                this.hideFileAutocomplete();
                break;
        }
    }

    updateAutocompleteSelection() {
        const items = this.currentAutocomplete.querySelectorAll('.autocomplete-item');
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === this.selectedIndex);
        });
    }

    insertFile(input, filename, atPosition) {
        const value = input.value;
        const beforeAt = value.substring(0, atPosition - 1);
        const afterCursor = value.substring(input.selectionStart);
        
        const newValue = beforeAt + `@${filename}` + afterCursor;
        input.value = newValue;
        
        // Set cursor position after the inserted filename
        const newCursorPos = atPosition + filename.length;
        input.setSelectionRange(newCursorPos, newCursorPos);
        input.focus();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    cleanDisplayText(text) {
        if (!text) return '';
        
        // Create a temporary div to decode HTML entities and strip tags
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = text;
        
        // Get the text content (this strips all HTML tags)
        let cleanText = tempDiv.textContent || tempDiv.innerText || '';
        
        // Clean up special characters and formatting artifacts
        cleanText = cleanText
            // Remove pronunciation guides like (/miːm/ ⓘ; MEEM)
            .replace(/\s*\([^)]*[ⓘ][^)]*\)/g, '')
            // Remove standalone pronunciation symbols
            .replace(/\s*[ⓘ]\s*/g, ' ')
            // Remove extra phonetic notations in parentheses at start
            .replace(/^\s*\([^)]*\)\s*[;:]?\s*/g, '')
            // Clean up multiple spaces
            .replace(/\s+/g, ' ')
            // Remove leading/trailing whitespace
            .trim();
        
        // If text is too long, truncate intelligently
        if (cleanText.length > 200) {
            // Find a good breaking point (sentence end or comma)
            let truncated = cleanText.substring(0, 180);
            const lastSentence = truncated.lastIndexOf('. ');
            const lastComma = truncated.lastIndexOf(', ');
            
            if (lastSentence > 100) {
                truncated = cleanText.substring(0, lastSentence + 1);
            } else if (lastComma > 100) {
                truncated = cleanText.substring(0, lastComma + 1);
            } else {
                truncated = cleanText.substring(0, 180) + '...';
            }
            
            return truncated;
        }
        
        return cleanText;
    }

    renderMarkdown(content) {
        // Safely render markdown content with syntax highlighting
        if (typeof marked === 'undefined') {
            return this.escapeHtml(content);
        }
        
        try {
            // Preprocess the content to handle escape sequences and improve formatting
            let processedContent = content
                // Convert literal \n to actual line breaks
                .replace(/\\n/g, '\n')
                // Convert \n followed by numbers (like \n1, \n2) to proper numbered lists
                .replace(/\\n(\d+)\.\s*/g, '\n$1. ')
                // Convert other escaped sequences
                .replace(/\\t/g, '\t')
                // Clean up multiple consecutive line breaks
                .replace(/\n\s*\n\s*\n/g, '\n\n')
                // Ensure proper spacing around headers and sections
                .replace(/([a-zA-Z]:)(\s*)\\n/g, '$1\n\n')
                // Fix spacing around section titles
                .replace(/(Summary of Key Trends|Emerging Technologies Identified|GitHub Repositories Mentioned|Correlation Between Different Sources|Recommendations for Further Analysis):/g, '\n## $1\n')
                // Clean up any remaining literal backslash-n patterns
                .replace(/([^\\])\\n/g, '$1\n')
                // Fix numbered lists that start with numbers
                .replace(/^\s*(\d+)\.\s*\*\*$/gm, '\n## $1.')
                // Clean up standalone ** markers that aren't properly closed
                .replace(/^\s*\*\*\s*$/gm, '')
                // Fix broken bold formatting - ensure ** pairs are on same line
                .replace(/\*\*([^*\n]+?)\*\*/g, '**$1**')
                // Clean up code-style backticks that might be artifacts
                .replace(/`([^`\n]+?)`/g, '**$1**')
                // Trim whitespace
                .trim();

            const html = marked.parse(processedContent);
            return html;
        } catch (error) {
            console.warn('Markdown parsing failed:', error);
            return this.escapeHtml(content);
        }
    }

    prettifyAssistantText(text) {
        // Unwrap common wrapper formats (e.g., AgentRunResult(output="...")) and tidy quotes
        if (!text) return '';

        try {
            // Match AgentRunResult(output="...") or with single quotes
            const agentMatch = text.match(/AgentRunResult\s*\(\s*output\s*=\s*(["'])([\s\S]*?)\1\s*\)/i);
            if (agentMatch && agentMatch[2]) {
                return agentMatch[2].trim();
            }

            // Generic output: "..." pattern
            const outputMatch = text.match(/\boutput\s*[:=]\s*(["'])([\s\S]*?)\1/i);
            if (outputMatch && outputMatch[2]) {
                return outputMatch[2].trim();
            }

            // Strip surrounding single/double quotes if the whole string is quoted
            if ((text.startsWith('"') && text.endsWith('"')) || (text.startsWith('\'') && text.endsWith('\''))) {
                return text.slice(1, -1).trim();
            }
        } catch (e) {
            // Fall through to return original text
        }

        return text;
    }

    applySyntaxHighlighting(element) {
        // Apply syntax highlighting to code blocks
        if (typeof Prism !== 'undefined') {
            setTimeout(() => {
                Prism.highlightAllUnder(element);
            }, 10);
        }
    }

    formatQueryForDisplay(rawQuery) {
        // Extract file references and clean query for beautiful display
        const filePattern = /--- Content of (.*?) ---\s*([\s\S]*?)\s*--- End of .*? ---/g;
        let cleanQuery = rawQuery;
        let fileInfo = [];
        let match;

        // Extract file content and references
        while ((match = filePattern.exec(rawQuery)) !== null) {
            const filename = match[1];
            const content = match[2].trim();
            
            // Try to parse JSON content for better display
            let parsedContent = null;
            try {
                parsedContent = JSON.parse(content);
            } catch (e) {
                // Not JSON, use as-is
            }

            fileInfo.push({
                filename: filename,
                content: content,
                parsed: parsedContent
            });

            // Remove the file content from the clean query
            cleanQuery = cleanQuery.replace(match[0], '').trim();
        }

        // Create beautiful title and metadata
        let title = '';
        let meta = '';

        if (fileInfo.length > 0) {
            // Format with file information
            const file = fileInfo[0]; // Use first file for display
            
            if (file.parsed && file.parsed.Context) {
                // Use the Context from JSON file as the main query
                title = `<i class="fas fa-file-alt" style="color: #6366f1; margin-right: 8px;"></i>Trends for: <span style="color: #6366f1; font-weight: 600;">"${this.escapeHtml(file.parsed.Context)}"</span>`;
                
                if (cleanQuery) {
                    title += ` <span style="color: #64748b;">+ "${this.escapeHtml(cleanQuery)}"</span>`;
                }
            } else {
                // Fallback to filename and clean query
                title = `<i class="fas fa-file-alt" style="color: #6366f1; margin-right: 8px;"></i>Analysis based on <span style="color: #6366f1; font-weight: 600;">${this.escapeHtml(file.filename)}</span>`;
                
                if (cleanQuery) {
                    title += `: <span style="color: #374151;">"${this.escapeHtml(cleanQuery)}"</span>`;
                }
            }

            // Create metadata about the file
            meta = `<i class="fas fa-info-circle" style="color: #10b981; margin-right: 4px;"></i>Using data from <strong>${this.escapeHtml(file.filename)}</strong>`;
            
            if (file.parsed && file.parsed.Tools && file.parsed.Tools.length > 0) {
                const toolCount = file.parsed.Tools.length;
                meta += ` (${toolCount} tool${toolCount > 1 ? 's' : ''} referenced)`;
            }
        } else {
            // No file content, just clean query
            title = `<i class="fas fa-search" style="color: #6366f1; margin-right: 8px;"></i>Trends for: <span style="color: #374151;">"${this.escapeHtml(cleanQuery)}"</span>`;
            meta = '<i class="fas fa-globe" style="color: #10b981; margin-right: 4px;"></i>Live search results';
        }

        return {
            title: title,
            meta: meta,
            fileInfo: fileInfo,
            cleanQuery: cleanQuery
        };
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TrendTracker();
});
