
from flask import Flask, render_template, request, jsonify, redirect, url_for
from google import genai
from dotenv import load_dotenv
from pathlib import Path
import os
import re

from database import (
    initialize_database,
    save_chat,
    get_projectors,
    borrow_projector,
    return_projector,
    update_projector,
    delete_projector
)

load_dotenv(Path(__file__).resolve().parent / ".env")

app = Flask(__name__)

# Gemini connection
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing.")

client = genai.Client(api_key=api_key)


# Initialize MySQL database
try:
    initialize_database()
    print("MySQL database connected successfully.")

except Exception:
    app.logger.exception("Database initialization failed.")
    raise


SYSTEM_PROMPT = """
You are an AI Projector Troubleshooting Assistant.

Your responsibilities:
1. Answer projector-related questions.
2. Provide clear step-by-step tutorials.
3. Help users troubleshoot projector problems.
4. Explain projector settings and connections.
5. Use simple and understandable language.
6. Ask follow-up questions if the problem is unclear.
7. Do not invent device-specific instructions.
8. Refer users to the official manual when unsure.
9. Politely redirect unrelated questions.
10. Never instruct users to open a projector or touch
internal electrical components.

Use numbered steps when appropriate.
"""


def format_date(value):
    if not value:
        return "N/A"

    return value.strftime("%B %d, %Y")


def answer_inventory_question(message):

    question = message.lower()

    inventory_keywords = [
        "available",
        "availability",
        "borrowed",
        "borrowing",
        "borrow",
        "returned",
        "return date",
        "return schedule",
        "who borrowed",
        "who is borrowing",
        "how many",
        "inventory",
        "projector status",
        "projector schedule"
    ]

    # Avoid treating ordinary setup questions as inventory questions.
    is_inventory_question = any(
        keyword in question for keyword in inventory_keywords
    )

    if not is_inventory_question:
        return None

    projectors = get_projectors()

    number_match = re.search(
        r"projector\s*#?\s*(\d+)",
        question
    )

    if number_match:
        projector_id = int(number_match.group(1))

        projector = next(
            (p for p in projectors if p["id"] == projector_id),
            None
        )

        if not projector:
            return f"Projector {projector_id} was not found in the database."

        name = projector["name"]

        if projector["availability"] == "Available":
            return (
                f"{name} is currently Available.\n"
                f"Last recorded return date: "
                f"{format_date(projector['date_returned'])}."
            )

        return (
            f"{name} is currently Not Available.\n"
            f"Borrowed by: {projector['borrowed_by'] or 'N/A'}\n"
            f"Date borrowed: {format_date(projector['date_borrowed'])}\n"
            f"Date returned: Not yet returned."
        )

    available = [
        p for p in projectors
        if p["availability"] == "Available"
    ]

    borrowed = [
        p for p in projectors
        if p["availability"] == "Not Available"
    ]

    if "how many" in question:
        return (
            f"There are {len(available)} available projectors "
            f"and {len(borrowed)} borrowed projectors "
            f"out of {len(projectors)} total projectors."
        )

    if "who" in question:
        if not borrowed:
            return "There are currently no borrowed projectors."

        details = [
            f"{p['name']} - Borrowed by: {p['borrowed_by'] or 'Unknown'}"
            for p in borrowed
        ]

        return "Current borrowers:\n" + "\n".join(details)

    if any(word in question for word in [
        "available", "availability"
    ]):
        names = ", ".join(p["name"] for p in available)

        if not names:
            names = "None"

        return (
            f"Currently available projectors: {names}.\n"
            f"Total available: {len(available)}."
        )

    if any(word in question for word in [
        "borrowed", "borrowing", "schedule", "return"
    ]):
        if not borrowed:
            return "There are currently no borrowed projectors."

        details = []

        for p in borrowed:
            details.append(
                f"{p['name']} - "
                f"Borrowed by: {p['borrowed_by'] or 'Unknown'}, "
                f"Date borrowed: {format_date(p['date_borrowed'])}, "
                f"Return date: Not yet returned."
            )

        return "Current borrowing records:\n" + "\n".join(details)

    return (
        f"There are {len(available)} available and "
        f"{len(borrowed)} borrowed projectors."
    )


# HOMEPAGE - REDIRECT TO ADMIN PAGE
@app.route("/")
def home():
    return redirect(url_for("admin"))


# ADMIN PAGE
@app.route("/admin")
def admin():
    return render_template("admin.html")


