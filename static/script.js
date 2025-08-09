document.addEventListener("DOMContentLoaded", () => {
  const chatMessages = document.getElementById("chatMessages")
  const userInput = document.getElementById("userInput")
  const sendButton = document.getElementById("sendButton")

  function escapeHtml(unsafe) {
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#039;")
  }

  function extractLinkAndText(rawText) {
    if (!rawText) return { cleanText: "", url: null }
    // Strip any HTML tags the model may have produced
    let text = String(rawText).replace(/<[^>]*>/g, "")

    // Prefer first markdown link URL
    let url = null
    const mdMatch = text.match(/\[[^\]]+\]\((https?:\/\/[^\s)]+)\)/)
    if (mdMatch) url = mdMatch[1]

    // If no markdown, find first bare URL
    if (!url) {
      const bareMatch = text.match(/(https?:\/\/[^\s<>'")]+)/)
      if (bareMatch) url = bareMatch[1]
    }

    // Remove all markdown links but keep labels
    text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_m, label) => label)
    // Remove all bare URLs
    text = text.replace(/(https?:\/\/[^\s<>'")]+)/g, "")

    // Clean up whitespace
    text = text.replace(/\s{2,}/g, " ").trim()

    // Trim trailing punctuation from captured URL
    if (url) {
      const m = url.match(/^(.*?)([\.,)\]]*)$/)
      url = m ? m[1] : url
    }
    return { cleanText: text, url }
  }

  function addMessage(content, isUser = false, questionText = null) {
    const messageDiv = document.createElement("div")
    messageDiv.classList.add("message", isUser ? "user" : "assistant")

    if (!isUser && questionText) {
      messageDiv.dataset.questionText = questionText
    }

    const messageContent = document.createElement("div")
    messageContent.classList.add("message-content")
    if (isUser) {
      messageContent.innerHTML = `<p>${escapeHtml(content)}</p>`
    } else {
      const { cleanText, url } = extractLinkAndText(content)
      const safe = escapeHtml(cleanText)
      const link = url ? ` <a class="know-more-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">know more</a>` : ""
      messageContent.innerHTML = `<p>${safe}${link}</p>`
    }
    messageDiv.appendChild(messageContent)

    if (!isUser) {
      const reactionButtons = document.createElement("div")
      reactionButtons.classList.add("reaction-buttons")
      reactionButtons.innerHTML = `
                <button class="like-btn" title="Like">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                    </svg>
                </button>
                <button class="dislike-btn" title="Dislike">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                    </svg>
                </button>
                <button class="copy-btn" title="Copy">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                </button>
            `
      messageDiv.appendChild(reactionButtons)
    }

    chatMessages.appendChild(messageDiv)
    chatMessages.scrollTop = chatMessages.scrollHeight
  }

  async function handleUserInput() {
    const message = userInput.value.trim()
    if (message) {
      addMessage(message, true)
      userInput.value = ""

      const typingDiv = document.createElement("div")
      typingDiv.classList.add("message", "assistant")
      typingDiv.innerHTML = '<div class="message-content"><p>Typing...</p></div>'
      chatMessages.appendChild(typingDiv)
      chatMessages.scrollTop = chatMessages.scrollHeight

      try {
        const response = await fetch("/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ message }),
        })

        if (!response.ok) {
          throw new Error("Failed to fetch response from the server.")
        }

        const data = await response.json()

        chatMessages.removeChild(typingDiv)

        addMessage(data.response, false, message)
      } catch (error) {
        chatMessages.removeChild(typingDiv)

        addMessage("Sorry, something went wrong. Please try again.", false)
        console.error(error)
      }
    }
  }

  async function handleReaction(event) {
    const button = event.target.closest("button")
    if (!button) return

    const message = button.closest(".message")
    const questionText = message.dataset.questionText

    if (button.classList.contains("like-btn")) {
      button.classList.toggle("liked")
      message.querySelector(".dislike-btn")?.classList.remove("disliked")
      if (button.classList.contains("liked") && questionText) {
        await sendFeedback(questionText, 1)
      }
    } else if (button.classList.contains("dislike-btn")) {
      button.classList.toggle("disliked")
      message.querySelector(".like-btn")?.classList.remove("liked")
      if (button.classList.contains("disliked") && questionText) {
        await sendFeedback(questionText, 0)
      }
    } else if (button.classList.contains("copy-btn")) {
      const messageContent = message.querySelector(".message-content p")
      if (messageContent) {
        navigator.clipboard
          .writeText(messageContent.textContent)
          .then(() => alert("Message copied to clipboard!"))
          .catch(() => alert("Failed to copy message."))
      }
    }
  }

  async function sendFeedback(questionText, feedback) {
    try {
      const response = await fetch("/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question_text: questionText, feedback }),
      })

      if (!response.ok) {
        throw new Error("Failed to record feedback.")
      }

      console.log("Feedback recorded successfully.")
    } catch (error) {
      console.error("Error recording feedback:", error)
    }
  }

  sendButton.addEventListener("click", handleUserInput)

  userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleUserInput()
    }
  })

  userInput.addEventListener("input", () => {
    userInput.style.height = "auto"
    userInput.style.height = userInput.scrollHeight + "px"
  })

  chatMessages.addEventListener("click", handleReaction)
})

