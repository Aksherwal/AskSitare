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
            await simulateTyping('Thank you for your message. As an AI assistant, I am here to help answer your questions and provide information on a wide range of topics. How else can I assist you today?');
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
});

