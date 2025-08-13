# -*- coding: utf-8 -*-
# =============================
# services/enhanced_avomo_chatbot.py
# =============================
# AVOMO-specific chatbot with file-backed sessions so it survives multi-process deployments (e.g., Render)

import json
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional

from .avomo_incident_structure import AVOMOIncidentStructure, AVOMOIntentClassifier
from .ehs_chatbot import SmartEHSChatbot

SESS_DIR = Path("data/tmp/sessions")
SESS_DIR.mkdir(parents=True, exist_ok=True)


class AVOMOIncidentChatbot(SmartEHSChatbot):
    """Enhanced chatbot with AVOMO-specific incident reporting (OSHA-compliant).
    Uses file-backed sessions keyed by user_id so flow persists across workers.
    """

    def __init__(self):
        super().__init__()
        self.avomo_structure = AVOMOIncidentStructure()
        self.avomo_classifier = AVOMOIntentClassifier()

    # -------- session helpers --------
    def _sess_path(self, user_id: str) -> Path:
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", user_id or "anon")
        return SESS_DIR / f"{safe}.json"

    def _load_session(self, user_id: str) -> Dict[str, Any]:
        p = self._sess_path(user_id)
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                return {}
        return {}

    def _save_session(self, user_id: str, data: Dict[str, Any]):
        p = self._sess_path(user_id)
        p.write_text(json.dumps(data, ensure_ascii=False))

    def _clear_session(self, user_id: str):
        p = self._sess_path(user_id)
        if p.exists():
            p.unlink()

    # -------- main entry --------
    def process_message(self, user_message: str, user_id: Optional[str] = None, context: Optional[Dict] = None) -> Dict:
        user_id = user_id or (context or {}).get("user_id") or "anon"
        msg = (user_message or "").strip()
        sess = self._load_session(user_id)

        # New incident request?
        if self._is_incident_reporting_request(msg):
            return self._start_avomo_incident_reporting(msg, user_id)

        # In-progress AVOMO flow?
        if sess.get("mode") == "avomo" and sess.get("data"):
            return self._continue_avomo_incident_reporting(msg, user_id)

        # otherwise fall back to general bot
        return super().process_message(msg, user_id, context)

    def _is_incident_reporting_request(self, message: str) -> bool:
        mk = message.lower()
        triggers = [
            "report incident",
            "incident report",
            "report a workplace incident",
            "i need to report",
            "accident",
            "injury",
            "collision",
            "spill",
            "near miss",
            "safety concern",
        ]
        return any(t in mk for t in triggers)

    # -------- start flow --------
    def _start_avomo_incident_reporting(self, message: str, user_id: str) -> Dict:
        # Classify to one of the AVOMO event types
        incident_type, conf, extracted_info = self.avomo_classifier.classify_avomo_incident_type(message)

        data = {
            "user_id": user_id,
            "incident_type": incident_type,
            "initial_description": message,
            "extracted_info": extracted_info,
            "collected_fields": {},
            "current_field_index": 0,
            "required_fields": list(self.avomo_structure.event_types[incident_type]["required_fields"]),
            "start_time": time.time(),
        }
        sess = {"mode": "avomo", "data": data}
        self._save_session(user_id, sess)

        # Severe event check (lightweight)
        is_severe, severe_type = self.avomo_structure.validate_severe_event({"event_type": incident_type})

        prefix = ""
        if is_severe:
            lines = [
                "🚨 **SEVERE EVENT DETECTED** 🚨",
                f"Type: **{severe_type}**",
                "**IMMEDIATE ACTIONS**: If anyone needs medical attention call 911; notify supervisor; preserve the scene if safe."
            ]
            prefix = "\n\n".join(lines) + "\n\n"

        q = self._get_current_question(data)
        return {
            "ok": True,
            "type": "avomo_incident_start",
            "incident_type": incident_type,
            "severe_event": bool(is_severe),
            "message": (
                prefix
                + f"I'll help you report this **{self.avomo_structure.event_types[incident_type]['name']}**.\n\n"
                + f"{self.avomo_structure.event_types[incident_type]['description']}\n\n"
                + f"**Question 1 of {len(data['required_fields'])}:** {q}"
            ),
            "quick_replies": self._get_quick_replies_for_field(data, data["required_fields"][0]),
        }

    # -------- continue flow --------
    def _continue_avomo_incident_reporting(self, message: str, user_id: str) -> Dict:
        sess = self._load_session(user_id)
        data = sess.get("data", {})
        if not data:
            return {"ok": False, "message": "No active incident session. Say 'report an incident' to start."}

        field = self._current_field(data)
        if not field:
            return self._complete_avomo(user_id)

        # Validate
        v = self._validate_field_response(field, message)
        if not v["valid"]:
            return {
                "ok": False,
                "type": "avomo_incident_retry",
                "message": f"❌ {v['error']}\n\n**Please re-enter:** {self._get_current_question(data)}",
                "field": field,
                "quick_replies": self._get_quick_replies_for_field(data, field),
            }

        # Save answer
        data["collected_fields"][field] = message.strip()
        data["current_field_index"] += 1
        sess["data"] = data
        self._save_session(user_id, sess)

        # Next or complete
        if data["current_field_index"] < len(data["required_fields"]):
            nxt_field = self._current_field(data)
            q = self._get_current_question(data)
            prog = data["current_field_index"] + 1
            total = len(data["required_fields"])
            return {
                "ok": True,
                "type": "avomo_incident_continue",
                "message": f"✅ **Recorded**\n\n**Question {prog} of {total}:** {q}",
                "field": nxt_field,
                "progress": {"current": prog, "total": total, "percentage": int((prog / total) * 100)},
                "quick_replies": self._get_quick_replies_for_field(data, nxt_field),
            }
        else:
            return self._complete_avomo(user_id)

    # -------- helpers --------
    def _current_field(self, data: Dict[str, Any]) -> str:
        i = data.get("current_field_index", 0)
        req = data.get("required_fields", [])
        return req[i] if i < len(req) else ""

    def _get_current_question(self, data: Dict[str, Any]) -> str:
        f = self._current_field(data)
        if not f:
            return ""
        return self.avomo_structure.get_smart_follow_up_question(data["incident_type"], data, f)

    def _get_quick_replies_for_field(self, data: Dict[str, Any], field: str):
        return self.avomo_structure.get_quick_replies(field)

    def _validate_field_response(self, field: str, response: str) -> Dict[str, Any]:
        resp = (response or "").strip()
        if len(resp) < 2:
            return {"valid": False, "error": "Please provide more detail."}
        rules = self.avomo_structure.get_validation_rules()
        if field in rules:
            rule = rules[field]
            if not re.match(rule["pattern"], resp):
                return {"valid": False, "error": rule["error"]}
        if field == "site":
            sites = [s.lower() for s in self.avomo_structure.avomo_sites.values()]
            if resp.lower() not in sites:
                return {
                    "valid": False,
                    "error": f"Please choose one of: {', '.join(self.avomo_structure.avomo_sites.values())}",
                }
        return {"valid": True}

    def _complete_avomo(self, user_id: str) -> Dict:
        sess = self._load_session(user_id)
        data = sess.get("data", {})
        payload = {
            "schema": "AVOMO-OSHA",
            "incident_type": data.get("incident_type"),
            "initial_description": data.get("initial_description"),
            "fields": data.get("collected_fields", {}),
            "started_at": data.get("start_time"),
        }
        # Append to storage
        out = Path("data/avomo_incidents.json")
        existing = []
        if out.exists():
            try:
                existing = json.loads(out.read_text())
            except Exception:
                existing = []
        existing.append(payload)
        out.write_text(json.dumps(existing, ensure_ascii=False, indent=2))

        # Clear session
        self._clear_session(user_id)

        return {
            "ok": True,
            "type": "avomo_incident_complete",
            "message": (
                "✅ **Incident Report Completed** (AVOMO/OSHA)\n\n"
                f"Type: {self.avomo_structure.event_types[payload['incident_type']]['name']}\n"
                "A formal record has been saved. You can download a PDF from the incidents page."
            ),
            "record": payload,
        }


def create_avomo_chatbot():
    return AVOMOIncidentChatbot()