# CHATBOT TEST PAGE
@app.route("/chatbot")
def chatbot():
    return render_template("index.html")


# GET PROJECTOR RECORDS
@app.route("/api/projectors", methods=["GET"])
def api_projectors():

    try:
        return jsonify(get_projectors())

    except Exception:
        app.logger.exception("Unable to load projectors.")

        return jsonify({
            "error": "Unable to load projector records."
        }), 500


# BORROW PROJECTOR
@app.route("/api/projectors/<int:projector_id>/borrow", methods=["POST"])
def api_borrow(projector_id):

    try:
        data = request.get_json(silent=True) or {}

        borrower = data.get("borrowed_by", "").strip()

        if not borrower:
            return jsonify({
                "error": "Please enter the borrower's name."
            }), 400

        if len(borrower) > 150:
            return jsonify({
                "error": "Borrower's name is too long."
            }), 400

        success = borrow_projector(projector_id, borrower)

        if not success:
            return jsonify({
                "error": "Projector not found or already borrowed."
            }), 409

        return jsonify({
            "message": "Projector successfully borrowed."
        })

    except Exception:
        app.logger.exception("Borrow error.")

        return jsonify({
            "error": "Unable to borrow projector."
        }), 500


# RETURN PROJECTOR
@app.route("/api/projectors/<int:projector_id>/return", methods=["POST"])
def api_return(projector_id):

    try:
        success = return_projector(projector_id)

        if not success:
            return jsonify({
                "error": "Projector not found or is not currently borrowed."
            }), 409

        return jsonify({
            "message": "Projector returned successfully. Date recorded."
        })

    except Exception:
        app.logger.exception("Return error.")

        return jsonify({
            "error": "Unable to return projector."
        }), 500


# EDIT PROJECTOR
@app.route("/api/projectors/<int:projector_id>/edit", methods=["PUT"])
def api_edit(projector_id):

    try:
        data = request.get_json(silent=True) or {}

        name = data.get("name", "").strip()

        if not name:
            return jsonify({
                "error": "Projector name is required."
            }), 400

        if len(name) > 100:
            return jsonify({
                "error": "Projector name is too long."
            }), 400

        success = update_projector(projector_id, name)

        if not success:
            return jsonify({
                "error": "Projector not found or no changes were made."
            }), 404

        return jsonify({
            "message": "Projector updated successfully."
        })

    except Exception:
        app.logger.exception("Edit error.")

        return jsonify({
            "error": "Unable to update projector."
        }), 500


# DELETE PROJECTOR
@app.route("/api/projectors/<int:projector_id>", methods=["DELETE"])
def api_delete(projector_id):

    try:
        success = delete_projector(projector_id)

        if not success:
            return jsonify({
                "error": "Projector not found."
            }), 404

        return jsonify({
            "message": "Projector deleted successfully."
        })

    except Exception:
        app.logger.exception("Delete error.")

        return jsonify({
            "error": "Unable to delete projector."
        }), 500


# CHATBOT API
@app.route("/chat", methods=["POST"])
def chat():

    try:
        data = request.get_json(silent=True) or {}

        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({
                "error": "Please enter a message."
            }), 400

        if len(user_message) > 4000:
            return jsonify({
                "error": "Message is too long."
            }), 400

        # Check the actual database before using Gemini.
        inventory_answer = answer_inventory_question(user_message)

        if inventory_answer is not None:
            save_chat(user_message, inventory_answer)

            return jsonify({
                "reply": inventory_answer
            })

        history = data.get("history", [])

        conversation = []

        if isinstance(history, list):

            for item in history[-10:]:

                if not isinstance(item, dict):
                    continue

                role = item.get("role")
                content = item.get("content")

                if role in ["user", "assistant"] and isinstance(content, str):
                    conversation.append(
                        f"{role}: {content[:4000]}"
                    )

        conversation.append(f"user: {user_message}")

        prompt = (
            SYSTEM_PROMPT
            + "\n\nConversation:\n"
            + "\n".join(conversation)
            + "\n\nassistant:"
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config={
                "http_options": {
                    "timeout": 60000
                }
            }
        )

        answer = response.text

        if not answer:
            answer = "Sorry, I could not generate an answer."

        save_chat(user_message, answer)

        return jsonify({
            "reply": answer
        })

    except Exception:
        app.logger.exception("Chatbot error.")

        return jsonify({
            "error": "Something went wrong. Please try again."
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
