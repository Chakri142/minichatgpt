document.addEventListener("DOMContentLoaded", () => {
    const chatBox = document.getElementById("chat-box");
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    
    let conversationHistory = ""; 

    // Helper function to add a message to the chat box
    function addMessage(message, sender) {
        const messageElement = document.createElement("div");
        messageElement.classList.add("message", `${sender}-message`);
        
        const pElement = document.createElement("p");
        pElement.textContent = message;
        messageElement.appendChild(pElement);
        
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Function to load and display history from DB
    async function loadHistory() {
        try {
            // Added 'credentials: "include"' to send the session cookie
            const response = await fetch("http://127.0.0.1:5000/get_history", {
                method: "GET",
                credentials: "include" 
            });
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            const data = await response.json();
            
            conversationHistory = data.history || ""; 
            chatBox.innerHTML = ""; // Clear default "Hello"

            // Parse and display the loaded history
            const turns = conversationHistory.split("\n");
            turns.forEach(turn => {
                if (turn.startsWith("User: ")) {
                    addMessage(turn.substring(6), "user");
                } else if (turn.startsWith("Bot: ")) {
                    addMessage(turn.substring(5), "bot");
                }
            });

        } catch (error) {
            console.error("Error loading history:", error);
            addMessage("Hello! I'm your AI assistant. How can I help?", "bot");
            conversationHistory = "Bot: Hello! I'm your AI assistant. How can I help?\n";
        }
    }

    // Handle form submission
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault(); 
        const userMessage = userInput.value.trim();
        if (userMessage === "") return;

        addMessage(userMessage, "user");
        userInput.value = "";

        try {
            // Added 'credentials: "include"' to send the session cookie
            const response = await fetch("http://127.0.0.1:5000/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include", 
                body: JSON.stringify({
                    message: userMessage,
                    history: conversationHistory 
                }),
            });

            if (!response.ok) {
                throw new Error("Network response was not ok");
            }

            const data = await response.json();
            addMessage(data.reply, "bot");
            conversationHistory = data.new_history;

        } catch (error)
            {
            console.error("Error:", error);
            addMessage("Sorry, something went wrong. Please try again.", "bot");
        }
    });

    // Load history when the page opens
    loadHistory();
});