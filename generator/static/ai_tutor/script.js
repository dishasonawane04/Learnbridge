
document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesContainer = document.getElementById('messages-container');
    const attachBtn = document.getElementById('attach-btn');
    const attachmentMenu = document.getElementById('attachment-menu');
    const fileInput = document.getElementById('fi-uploader');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const loadingIndicator = document.getElementById('loading-indicator');
    const welcomeScreen = document.getElementById('welcome-screen');

    let currentUploadType = 'text';
    let selectedFile = null;
    let currentChatId = null; // Track current DB Chat ID

    // Auto-scroll to bottom
    const scrollToBottom = () => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };

    // Toggle Attachment Menu
    attachBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        attachmentMenu.style.display = attachmentMenu.style.display === 'block' ? 'none' : 'block';
    });
    document.addEventListener('click', () => {
        attachmentMenu.style.display = 'none';
        // Also close ANY open chat option menus
        document.querySelectorAll('.opts-menu').forEach(m => m.style.display = 'none');
    });

    // Handle Attachment Uploads
    document.querySelectorAll('.attachment-menu button').forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.getAttribute('data-type');
            currentUploadType = type;
            if (type === 'audio') {
                attachmentMenu.style.display = 'none';
                startVoiceInput();
            } else {
                if (type === 'image') fileInput.accept = "image/*";
                else if (type === 'doc') fileInput.accept = ".pdf,.docx,.txt";
                fileInput.click();
                attachmentMenu.style.display = 'none';
            }
        });
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            selectedFile = fileInput.files[0];
            renderPreview(selectedFile);
        }
    });

    const renderPreview = (file) => {
        const previewContainer = document.getElementById('file-preview-container');
        previewContainer.style.display = 'flex';
        previewContainer.innerHTML = '';
        const item = document.createElement('div');
        item.className = 'preview-item';
        if (file.type.startsWith('image/')) {
            const url = URL.createObjectURL(file);
            item.innerHTML = `<img src="${url}"><button class="remove-file-btn" onclick="removeFile()">×</button>`;
        } else {
            item.innerHTML = `<div style="font-size:24px;"><i class="ph ph-file-text"></i></div><button class="remove-file-btn" onclick="removeFile()">×</button>`;
        }
        previewContainer.appendChild(item);
    };

    window.removeFile = () => {
        selectedFile = null;
        fileInput.value = '';
        document.getElementById('file-preview-container').style.display = 'none';
    };

    // --- Message Rendering ---
    const addMessage = (text, sender, type = 'text', fileData = null) => {
        // Hide welcome screen if first message
        if (welcomeScreen) welcomeScreen.style.display = 'none';

        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender === 'user' ? 'user-message' : 'ai-message'}`;

        let contentHtml = "";
        if (fileData) {
            if (fileData instanceof File) {
                // Preview for User Upload (Client side)
                if (type === 'image' || fileData.type.startsWith('image/')) {
                    const url = URL.createObjectURL(fileData);
                    contentHtml += `<div class="media-bubble"><img src="${url}"></div>`;
                } else {
                    contentHtml += `<div class="media-bubble"><i class="ph ph-file"></i> ${fileData.name}</div>`;
                }
            } else if (typeof fileData === 'string') {
                // URL from DB
                contentHtml += `<div class="media-bubble"><a href="${fileData}" target="_blank">View Attachment</a></div>`;
            }
        }

        if (text) {
            contentHtml += `<div class="content">${text.replace(/\n/g, '<br>')}</div>`;
        } else if (!fileData) {
            // Placeholder for streaming
            contentHtml += `<div class="content typing-cursor">...</div>`;
        }

        if (sender === 'ai') {
            msgDiv.innerHTML = `<div class="avatar"><i class="ph ph-robot"></i></div><div class="message-body">${contentHtml}</div>`;
        } else {
            msgDiv.innerHTML = `<div class="message-body">${contentHtml}</div>`;
        }

        messagesContainer.appendChild(msgDiv); // Append instead of insertBefore loading to keep loading at bottom
        scrollToBottom();
        return msgDiv; // Return reference for streaming updates
    };

    // --- MAIN SEND LOGIC ---
    const sendMessage = async (text, file = null, type = 'text') => {
        if (!text && !file) return;

        let backendType = type;
        if (file) {
            backendType = currentUploadType;
            if (backendType === 'text') backendType = 'image';
        }

        // Add User Message
        addMessage(text, 'user', backendType, file);

        // Clear Inputs
        chatInput.value = '';
        fileInput.value = '';
        window.removeFile();

        // Immediate "Thinking" Feedback (Optimized UX)
        // Instead of showing the bottom spinner wait, we create the AI bubble IMMEDIATELY
        const aiMsgDiv = addMessage("", 'ai');
        const intentContentDiv = aiMsgDiv.querySelector('.content');
        intentContentDiv.innerHTML = '<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>'; // Custom dot animation

        try {
            const formData = new FormData();
            formData.append('message', text);
            formData.append('type', backendType);
            if (file) formData.append('file', file);
            if (currentChatId) formData.append('chat_id', currentChatId);

            const response = await fetch('/ai/api/chat/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: formData
            });

            // Check for New Chat ID in headers
            const newId = response.headers.get('X-Chat-ID');
            if (newId && !currentChatId) {
                currentChatId = newId;
                addChatToSidebar(newId, text || "New Chat");
            }


            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullText = "";
            let buffer = "";

            intentContentDiv.innerHTML = ""; // Clear "..."

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                fullText += chunk;

                // Render Markdown (basic) + Line Breaks
                // For better markdown, we'd need a library like marked.js
                intentContentDiv.innerHTML = fullText.replace(/\n/g, '<br>');
                scrollToBottom();

                // Voice Logic
                if (backendType === 'voice') {
                    buffer += chunk;
                    const end = /[.?!]\s/;
                    let match = buffer.match(end);
                    while (match) {
                        const s = buffer.substring(0, match.index + 1);
                        speakSentence(s);
                        buffer = buffer.substring(match.index + 1);
                        match = buffer.match(end);
                    }
                }
            }
            if (backendType === 'voice' && buffer.trim()) speakSentence(buffer);

        } catch (error) {
            intentContentDiv.innerHTML = "Error: " + error;
        }
    };

    // --- Chat Management ---

    // Switch Chat
    window.loadChat = async (chatId) => {
        if (currentChatId === chatId) return;
        currentChatId = chatId;

        // Highlight active sidebar item
        document.querySelectorAll('.history-item').forEach(i => i.classList.remove('active'));
        const item = document.querySelector(`.history-item[data-id="${chatId}"]`);
        if (item) item.classList.add('active');

        // Fetch History
        messagesContainer.innerHTML = ''; // Clear current view
        // Show loading...
        loadingIndicator.style.display = 'flex';
        messagesContainer.appendChild(loadingIndicator); // move to bottom

        try {
            const res = await fetch(`/ai/api/chat/${chatId}/history/`);
            const data = await res.json();

            loadingIndicator.style.display = 'none';
            if (welcomeScreen) welcomeScreen.style.display = 'none';

            data.messages.forEach(msg => {
                const sender = msg.role === 'assistant' ? 'ai' : 'user';
                addMessage(msg.content, sender, msg.type, msg.file_url);
            });

        } catch (e) {
            console.error(e);
        }

    };

    window.startNewChat = async () => {
        try {
            const res = await fetch('/ai/new/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken }
            });
            const data = await res.json();
            if (data.status === 'success') {
                currentChatId = data.chat_id;
                messagesContainer.innerHTML = '';
                if (welcomeScreen) welcomeScreen.style.display = 'flex';
                // Reset Sidebar active
                document.querySelectorAll('.history-item').forEach(i => i.classList.remove('active'));

                // Add to sidebar
                addChatToSidebar(data.chat_id, "New Chat");
            }
        } catch (e) {
            console.error(e);
        }
    };

    const addChatToSidebar = (id, title) => {
        // Avoid duplicate entries
        if (document.querySelector(`.history-item[data-id="${id}"]`)) return;

        const recentSection = document.getElementById('recent-section');
        const noChatsMsg = document.getElementById('no-chats-msg');
        if (noChatsMsg) noChatsMsg.remove();

        const item = document.createElement('div');
        item.className = 'history-item active';
        item.setAttribute('data-id', id);
        item.onclick = () => loadChat(id);

        item.innerHTML = `
            <div class="chat-title">
                <i class="ph ph-chat-circle-text"></i>
                <span>${title}</span>
            </div>
            <div class="chat-options">
                <button class="opts-btn" onclick="toggleMenu(event, '${id}')">
                    <i class="ph ph-dots-three"></i>
                </button>
                <div class="opts-menu" id="menu-${id}">
                    <button onclick="renameChat(event, '${id}')"><i class="ph ph-pencil"></i> Rename</button>
                    <button onclick="pinChat(event, '${id}')"><i class="ph ph-push-pin"></i> Pin</button>
                    <button onclick="archiveChat(event, '${id}')"><i class="ph ph-archive"></i> Archive</button>
                    <button onclick="shareChat(event, '${id}')"><i class="ph ph-share-network"></i> Share</button>
                    <button onclick="deleteChat(event, '${id}')" class="delete-opt"><i class="ph ph-trash"></i> Delete</button>
                </div>
            </div>
        `;

        // Insert at top of recent section (after label)
        const label = recentSection.querySelector('.history-label');
        label.after(item);
    };



    window.toggleMenu = (e, chatId) => {
        e.stopPropagation();
        e.preventDefault(); // Safety
        console.log("Toggle Menu clicked for:", chatId);
        const menu = document.getElementById(`menu-${chatId}`);
        if (!menu) return;

        // Close others
        document.querySelectorAll('.opts-menu').forEach(m => {
            if (m !== menu) m.style.display = 'none';
        });
        menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
    };

    // Chat Search
    window.filterChats = () => {
        const input = document.getElementById('chat-search');
        const filter = input.value.toLowerCase();
        const items = document.querySelectorAll('.history-item');

        items.forEach(item => {
            const title = item.querySelector('.chat-title span').innerText.toLowerCase();
            if (title.includes(filter)) {
                item.style.display = "flex";
            } else {
                item.style.display = "none";
            }
        });
    };

    window.renameChat = async (e, chatId) => {
        e.stopPropagation();
        const newTitle = prompt("Enter new chat name:");
        if (newTitle) {
            const res = await fetch(`/ai/rename/${chatId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            });
            const data = await res.json();
            if (data.status === 'success') {
                const item = document.querySelector(`.history-item[data-id="${chatId}"]`);
                if (item) item.querySelector('.chat-title span').innerText = newTitle;
            }
        }
    };

    window.deleteChat = async (e, chatId) => {
        e.stopPropagation();
        if (confirm("Delete this chat permanently?")) {
            const res = await fetch(`/ai/delete/${chatId}/`, {
                method: 'POST', headers: { 'X-CSRFToken': csrfToken }
            });
            const data = await res.json();
            if (data.status === 'success') {
                const item = document.querySelector(`.history-item[data-id="${chatId}"]`);
                if (item) item.remove();
                if (currentChatId === chatId) startNewChat(); // Reset if deleted current
            }
        }
    };

    window.archiveChat = async (e, chatId) => {
        e.stopPropagation();
        const res = await fetch(`/ai/archive/${chatId}/`, {
            method: 'POST', headers: { 'X-CSRFToken': csrfToken }
        });
        const data = await res.json();
        if (data.status === 'success') {
            const item = document.querySelector(`.history-item[data-id="${chatId}"]`);
            if (item) item.remove();
            if (currentChatId === chatId) startNewChat();
        }
    };

    window.pinChat = async (e, chatId) => {
        e.stopPropagation();
        const res = await fetch(`/ai/pin/${chatId}/`, {
            method: 'POST', headers: { 'X-CSRFToken': csrfToken }
        });
        const data = await res.json();
        if (data.status === 'success') {
            // Simplify: Refresh sidebar or just reload for layout complex moves
            // But user said "no reload". Let's try to move it.
            const item = document.querySelector(`.history-item[data-id="${chatId}"]`);
            if (item) {
                const pinnedSection = document.getElementById('pinned-section');
                const recentSection = document.getElementById('recent-section');

                item.remove();
                if (data.is_pinned) {
                    pinnedSection.appendChild(item);
                    item.querySelector('.ph-chat-circle-text')?.classList.replace('ph-chat-circle-text', 'ph-push-pin');
                } else {
                    recentSection.appendChild(item);
                    item.querySelector('.ph-push-pin')?.classList.replace('ph-push-pin', 'ph-chat-circle-text');
                }
            }
        }
    };


    window.shareChat = async (e, chatId) => {
        e.stopPropagation();
        try {
            const res = await fetch(`/ai/api/chat/${chatId}/share-link/`);
            const data = await res.json();
            if (data.status === 'success') {
                await navigator.clipboard.writeText(data.url);
                alert("Chat link copied to clipboard!");
            }
        } catch (err) {
            console.error("Failed to share", err);
            alert("Could not copy link.");
        }
    };

    // Event Listeners
    sendBtn.addEventListener('click', () => sendMessage(chatInput.value.trim(), selectedFile));
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage(chatInput.value.trim(), selectedFile);
    });
    window.sendSuggestion = (text) => sendMessage(text);

    // --- Voice Utils (Browser APIs) ---
    const speakSentence = (text) => {
        if ('speechSynthesis' in window) {
            // Cancel any current speech
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = "en-IN";
            utterance.rate = 1;
            utterance.pitch = 1;

            // Visual Feedback: Speaking
            const statusDiv = document.getElementById('voice-status');
            if (statusDiv) statusDiv.innerText = "AI is speaking...";

            utterance.onend = () => {
                if (statusDiv) statusDiv.innerText = "";
            };

            window.speechSynthesis.speak(utterance);
        }
    };

    // --- Voice Input Logic (STT) ---
    window.startVoiceInput = () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert("Speech recognition is not supported in this browser.");
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = "en-IN";
        recognition.continuous = false;
        recognition.interimResults = false;

        // Visual Feedback: Listening
        const attachBtnIcon = attachBtn.querySelector('i');
        const originalIcon = attachBtnIcon.className;
        attachBtn.innerHTML = '<span class="typing-dots" style="color:red"><span>.</span><span>.</span><span>.</span></span>';

        // Show status message if possible or use a dedicated element
        let statusDiv = document.getElementById('voice-status');
        if (!statusDiv) {
            statusDiv = document.createElement('div');
            statusDiv.id = 'voice-status';
            statusDiv.style = "font-size: 0.8rem; color: var(--primary); margin-top: 0.5rem; text-align: center; font-weight: 500;";
            document.querySelector('.input-wrapper').appendChild(statusDiv);
        }
        statusDiv.innerText = "Listening...";

        recognition.onstart = () => {
            console.log("Speech recognition started");
        };

        recognition.onresult = async (event) => {
            const transcript = event.results[0][0].transcript;
            chatInput.value = transcript;
            statusDiv.innerText = "Thinking...";

            // Auto-send to AI
            await sendVoiceQuestion(transcript);
        };

        recognition.onerror = (event) => {
            console.error("Speech recognition error", event.error);
            attachBtn.innerHTML = `<i class="${originalIcon}"></i>`;

            if (event.error === 'no-speech') {
                statusDiv.innerText = "Could not hear you. Please speak clearly and try again.";
            } else if (event.error === 'not-allowed') {
                alert("Microphone permission denied. Please allow microphone access in your browser settings.");
                statusDiv.innerText = "";
            } else {
                statusDiv.innerText = "Connection Error. Please check your microphone.";
            }

            setTimeout(() => { statusDiv.innerText = ""; }, 4000);
        };

        recognition.onend = () => {
            attachBtn.innerHTML = `<i class="${originalIcon}"></i>`;
            if (statusDiv.innerText === "Listening...") {
                statusDiv.innerText = "";
            }
        };

        recognition.start();
    };

    const sendVoiceQuestion = async (text) => {
        if (!text) return;

        // Get course ID from URL
        let course_id = null;
        const pathParts = window.location.pathname.split('/');
        if (pathParts.includes('course')) {
            const idx = pathParts.indexOf('course');
            if (pathParts[idx + 1]) course_id = pathParts[idx + 1];
        }

        // Show User Message
        addMessage(text, 'user', 'text');

        // Show AI Message loading
        const aiMsgDiv = addMessage("", 'ai');
        const intentContentDiv = aiMsgDiv.querySelector('.content');
        intentContentDiv.innerHTML = '<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';

        try {
            const response = await fetch('/ai/ask_voice/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question: text,
                    course_id: course_id
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                intentContentDiv.innerHTML = data.answer.replace(/\n/g, '<br>');
                scrollToBottom();

                // Speak the answer
                speakSentence(data.answer);
            } else {
                intentContentDiv.innerText = "Error: " + (data.error || "Unknown error");
            }
        } catch (err) {
            console.error(err);
            intentContentDiv.innerText = "Connection Error. Please ensure Ollama is running.";
        }
    };
});
