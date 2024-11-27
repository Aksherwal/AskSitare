document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');

    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', isUser ? 'user' : 'assistant');
        
        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');
        messageContent.innerHTML = `<p>${content}</p>`;
        messageDiv.appendChild(messageContent);

        // Add reaction buttons for assistant messages
        if (!isUser) {
            const reactionButtons = document.createElement('div');
            reactionButtons.classList.add('reaction-buttons');
            reactionButtons.innerHTML = `
                    <button class="like-btn" title="Like">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M2 20h2c.55 0 1-.45 1-1v-9c0-.55-.45-1-1-1H2v11zm19.83-7.12c.11-.25.17-.52.17-.8V11c0-1.1-.9-2-2-2h-5.5l.92-4.65c.05-.22.02-.46-.08-.66-.23-.45-.52-.86-.88-1.22L14 2 7.59 8.41C7.21 8.79 7 9.3 7 9.83v7.84C7 18.95 8.05 20 9.34 20h8.11c.7 0 1.36-.37 1.72-.97l2.66-6.15z"></path>
                    </svg>
                </button>
                <button class="dislike-btn" title="Dislike">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M22 4h-2c-.55 0-1 .45-1 1v9c0 .55.45 1 1 1h2V4zM2.17 11.12c-.11.25-.17.52-.17.8V13c0 1.1.9 2 2 2h5.5l-.92 4.65c-.05.22-.02.46.08.66.23.45.52.86.88 1.22L10 22l6.41-6.41c.38-.38.59-.89.59-1.42V6.34C17 5.05 15.95 4 14.66 4H6.55c-.7 0-1.36.37-1.72.97l-2.66 6.15z"></path>
                    </svg>
                </button>
                <button class="copy-btn" title="Copy">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2"></path>
                        <rect x="8" y="8" width="8" height="8" rx="2"></rect>
                    </svg>
                </button>

            `;
            messageDiv.appendChild(reactionButtons);
        }

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function simulateTyping(message) {
        return new Promise((resolve) => {
            const typingDiv = document.createElement('div');
            typingDiv.classList.add('message', 'assistant');
            typingDiv.innerHTML = '<div class="message-content"><p>Typing...</p></div>';
            chatMessages.appendChild(typingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            setTimeout(() => {
                chatMessages.removeChild(typingDiv);
                addMessage(message);
                resolve();
            }, 1500 + Math.random() * 1500);
        });
    }

    async function handleUserInput() {
        const message = userInput.value.trim();
        if (message) {
            addMessage(message, true);
            userInput.value = '';
            await simulateTyping('Thank you for your message. How else can I assist you today?');
        }
    }

    function handleReaction(event) {
        const button = event.target.closest('button');
        if (!button) return;

        const message = button.closest('.message');

        if (button.classList.contains('like-btn')) {
            button.classList.toggle('liked');
            message.querySelector('.dislike-btn')?.classList.remove('disliked');
        } else if (button.classList.contains('dislike-btn')) {
            button.classList.toggle('disliked');
            message.querySelector('.like-btn')?.classList.remove('liked');
        } else if (button.classList.contains('copy-btn')) {
            const messageContent = message.querySelector('.message-content p');
            if (messageContent) {
                navigator.clipboard.writeText(messageContent.textContent)
                    .then(() => alert('Message copied to clipboard!'))
                    .catch(() => alert('Failed to copy message.'));
            }
        }
    }

    sendButton.addEventListener('click', handleUserInput);

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleUserInput();
        }
    });

    userInput.addEventListener('input', () => {
        userInput.style.height = 'auto';
        userInput.style.height = userInput.scrollHeight + 'px';
    });

    chatMessages.addEventListener('click', handleReaction);
});
