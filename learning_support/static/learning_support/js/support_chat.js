
document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesContainer = document.getElementById('messages-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const voiceBtn = document.getElementById('voice-btn');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Get initial chat ID
    let currentChatId = messagesContainer.dataset.chatId || "";

    const scrollToBottom = () => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };

    // Scroll on load
    scrollToBottom();

    const addMessage = (text, sender) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender === 'user' ? 'user-message' : 'ai-message'}`;

        let contentHtml = `<div class="content">${text.replace(/\n/g, '<br>')}</div>`;

        if (sender === 'ai') {
            msgDiv.innerHTML = `<div class="avatar"><i class="ph ph-life-buoy"></i></div>${contentHtml}`;
        } else {
            msgDiv.innerHTML = `<div class="avatar"><i class="ph ph-user"></i></div>${contentHtml}`;
        }

        messagesContainer.insertBefore(msgDiv, loadingIndicator);
        scrollToBottom();
    };

    const sendMessage = async (text, type = 'text') => {
        if (!text) return;

        addMessage(text, 'user');
        chatInput.value = '';
        loadingIndicator.style.display = 'flex'; // Use flex to center if needed, or block
        scrollToBottom();

        try {
            const formData = new FormData();
            formData.append('message', text);
            formData.append('type', type);
            if (currentChatId) formData.append('chat_id', currentChatId);

            const response = await fetch('/support/api/chat/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: formData
            });

            loadingIndicator.style.display = 'none';

            // STREAMING LOGIC
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            // Create Placeholder for AI Message
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message ai-message';
            msgDiv.innerHTML = `<div class="avatar"><i class="ph ph-life-buoy"></i></div><div class="content"></div>`;
            messagesContainer.insertBefore(msgDiv, loadingIndicator);
            const contentDiv = msgDiv.querySelector('.content');

            let fullText = "";
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                let chunk = decoder.decode(value, { stream: true });

                // Check for Meta Packet (New Chat ID)
                // Assuming it comes as first line: {"type": "meta", "chat_id": "..."}
                if (chunk.includes('{"type": "meta"')) {
                    const lines = chunk.split('\n');
                    for (let line of lines) {
                        if (line.trim().startsWith('{"type": "meta"')) {
                            try {
                                const meta = JSON.parse(line);
                                if (meta.chat_id) {
                                    currentChatId = meta.chat_id;
                                    // Update URL without reload
                                    const newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + '?chat_id=' + currentChatId;
                                    window.history.pushState({ path: newUrl }, '', newUrl);
                                }
                            } catch (e) { }
                            // Remove meta line from chunk display
                            chunk = chunk.replace(line, "").trim();
                        }
                    }
                }

                fullText += chunk;
                contentDiv.innerHTML = fullText.replace(/\n/g, '<br>');
                scrollToBottom();

                // TTS Buffer logic for Voice Mode
                if (type === 'voice') {
                    buffer += chunk;
                    const sentenceMatch = buffer.match(/[.?!]\s/);
                    if (sentenceMatch) {
                        const sentence = buffer.substring(0, sentenceMatch.index + 1);
                        speakSentence(sentence);
                        buffer = buffer.substring(sentenceMatch.index + 1); // Keep remainder
                    }
                }
            }
            // Speak remaining buffer
            if (type === 'voice' && buffer.trim()) speakSentence(buffer);

        } catch (error) {
            loadingIndicator.style.display = 'none';
            addMessage("Error: " + error, 'ai');
        }
    };

    // --- Voice Logic ---
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'en-US';

    voiceBtn.addEventListener('click', () => {
        voiceBtn.classList.add('recording'); // Use class for styling
        voiceBtn.style.color = '#ef4444';
        chatInput.placeholder = "Listening...";
        recognition.start();
    });

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) sendMessage(transcript, 'voice');
    };

    recognition.onend = () => {
        voiceBtn.style.color = '';
        chatInput.placeholder = "Type your doubt here...";
    };

    // --- TTS Logic ---
    let ttsQueue = [];
    let isSpeaking = false;

    const speakSentence = (text) => {
        const cleanText = text.replace(/[*#_]/g, '').trim();
        if (!cleanText) return;
        ttsQueue.push(cleanText);
        processTTS();
    };

    const processTTS = () => {
        if (isSpeaking || ttsQueue.length === 0) return;
        isSpeaking = true;

        const utt = new SpeechSynthesisUtterance(ttsQueue.shift());
        utt.onend = () => { isSpeaking = false; processTTS(); };
        window.speechSynthesis.speak(utt);
    };

    // --- Event Listeners ---
    sendBtn.addEventListener('click', () => sendMessage(chatInput.value.trim()));
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage(chatInput.value.trim());
    });

    // Expose for buttons
    window.sendQuickText = (text) => sendMessage(text);
});
