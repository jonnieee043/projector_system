
const input = document.getElementById("user-input");
const chatBox = document.getElementById("chat-box");
const sendButton = document.getElementById("send-btn");
const typing = document.getElementById("typing");

let conversationHistory = [];

function displayMessage(message, sender) {
    const messageElement = document.createElement("div");

    messageElement.classList.add("message", sender);
    messageElement.textContent = message;

    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight;
}


async function sendMessage() {
    const message = input.value.trim();

    if (message === "" || sendButton.disabled) {
        return;
    }

    displayMessage(message, "user");

    input.value = "";
    sendButton.disabled = true;
    typing.hidden = false;

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message,
                history: conversationHistory
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Request failed.");
        }

        displayMessage(data.reply, "bot");

        conversationHistory.push(
            { role: "user", content: message },
            { role: "assistant", content: data.reply }
        );

        conversationHistory = conversationHistory.slice(-10);

    } catch (error) {
        displayMessage(
            error.message || "Unable to connect to the server.",
            "bot"
        );

    } finally {
        typing.hidden = true;
        sendButton.disabled = false;
        input.focus();
    }
}


sendButton.addEventListener("click", sendMessage);


input.addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});
