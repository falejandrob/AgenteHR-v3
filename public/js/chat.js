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
        this.uploadFileOption = document.getElementById('uploadFileOption');
        this.fileInput = document.getElementById('fileInput');
        this.uploadedFilesSection = document.getElementById('uploadedFilesSection');
        this.uploadedFilesList = document.getElementById('uploadedFilesList');
        
        // To manage ongoing requests
        this.currentRequest = null;
        this.isTyping = false;
        
        // File management
        this.uploadedFiles = [];
        this.sessionId = this.generateSessionId();
        
        this.initializeEventListeners();
        this.loadMarkdownRenderer();
        this.checkHealth();

        // Input position management
        this.inputSection = document.getElementById('inputSection');
        this.hasStartedConversation = false;
        
        // Load uploaded files after everything is initialized
        setTimeout(() => {
            this.loadUploadedFiles();
        }, 100);
        
        // Setup cleanup on page unload
        this.setupCleanupOnUnload();
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
        
        // Upload file option - check if element exists
        if (this.uploadFileOption) {
            this.uploadFileOption.addEventListener('click', () => {
                this.fileInput.click();
                this.hideDropdown();
            });
        }
        
        // File input change event - check if element exists
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleMultipleFileUpload(Array.from(e.target.files));
                }
            });
        }
        
        // Drag and drop functionality
        this.setupDragAndDrop();
        
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

        // Capture files attached to this message
        const attachedFiles = this.captureAttachedFiles();

        // Add user message with files
        this.addMessage(message, 'user', attachedFiles);

        // Clear input and disable send button
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        this.updateSendButtonState();
        this.messageInput.disabled = true;

        // Clear files from input area (like ChatGPT)
        this.clearFilesFromInput();

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
                body: JSON.stringify({ 
                    message: message,
                    sessionId: this.sessionId
                }),
                signal: this.currentRequest.signal
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.hideTyping();
                this.isTyping = false;
                
                // Add assistant response without any indicators
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
    
    addMessage(text, sender, useMarkdownOrFiles = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender} fade-in`;
        
        // Handle files parameter for user messages
        let attachedFiles = null;
        let useMarkdown = false;
        
        if (sender === 'user' && Array.isArray(useMarkdownOrFiles)) {
            attachedFiles = useMarkdownOrFiles;
        } else if (typeof useMarkdownOrFiles === 'boolean') {
            useMarkdown = useMarkdownOrFiles;
        }
        
        // Add files display if there are attached files
        if (attachedFiles && attachedFiles.length > 0) {
            const filesDiv = document.createElement('div');
            filesDiv.className = 'message-files';
            
            attachedFiles.forEach(file => {
                const fileElement = document.createElement('div');
                fileElement.className = 'message-file-item';
                
                const fileExtension = file.type || file.name.split('.').pop().toLowerCase();
                const fileSize = this.formatFileSize(file.size);
                
                fileElement.innerHTML = `
                    <div class="message-file-icon ${fileExtension}">${fileExtension.toUpperCase()}</div>
                    <div class="message-file-info">
                        <p class="message-file-name">${file.name}</p>
                        <p class="message-file-size">${fileSize}</p>
                    </div>
                `;
                
                filesDiv.appendChild(fileElement);
            });
            
            messageDiv.appendChild(filesDiv);
        }
        
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
    
    // Generate session ID
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    // Setup drag and drop functionality
    setupDragAndDrop() {
        const dropZones = [this.messagesArea, this.inputSection];
        
        dropZones.forEach(zone => {
            if (!zone) return; // Skip if element doesn't exist
            
            zone.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (this.uploadedFilesSection) {
                    this.uploadedFilesSection.classList.add('file-upload-drag');
                }
            });
            
            zone.addEventListener('dragleave', (e) => {
                e.preventDefault();
                e.stopPropagation();
                // Only remove if leaving the actual drop zone
                if (!zone.contains(e.relatedTarget) && this.uploadedFilesSection) {
                    this.uploadedFilesSection.classList.remove('file-upload-drag');
                }
            });
            
            zone.addEventListener('drop', (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (this.uploadedFilesSection) {
                    this.uploadedFilesSection.classList.remove('file-upload-drag');
                }
                
                const files = Array.from(e.dataTransfer.files);
                if (files.length > 0) {
                    this.handleMultipleFileUpload(files);
                }
            });
        });
    }
    
    // Handle multiple file upload with ChatGPT-style display
    async handleMultipleFileUpload(files) {
        if (!files || files.length === 0) return;
        
        // Validate all files first
        const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
        const allowedExtensions = ['.pdf', '.xlsx'];
        const maxFileSize = 10 * 1024 * 1024; // 10MB
        
        const validFiles = [];
        const invalidFiles = [];
        
        for (const file of files) {
            const fileName = file.name.toLowerCase();
            const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext));
            const hasValidType = allowedTypes.includes(file.type);
            const isValidSize = file.size <= maxFileSize;
            
            if ((hasValidType || hasValidExtension) && isValidSize) {
                validFiles.push(file);
            } else {
                let reason = '';
                if (!hasValidType && !hasValidExtension) {
                    reason = 'Invalid file type (only PDF and XLSX supported)';
                } else if (!isValidSize) {
                    reason = 'File too large (max 10MB)';
                }
                invalidFiles.push({ name: file.name, reason });
            }
        }
        
        // Show validation errors if any
        if (invalidFiles.length > 0) {
            const errorMessage = invalidFiles.map(f => `${f.name}: ${f.reason}`).join('\n');
            this.showNotification(`Some files were rejected:\n${errorMessage}`, 'error');
        }
        
        if (validFiles.length === 0) {
            this.showNotification('No valid files to upload', 'error');
            return;
        }

        // Create file items in chat with progress indicators
        const uploadPromises = validFiles.map(file => this.uploadSingleFileToChat(file));
        
        try {
            await Promise.all(uploadPromises);
            // Refresh the file list after all uploads complete
            await this.loadUploadedFiles();
        } catch (error) {
            console.error('Some file uploads failed:', error);
        }
        
        // Reset file input
        this.fileInput.value = '';
    }

    // Upload single file with ChatGPT-style progress display
    async uploadSingleFileToChat(file) {
        // Create file element in chat
        const fileElement = this.addFileToChat(file);
        
        try {
            const formData = new FormData();
            formData.append('files', file);
            formData.append('sessionId', this.sessionId);
            
            // Show progress circle
            this.showFileProgress(fileElement, 0, true);
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                // Show complete state
                this.showFileProgress(fileElement, 100, false);
                this.markFileAsComplete(fileElement);
                
                // Add to uploaded files list
                if (result.uploaded_files && result.uploaded_files.length > 0) {
                    const fileInfo = result.uploaded_files[0];
                    this.uploadedFiles.push(fileInfo);
                }
                
            } else {
                // Show error state
                this.markFileAsError(fileElement, result.error || 'Upload failed');
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            this.markFileAsError(fileElement, 'Upload failed. Please try again.');
        }
    }

    // Add file to chat area (like ChatGPT)
    addFileToChat(file) {
        const fileExtension = file.name.split('.').pop().toLowerCase();
        const fileSize = this.formatFileSize(file.size);
        
        const fileElement = document.createElement('div');
        fileElement.className = 'chat-file-item uploading';
        fileElement.dataset.fileName = file.name;
        
        fileElement.innerHTML = `
            <div class="chat-file-info">
                <div class="chat-file-icon ${fileExtension}">${fileExtension.toUpperCase()}</div>
                <div class="chat-file-details">
                    <p class="chat-file-name">${file.name}</p>
                    <p class="chat-file-size">${fileSize}</p>
                </div>
            </div>
            <div class="upload-progress-circle spinning">
                <svg class="progress-ring" width="20" height="20">
                    <circle class="progress-ring-background" cx="10" cy="10" r="8"></circle>
                    <circle class="progress-ring-progress" cx="10" cy="10" r="8"></circle>
                </svg>
            </div>
            <div class="chat-file-actions" style="display: none;">
                <button class="chat-file-remove" title="Remove file">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `;
        
        // Add remove event listener
        const removeBtn = fileElement.querySelector('.chat-file-remove');
        removeBtn.addEventListener('click', () => this.removeFileFromChat(fileElement));
        
        // Add to chat files container instead of messages area
        const chatFilesContainer = document.getElementById('chatFilesContainer');
        if (chatFilesContainer) {
            chatFilesContainer.appendChild(fileElement);
            chatFilesContainer.style.display = 'block';
        }
        
        return fileElement;
    }

    // Show file upload progress
    showFileProgress(fileElement, percentage, isIndeterminate = false) {
        const progressCircle = fileElement.querySelector('.upload-progress-circle');
        
        if (!progressCircle) return; // Safety check
        
        if (isIndeterminate) {
            // Show spinning animation
            progressCircle.classList.add('spinning');
        } else {
            // Stop spinning and show percentage if needed
            progressCircle.classList.remove('spinning');
        }
    }

    // Mark file as upload complete
    markFileAsComplete(fileElement) {
        fileElement.classList.remove('uploading');
        fileElement.classList.add('upload-complete');
        
        // Hide progress circle and show remove button
        const progressCircle = fileElement.querySelector('.upload-progress-circle');
        const actions = fileElement.querySelector('.chat-file-actions');
        
        if (progressCircle) {
            progressCircle.style.display = 'none';
        }
        if (actions) {
            actions.style.display = 'flex';
        }
    }

    // Mark file as error
    markFileAsError(fileElement, errorMessage) {
        fileElement.classList.remove('uploading');
        fileElement.classList.add('upload-error');
        
        // Update file details to show error
        const fileDetails = fileElement.querySelector('.chat-file-details');
        if (fileDetails) {
            fileDetails.innerHTML = `
                <p class="chat-file-name">${fileElement.dataset.fileName}</p>
                <p class="chat-file-size" style="color: #ef4444;">${errorMessage}</p>
            `;
        }
        
        // Hide progress circle and show remove button
        const progressCircle = fileElement.querySelector('.upload-progress-circle');
        const actions = fileElement.querySelector('.chat-file-actions');
        
        if (progressCircle) {
            progressCircle.style.display = 'none';
        }
        if (actions) {
            actions.style.display = 'flex';
        }
        
        // Change file icon to error style
        const fileIcon = fileElement.querySelector('.chat-file-icon');
        if (fileIcon) {
            fileIcon.style.background = '#ef4444';
            fileIcon.textContent = '!';
        }
    }

    // Remove file from chat
    async removeFileFromChat(fileElement) {
        const fileName = fileElement.dataset.fileName;
        
        try {
            // If file is already uploaded, remove from server
            if (!fileElement.classList.contains('uploading') && !fileElement.classList.contains('upload-error')) {
                const response = await fetch(`/api/files/${this.sessionId}/${encodeURIComponent(fileName)}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    // Remove from local files array
                    this.uploadedFiles = this.uploadedFiles.filter(f => f.name !== fileName);
                }
            }
            
            // Remove from chat
            fileElement.remove();
            
            // Hide container if no more files
            const chatFilesContainer = document.getElementById('chatFilesContainer');
            if (chatFilesContainer && chatFilesContainer.children.length === 0) {
                chatFilesContainer.style.display = 'none';
            }
            
        } catch (error) {
            console.error('Error removing file:', error);
            this.showNotification('Error removing file', 'error');
        }
    }

    // Handle single file upload (kept for backward compatibility)
    async handleFileUpload(file) {
        // Check file type
        const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
        const allowedExtensions = ['.pdf', '.xlsx'];
        
        const fileName = file.name.toLowerCase();
        const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext));
        
        if (!allowedTypes.includes(file.type) && !hasValidExtension) {
            this.showNotification('Only PDF and XLSX files are supported', 'error');
            return;
        }
        
        // Check file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
            this.showNotification('File size must be less than 10MB', 'error');
            return;
        }
        
        try {
            this.showNotification('Uploading file...', 'info');
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('sessionId', this.sessionId);
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showNotification(`File "${result.file_info.name}" uploaded successfully!`, 'success');
                await this.loadUploadedFiles();
            } else {
                this.showNotification(result.error || 'Upload failed', 'error');
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Upload failed. Please try again.', 'error');
        }
        
        // Reset file input
        this.fileInput.value = '';
    }
    
    // Load uploaded files for the session
    async loadUploadedFiles() {
        try {
            const response = await fetch(`/api/files/${this.sessionId}`);
            const result = await response.json();
            
            if (response.ok) {
                this.uploadedFiles = result.files || [];
                this.updateUploadedFilesDisplay();
                this.displayFilesInChat();
            }
        } catch (error) {
            console.error('Error loading files:', error);
        }
    }

    // Display files in chat area (like ChatGPT)
    displayFilesInChat() {
        const chatFilesContainer = document.getElementById('chatFilesContainer');
        if (!chatFilesContainer) return;
        
        // Clear container
        chatFilesContainer.innerHTML = '';
        
        if (this.uploadedFiles.length === 0) {
            chatFilesContainer.style.display = 'none';
            return;
        }

        // Add each uploaded file to chat files container
        this.uploadedFiles.forEach(file => {
            const fileElement = this.createChatFileElement(file);
            chatFilesContainer.appendChild(fileElement);
        });
        
        // Show container
        chatFilesContainer.style.display = 'block';
    }

    // Create a chat file element for an uploaded file
    createChatFileElement(file) {
        const fileExtension = file.type || 'pdf';
        const fileSize = this.formatFileSize(file.size);
        
        const fileElement = document.createElement('div');
        fileElement.className = 'chat-file-item upload-complete';
        fileElement.dataset.fileName = file.name;
        
        fileElement.innerHTML = `
            <div class="chat-file-info">
                <div class="chat-file-icon ${fileExtension}">${fileExtension.toUpperCase()}</div>
                <div class="chat-file-details">
                    <p class="chat-file-name">${file.name}</p>
                    <p class="chat-file-size">${fileSize}</p>
                </div>
            </div>
            <div class="chat-file-actions">
                <button class="chat-file-remove" title="Remove file">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `;
        
        // Add remove event listener
        const removeBtn = fileElement.querySelector('.chat-file-remove');
        removeBtn.addEventListener('click', () => this.removeFileFromChat(fileElement));
        
        return fileElement;
    }
    
    // Update the uploaded files display (hide the old section)
    updateUploadedFilesDisplay() {
        // Hide the old uploaded files section since we now show files in chat
        if (this.uploadedFilesSection) {
            this.uploadedFilesSection.style.display = 'none';
        }
        return; // Skip the old display logic
        
        if (!this.uploadedFilesSection || !this.uploadedFilesList) {
            console.warn('Uploaded files elements not found');
            return;
        }
        
        if (this.uploadedFiles.length === 0) {
            this.uploadedFilesSection.style.display = 'none';
            return;
        }
        
        this.uploadedFilesSection.style.display = 'block';
        this.uploadedFilesList.innerHTML = '';
        
        this.uploadedFiles.forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'uploaded-file-item';
            
            const fileIcon = file.type === 'pdf' ? 'PDF' : 'XLSX';
            const fileSize = this.formatFileSize(file.size);
            
            fileItem.innerHTML = `
                <div class="file-info">
                    <div class="file-icon ${file.type}">${fileIcon}</div>
                    <div class="file-details">
                        <p class="file-name">${file.name}</p>
                        <p class="file-size">${fileSize}</p>
                    </div>
                </div>
            `;
            
            this.uploadedFilesList.appendChild(fileItem);
        });
    }
    
    // Format file size
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Show notification
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `upload-notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Remove after 4 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 300);
            }
        }, 4000);
    }
    
    // Modified start new conversation to include file clearing
    async startNewConversation() {
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
        
        // Clear files from server first
        await this.clearCurrentSessionFiles();
        
        // Clear uploaded files locally
        this.uploadedFiles = [];
        this.updateUploadedFilesDisplay();
        
        // Generate new session ID
        this.sessionId = this.generateSessionId();
        
        // Clean ALL elements from messages area
        const allElements = this.messagesArea.querySelectorAll('.message, .welcome-message');
        
        if (allElements.length === 0) {
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
        }, 300);
        
        // Call server to start new conversation
        try {
            await fetch('/api/new-conversation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    sessionId: this.sessionId 
                })
            });
        } catch (error) {
            console.error('Error starting new conversation:', error);
        }
    }
    
    // Setup cleanup when page is closed or refreshed
    setupCleanupOnUnload() {
        // Listen for page unload events (F5, closing tab, navigation)
        window.addEventListener('beforeunload', (event) => {
            this.cleanupSessionFiles();
        });
        
        // Listen for unload event (backup)
        window.addEventListener('unload', () => {
            this.cleanupSessionFiles();
        });
        
        // Also cleanup on visibility change (when tab is closed or hidden)
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                // Small delay to ensure the request goes through
                setTimeout(() => {
                    this.cleanupSessionFiles();
                }, 100);
            }
        });
        
        // Cleanup on page hide (iOS Safari support and better mobile handling)
        window.addEventListener('pagehide', (event) => {
            this.cleanupSessionFiles();
        });
        
        // Additional cleanup for navigation events
        window.addEventListener('popstate', () => {
            this.cleanupSessionFiles();
        });
        
        // Cleanup when the page is about to be replaced
        if ('onbeforeunload' in window) {
            window.onbeforeunload = () => {
                this.cleanupSessionFiles();
                return null; // Don't show confirmation dialog
            };
        }
    }
    
    // Capture files currently in the input area
    captureAttachedFiles() {
        const chatFilesContainer = document.getElementById('chatFilesContainer');
        const attachedFiles = [];
        
        if (chatFilesContainer && chatFilesContainer.style.display !== 'none') {
            const fileItems = chatFilesContainer.querySelectorAll('.chat-file-item');
            
            fileItems.forEach(item => {
                const fileName = item.dataset.fileName;
                const fileSizeText = item.querySelector('.chat-file-size')?.textContent || '';
                const fileType = item.querySelector('.chat-file-icon')?.classList[1] || 'unknown';
                
                // Find the file in uploadedFiles array
                const file = this.uploadedFiles.find(f => f.name === fileName);
                if (file) {
                    attachedFiles.push(file);
                }
            });
        }
        
        return attachedFiles;
    }
    
    // Clear files from input area (like ChatGPT)
    clearFilesFromInput() {
        const chatFilesContainer = document.getElementById('chatFilesContainer');
        if (chatFilesContainer) {
            chatFilesContainer.innerHTML = '';
            chatFilesContainer.style.display = 'none';
        }
        // Note: We don't clear uploadedFiles array as files are still on server
    }
    
    // Clean up files for current session
    cleanupSessionFiles() {
        if (this.uploadedFiles.length === 0) return;
        
        try {
            // Use sendBeacon with POST method for reliable cleanup on page unload
            const data = new FormData();
            data.append('action', 'cleanup');
            data.append('sessionId', this.sessionId);
            
            // Try sendBeacon first (most reliable for page unload)
            if (navigator.sendBeacon) {
                const success = navigator.sendBeacon('/api/cleanup-session', data);
                console.log('Cleanup beacon sent for session:', this.sessionId, success ? 'success' : 'failed');
            } else {
                // Fallback for older browsers using fetch with keepalive
                fetch('/api/cleanup-session', {
                    method: 'POST',
                    body: data,
                    keepalive: true
                }).catch(e => {
                    console.warn('Cleanup request failed:', e);
                });
            }
        } catch (error) {
            console.error('Error during cleanup:', error);
        }
    }
    
    // Clear files manually (for new chat button)
    async clearCurrentSessionFiles() {
        if (this.uploadedFiles.length === 0) return;
        
        try {
            const response = await fetch(`/api/files/${this.sessionId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                console.log('Session files cleared successfully');
            }
        } catch (error) {
            console.error('Error clearing session files:', error);
        }
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