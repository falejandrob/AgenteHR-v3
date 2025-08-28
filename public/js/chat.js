// Chat functionality with Markdown support
class HavasChat {
    constructor() {
        this.messagesArea = document.getElementById('messagesArea');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.statusText = document.getElementById('statusText');
        this.docsCounter = document.getElementById('docsCounter');
        this.docsCount = document.getElementById('docsCount');
        this.menuButton = document.getElementById('menuButton');
        this.dropdownMenu = document.getElementById('dropdownMenu');
        this.newChatOption = document.getElementById('newChatOption');
        
        // To manage ongoing requests
        this.currentRequest = null;
        this.isTyping = false;
        
        this.initializeEventListeners();
        this.loadMarkdownRenderer();
        this.checkHealth();

    // Input position management
    this.inputSection = document.getElementById('inputSection');
    this.hasStartedConversation = false;
    }
    
    // Load Markdown library
    async loadMarkdownRenderer() {
        try {
            // Load marked.js from CDN
            if (!window.marked) {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/marked/9.1.6/marked.min.js';
                script.onload = () => {
                    console.log('Markdown renderer loaded');
                    // Configure marked to be safer
                    if (window.marked) {
                        marked.setOptions({
                            breaks: true,
                            gfm: true,
                            sanitize: false // We'll handle this manually
                        });
                    }
                };
                document.head.appendChild(script);
            }
        } catch (error) {
            console.error('Error loading markdown renderer:', error);
        }
    }
    
