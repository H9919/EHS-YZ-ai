# routes/chatbot.py — AVOMO/OSHA-compliant Chat API + UI
from __future__ import annotations
from pathlib import Path
import json
import traceback

from flask import Blueprint, request, jsonify, render_template
from werkzeug.utils import secure_filename

# AVOMO-enhanced chatbot (guided OSHA/AVOMO flow + saving to incidents.json)
from services.enhanced_avomo_chatbot import create_avomo_chatbot
# 5-Whys manager used by the home dashboard buttons
from services.ehs_chatbot import five_whys_manager
# Safe upload helpers
from utils.uploads import is_allowed, save_upload

chatbot_bp = Blueprint("chatbot_bp", __name__, template_folder="../templates")

# --- Single, long-lived chatbot instance (persists across requests)
_BOT = create_avomo_chatbot()

# Where to keep temporary chat uploads
UPLOAD_DIR = Path("data/tmp/chat_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _get_user_id() -> str:
    # Keep it simple; your UI sends 'user_id'
    return (request.form.get("user_id") or request.json.get("user_id")  # type: ignore
            if request.is_json else request.form.get("user_id")) or "main_chat_user"


def _parse_context() -> dict:
    # UI sends 'context' (JSON string) – be resilient if absent/invalid
    raw = request.form.get("context")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _maybe_save_upload() -> dict | None:
    """Store a single optional file upload and return minimal metadata for the bot."""
    if "file" not in request.files:
        return None

    file = request.files["file"]
    if not file or not file.filename:
        return None

    # best-effort MIME (Render sometimes strips it)
    mimetype = file.mimetype or "application/octet-stream"
    fname = secure_filename(file.filename)

    if not is_allowed(fname, mimetype):
        raise ValueError("Unsupported file type. Allowed: images (png/jpg/gif), PDF, TXT")

    saved_path = save_upload(file, UPLOAD_DIR, fname)
    return {
        "filename": fname,
        "path": str(saved_path),
        "mimetype": mimetype,
        "size": saved_path.stat().st_size,
    }


# ---------- UI (optional dedicated page) ----------
@chatbot_bp.get("/chatbot")
def chatbot_page():
    """Dedicated full-screen chat page. The dashboard also chats via /chat."""
    return render_template("chatbot.html")


# ---------- Core chat endpoint used by both UIs ----------
@chatbot_bp.post("/chat")
def chat_api():
    """
    Accepts:
      - message (optional if sending only a file)
      - user_id (string)
      - context (JSON as string) — see enhanced_dashboard/chatbot UIs
      - file (optional: image/pdf/txt)
    """
    try:
        user_id = _get_user_id()
        message = (request.form.get("message") or "").strip()
        context = _parse_context()

        # Handle upload (optional)
        uploaded_file_info = None
        try:
            uploaded_file_info = _maybe_save_upload()
        except ValueError as ve:
            return jsonify({"ok": False, "error": str(ve)}), 400

        if uploaded_file_info:
            # Let the bot know there is an uploaded file
            context["uploaded_file"] = uploaded_file_info

        # If user sent only a file (no text), be helpful instead of failing
        if not message and uploaded_file_info:
            # If the bot is already running an AVOMO flow, simply acknowledge the attachment;
            # otherwise, the general bot will also see this via context.
            return jsonify({
                "ok": True,
                "type": "file_upload",
                "message": f"📎 **Attachment saved:** `{uploaded_file_info['filename']}` "
                           f"({uploaded_file_info['size']} bytes). "
                           "You can add a description, and I’ll extract any useful details to help fill the report.",
                "guidance": "If this is an incident report, describe what happened. "
                            "I’ll auto-suggest fields (time, location, body part, etc.) when I can.",
            })

        # Normal bot handling (AVOMO flows or general responses)
        response = _BOT.process_message(message, user_id=user_id, context=context)  # type: ignore
        # Always add ok flag for UI consistency
        if isinstance(response, dict) and "ok" not in response:
            response["ok"] = True
        return jsonify(response)

    except Exception as e:
        print("ERROR in /chat:", e, traceback.format_exc())
        return jsonify({
            "ok": False,
            "message": "Sorry, something went wrong while processing your message.",
            "error": str(e)
        }), 500


# ---------- Reset the chat session ----------
@chatbot_bp.post("/chat/reset")
def chat_reset():
    global _BOT
    _BOT = create_avomo_chatbot()
    return jsonify({"ok": True, "message": "🔄 Chat session reset. How can I help?"})


# ---------- 5-Whys API used by enhanced dashboard ----------
@chatbot_bp.post("/chat/five_whys/start")
def five_whys_start():
    problem = (request.form.get("problem") or "").strip()
    user_id = _get_user_id()
    if not problem:
        return jsonify({"ok": False, "error": "Please provide a problem statement."}), 400

    five_whys_manager.start(user_id, problem)
    return jsonify({
        "ok": True,
        "prompt": "Why did this happen? (Why 1)",
        "step": 1
    })


@chatbot_bp.post("/chat/five_whys/answer")
def five_whys_answer():
    ans = (request.form.get("answer") or "").strip()
    user_id = _get_user_id()
    complete_flag = (request.form.get("complete") or "").lower() == "true"

    sess = five_whys_manager.answer(user_id, ans)
    if not sess:
        return jsonify({"ok": False, "error": "No active 5-Whys session. Start one first."}), 400

    complete = five_whys_manager.is_complete(user_id) or complete_flag
    return jsonify({
        "ok": True,
        "complete": complete,
        "session": sess
    })