    initializeEventListeners() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Menu button functionality
        this.menuButton.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });
        
        // New chat option
        this.newChatOption.addEventListener('click', () => {
            this.startNewConversation();
            this.hideDropdown();
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.dropdownMenu.contains(e.target) && !this.menuButton.contains(e.target)) {
                this.hideDropdown();
            }
        });
        
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea ChatGPT style
        this.messageInput.addEventListener('input', () => {
            // Reset height to auto to get correct scrollHeight
            this.messageInput.style.height = 'auto';
            
            // Calculate new height based on content
            const newHeight = Math.min(this.messageInput.scrollHeight, 200);
            this.messageInput.style.height = newHeight + 'px';
            
            // Update send button state
            this.updateSendButtonState();
        });

        // Initial send button state
        this.updateSendButtonState();
    }
    
    // Toggle dropdown menu
    toggleDropdown() {
        const isVisible = this.dropdownMenu.classList.contains('show');
        if (isVisible) {
            this.hideDropdown();
        } else {
            this.showDropdown();
        }
    }
    
    // Show dropdown menu
    showDropdown() {
        this.dropdownMenu.classList.add('show');
        this.menuButton.classList.add('active');
    }
    
    // Hide dropdown menu
    hideDropdown() {
        this.dropdownMenu.classList.remove('show');
        this.menuButton.classList.remove('active');
    }
    
    // Update send button state based on input content
    updateSendButtonState() {
        const hasContent = this.messageInput.value.trim().length > 0;
        this.sendButton.style.opacity = hasContent ? '1' : '0.5';
        this.sendButton.disabled = !hasContent;
    }
    
    async checkHealth() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            if (data.status === 'healthy') {
                this.updateStatus('Azure AI Connected', true);
                if (data.services) {
                    console.log('Services status:', data.services);
                }
            } else {
                this.updateStatus('Connection problem', false);
                console.error('Health check failed:', data);
            }
        } catch (error) {
            this.updateStatus('Disconnected', false);
            console.error('Health check failed:', error);
        }
    }
    
    updateStatus(text, isConnected) {
        this.statusText.textContent = text;
        const statusDot = document.querySelector('.status-dot');
        statusDot.style.background = isConnected ? '#00ff00' : '#ff0000';
        statusDot.style.boxShadow = `0 0 10px ${isConnected ? '#00ff00' : '#ff0000'}`;
    }
    
    // Function to start a new conversation
    startNewConversation() {
        // Cancel any ongoing request
        if (this.currentRequest) {
            this.currentRequest.abort();
            this.currentRequest = null;
            console.log('Request cancelled for new conversation');
        }

    // Restore centered input position
    this.restoreCenteredPosition();
        
        // Clear typing state
        this.hideTyping();
        this.isTyping = false;
        
        // Re-enable input if it was disabled
        this.messageInput.disabled = false;
        this.updateSendButtonState();
        
        // Clean ALL elements from messages area (including welcome-message)
        const allElements = this.messagesArea.querySelectorAll('.message, .welcome-message');
        
        if (allElements.length === 0) {
            // If no elements, do nothing (already clean)
            return;
        }
        
        allElements.forEach(element => {
            element.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                if (element.parentNode) {
                    element.remove();
                }
            }, 300);
        });
        
        // Restore welcome message after cleaning
        setTimeout(() => {
            const welcomeMessage = document.createElement('div');
            welcomeMessage.className = 'welcome-message fade-in';
            welcomeMessage.innerHTML = `
                <div class="welcome-icon"></div>
                <h3>Welcome to HAVAS Assistant!</h3>
                <p>I'm here to help you with any questions about our knowledge base. How can I assist you today?</p>
            `;
            this.messagesArea.appendChild(welcomeMessage);
            
            // Clean input
            this.messageInput.value = '';
            this.messageInput.style.height = 'auto';
            this.updateSendButtonState();
            this.messageInput.focus();
            
            // Hide documents counter
            if (this.docsCounter) {
                this.docsCounter.style.display = 'none';
            }
            
            console.log('New conversation started');
        }, 350);
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;
        
        // If there's an ongoing request, cancel it
        if (this.currentRequest) {
            this.currentRequest.abort();
        }
        
        // Create new AbortController for this request
        this.currentRequest = new AbortController();
        
        // Clear welcome message if it exists
        const welcomeMessage = document.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        // Add user message
        this.addMessage(message, 'user');

        // Clear input and disable send button
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        this.updateSendButtonState();
        this.messageInput.disabled = true;

        // Show typing indicator
        this.showTyping();
        this.isTyping = true;

        // If it's the first message, dock input to bottom
        if (!this.hasStartedConversation) {
            this.dockInputSection();
            this.hasStartedConversation = true;
        }

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message }),
                signal: this.currentRequest.signal
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.hideTyping();
                this.isTyping = false;
                this.addMessage(data.response, 'assistant', true); // true for markdown

                // Update documents counter if applicable
                if (data.documentsFound > 0 && this.docsCounter) {
                    this.docsCounter.style.display = 'flex';
                    if (this.docsCount) {
                        this.docsCount.textContent = data.documentsFound;
                    }

                    // Show context indicator
                    if (data.hasContext) {
                        const contextIndicator = document.createElement('div');
                        contextIndicator.className = 'context-indicator';
                        contextIndicator.innerHTML = `
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                <polyline points="14,2 14,8 20,8"/>
                            </svg>
                            Response based on found documents
                        `;                        const lastMessage = this.messagesArea.lastElementChild;
                        if (lastMessage && lastMessage.classList.contains('assistant')) {
                            const messageContent = lastMessage.querySelector('.message-content');
                            if (messageContent) {
                                messageContent.appendChild(contextIndicator);
                            }
                        }
                    }
                    
                    // Hide counter after 5 seconds
                    if (this.docsCounter) {
                        setTimeout(() => {
                            this.docsCounter.style.display = 'none';
                        }, 5000);
                    }
                }
            } else {
                this.hideTyping();
                this.isTyping = false;
                
                // Show server error message if available
                const errorMsg = data.error || data.details || 'Server error';
                console.error('Server error:', errorMsg);
                
                this.addMessage(
                    `Server error: **${errorMsg}**\n\nPlease try again in a few moments.`,
                    'assistant',
                    true
                );
            }
        } catch (error) {
            // If request was cancelled, don't show error
            if (error.name === 'AbortError') {
                console.log('Request was cancelled');
                return;
            }
            
            this.hideTyping();
            this.isTyping = false;
            
            console.error('Error in sendMessage:', error);
            
            this.addMessage(
                'Sorry, an error occurred while processing your message. Please **try again** in a few moments.\n\n*If the problem persists, contact technical support.*',
                'assistant',
                true
            );

            // Show reconnection status
            this.updateStatus('Error - Reconnecting...', false);
            setTimeout(() => this.checkHealth(), 2000);
        } finally {
            // Only clear currentRequest if it wasn't aborted by new conversation
            if (this.currentRequest && !this.currentRequest.signal.aborted) {
                this.currentRequest = null;
            }
            this.messageInput.disabled = false;
            this.updateSendButtonState();
            this.messageInput.focus();
        }
    }
    
    // Dock input to bottom (transition from centered to bottom)
    dockInputSection() {
        if (!this.inputSection) return;
        this.inputSection.classList.remove('centered');
        void this.inputSection.offsetWidth; // force reflow for transition
        this.inputSection.classList.add('docked');
    }

    // Restore centered input position (for new conversation)
    restoreCenteredPosition() {
        if (!this.inputSection) return;
        this.inputSection.classList.remove('docked');
        void this.inputSection.offsetWidth;
        this.inputSection.classList.add('centered');
        this.hasStartedConversation = false;
    }

    // Function for basic HTML sanitization
    sanitizeHtml(html) {
        const temp = document.createElement('div');
        temp.textContent = html;
        return temp.innerHTML
            .replace(/&lt;(\/?(?:b|strong|i|em|u|code|pre|h[1-6]|p|br|ul|ol|li|blockquote|mark))&gt;/g, '<$1>')
            .replace(/&lt;\/(\w+)&gt;/g, '</$1>');
    }
    
    // Enhanced function for Markdown rendering
    renderMarkdown(text) {
        if (!window.marked) {
            // Fallback: basic rendering if marked is not available
            return this.basicMarkdownRender(text);
        }
        try {
            let html = marked.parse(text);
            // Remove scripts and dangerous attributes
            html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
            html = html.replace(/on\w+="[^"]*"/gi, '');
            html = html.replace(/javascript:/gi, '');
            // Filter unauthorized tags (simple whitelist)
            const allowedTags = ['p','br','strong','b','em','i','u','h1','h2','h3','h4','h5','h6','ul','ol','li','blockquote','code','pre','mark','table','thead','tbody','tr','th','td'];
            html = html.replace(/<(\/)?(\w+)[^>]*>/g, (match, closing, tag) => {
                return allowedTags.includes(tag.toLowerCase()) ? match : '';
            });
            return html;
        } catch (e) {
            console.error('Markdown rendering error:', e);
            return this.basicMarkdownRender(text);
        }
    }
    
    // Basic Markdown rendering as fallback
    basicMarkdownRender(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/^\- (.*$)/gim, '<li>$1</li>')
            .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
            .replace(/\n/g, '<br>');
    }
    
    addMessage(text, sender, useMarkdown = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender} fade-in`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (useMarkdown && sender === 'assistant') {
            contentDiv.innerHTML = this.renderMarkdown(text);
            // Enhance tables after rendering
            this.enhanceTablesInMessage(contentDiv);
        } else {
            contentDiv.textContent = text;
        }
        
        messageDiv.appendChild(contentDiv);
        this.messagesArea.appendChild(messageDiv);
        
        // Scroll to bottom with smooth animation
        setTimeout(() => {
            this.messagesArea.scrollTo({
                top: this.messagesArea.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);
        
        // Animate message entry
        setTimeout(() => {
            messageDiv.classList.add('visible');
        }, 50);
    }
    
    showTyping() {
        this.typingIndicator.classList.add('active');
        this.isTyping = true;
        setTimeout(() => {
            this.messagesArea.scrollTo({
                top: this.messagesArea.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);
    }
    
    hideTyping() {
        this.typingIndicator.classList.remove('active');
        this.isTyping = false;
    }
    
    // Function for index debugging
    async debugIndex() {
        try {
            const response = await fetch('/api/debug/index');
            const data = await response.json();
            console.log('Index Debug Info:', data);
            return data;
        } catch (error) {
            console.error('Error getting index debug information:', error);
        }
    }
    
    // Adaptive table enhancement similar to ChatGPT
    enhanceTablesInMessage(messageDiv) {
        const tables = messageDiv.querySelectorAll('table');

        tables.forEach(table => {
            // Remove inline styles from previous passes
            table.removeAttribute('style');

            // Count rows for compact class
            const bodyRows = table.querySelectorAll('tbody tr').length || table.querySelectorAll('tr').length;
            if (bodyRows > 0 && bodyRows <= 4) {
                table.classList.add('compact');
            }

            // Wrap table only if scrollable (defer until next frame to ensure dimensions)
            requestAnimationFrame(() => {
                const needsHorizontal = table.scrollWidth > table.clientWidth;
                const needsVertical = table.scrollHeight > 400; // threshold like CSS max-height

                const alreadyWrapped = table.parentElement.classList.contains('table-wrapper');
                if (!alreadyWrapped && (needsHorizontal || needsVertical)) {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'table-wrapper scrollable';
                    table.parentNode.insertBefore(wrapper, table);
                    wrapper.appendChild(table);
                } else if (!alreadyWrapped) {
                    // Still wrap for consistent radius/shadow, but without scroll class
                    const wrapper = document.createElement('div');
                    wrapper.className = 'table-wrapper';
                    table.parentNode.insertBefore(wrapper, table);
                    wrapper.appendChild(table);
                } else if (alreadyWrapped) {
                    // Toggle scrollable class depending on need
                    table.parentElement.classList.toggle('scrollable', (needsHorizontal || needsVertical));
                }
            });
        });
    }
}

// Initialize chat when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const chat = new HavasChat();
    
    // Add connection check every 30 seconds
    setInterval(() => {
        chat.checkHealth();
    }, 30000);
    
    // Add debug command in console
    window.debugHavasIndex = () => chat.debugIndex();
    
    console.log('HAVAS Chat initialized');
    console.log('Use debugHavasIndex() in console to see index structure');
});