# routes/audits.py - Enhanced audit management
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify

audits_bp = Blueprint("audits", __name__)

@audits_bp.route("/")
def audits_list():
    """List all audits"""
    audits = load_audits()
    audit_list = sorted(audits.values(), key=lambda x: x.get("created_date", 0), reverse=True)
    
    # Calculate statistics
    stats = {
        "total": len(audit_list),
        "scheduled": len([a for a in audit_list if a.get("status") == "scheduled"]),
        "completed": len([a for a in audit_list if a.get("status") == "completed"]),
        "in_progress": len([a for a in audit_list if a.get("status") == "in_progress"]),
        "avg_score": calculate_average_score(audit_list)
    }
    
    return render_template("audits_list.html", audits=audit_list, stats=stats)

@audits_bp.route("/new", methods=["GET", "POST"])
def new_audit():
    """Create new audit"""
    if request.method == "GET":
        audit_templates = get_audit_templates()
        return render_template("audit_new.html", templates=audit_templates)
    
    audit_data = {
        "id": str(int(time.time() * 1000)),
        "title": request.form.get("title"),
        "type": request.form.get("type"),
        "template": request.form.get("template"),
        "auditor": request.form.get("auditor"),
        "location": request.form.get("location"),
        "scheduled_date": request.form.get("scheduled_date"),
        "status": "scheduled",
        "created_date": time.time(),
        "checklist_items": get_checklist_for_template(request.form.get("template")),
        "findings": [],
        "score": 0
    }
    
    save_audit(audit_data)
    flash(f"Audit {audit_data['id'][:8]} scheduled successfully", "success")
    return redirect(url_for("audits.audit_detail", audit_id=audit_data["id"]))

@audits_bp.route("/<audit_id>")
def audit_detail(audit_id):
    """View audit details"""
    audits = load_audits()
    audit = audits.get(audit_id)
    if not audit:
        flash("Audit not found", "error")
        return redirect(url_for("audits.audits_list"))
    return render_template("audit_detail.html", audit=audit)

@audits_bp.route("/<audit_id>/conduct", methods=["GET", "POST"])
def conduct_audit(audit_id):
    """Conduct audit"""
    audits = load_audits()
    audit = audits.get(audit_id)
    
    if not audit:
        flash("Audit not found", "error")
        return redirect(url_for("audits.audits_list"))
    
    if request.method == "GET":
        return render_template("audit_conduct.html", audit=audit)
    
    # Process audit responses
    responses = {}
    findings = []
    total_score = 0
    max_score = 0
    
    for item in audit["checklist_items"]:
        response = request.form.get(f"item_{item['id']}")
        responses[item["id"]] = response
        
        if response == "yes":
            total_score += item.get("points", 1)
        elif response == "no":
            finding = {
                "item": item["question"],
                "severity": request.form.get(f"severity_{item['id']}", "medium"),
                "action_required": request.form.get(f"action_{item['id']}", ""),
                "photo": request.form.get(f"photo_{item['id']}", "")
            }
            findings.append(finding)
        
        max_score += item.get("points", 1)
    
    # Update audit
    audit["status"] = "completed"
    audit["completed_date"] = time.time()
    audit["responses"] = responses
    audit["findings"] = findings
    audit["score"] = round((total_score / max_score) * 100) if max_score > 0 else 0
    audit["completion_notes"] = request.form.get("completion_notes", "")
    
    audits[audit_id] = audit
    save_audits(audits)
    
    # Auto-generate CAPAs for high severity findings
    if findings:
        auto_generate_capas_from_audit(audit_id, findings)
    
    flash(f"Audit completed with score: {audit['score']}%. {len(findings)} findings identified.", "info")
    return redirect(url_for("audits.audit_detail", audit_id=audit_id))

def auto_generate_capas_from_audit(audit_id, findings):
    """Auto-generate CAPAs for audit findings"""
    try:
        from services.capa_manager import CAPAManager
        capa_manager = CAPAManager()
        
        for finding in findings:
            if finding["severity"] in ["high", "critical"]:
                capa_data = {
                    "title": f"Address audit finding: {finding['item'][:50]}...",
                    "description": f"Audit Finding: {finding['item']}\nAction Required: {finding['action_required']}",
                    "type": "corrective",
                    "source": "audit",
                    "source_id": audit_id,
                    "priority": "high" if finding["severity"] == "critical" else "medium",
                    "assignee": "TBD",
                    "due_date": (datetime.now() + timedelta(days=30)).isoformat()[:10]
                }
                capa_manager.create_capa(capa_data)
    except ImportError:
        pass  # CAPA manager not available

def get_audit_templates():
    """Get available audit templates"""
    return [
        {"id": "safety_walk", "name": "Safety Walk-through", "description": "General safety inspection"},
        {"id": "chemical_audit", "name": "Chemical Management Audit", "description": "Chemical storage and handling"},
        {"id": "equipment_check", "name": "Equipment Safety Check", "description": "Equipment and machinery safety"},
        {"id": "emergency_prep", "name": "Emergency Preparedness", "description": "Emergency procedures and equipment"},
        {"id": "contractor_safety", "name": "Contractor Safety Audit", "description": "Contractor compliance verification"},
        {"id": "environmental", "name": "Environmental Compliance", "description": "Environmental regulations check"}
    ]

def get_checklist_for_template(template_id):
    """Get checklist items for a specific template"""
    checklists = {
        "safety_walk": [
            {"id": "sw_1", "question": "Are all walkways clear of obstacles?", "points": 2, "category": "housekeeping"},
            {"id": "sw_2", "question": "Are emergency exits clearly marked and unobstructed?", "points": 3, "category": "emergency"},
            {"id": "sw_3", "question": "Are all required safety signs posted and visible?", "points": 2, "category": "signage"},
            {"id": "sw_4", "question": "Is personal protective equipment available and in good condition?", "points": 3, "category": "ppe"},
            {"id": "sw_5", "question": "Are spill kits accessible and properly stocked?", "points": 2, "category": "emergency"}
        ],
        "chemical_audit": [
            {"id": "ca_1", "question": "Are all chemicals properly labeled with hazard information?", "points": 3, "category": "labeling"},
            {"id": "ca_2", "question": "Are SDS readily accessible for all chemicals on site?", "points": 3, "category": "documentation"},
            {"id": "ca_3", "question": "Are incompatible chemicals stored separately?", "points": 4, "category": "storage"},
            {"id": "ca_4", "question": "Are secondary containment systems in place and functional?", "points": 3, "category": "containment"},
            {"id": "ca_5", "question": "Is chemical inventory accurate and up to date?", "points": 2, "category": "inventory"}
        ]
    }
    return checklists.get(template_id, [])

def calculate_average_score(audits):
    """Calculate average audit score"""
    completed_audits = [a for a in audits if a.get("status") == "completed" and a.get("score")]
    if not completed_audits:
        return 0
    return round(sum(a["score"] for a in completed_audits) / len(completed_audits), 1)

def save_audit(audit_data):
    """Save audit to JSON file"""
    audits = load_audits()
    audits[audit_data["id"]] = audit_data
    save_audits(audits)

def save_audits(audits):
    """Save audits dictionary to file"""
    data_dir = Path("data")
    audits_file = data_dir / "audits.json"
    data_dir.mkdir(exist_ok=True)
    audits_file.write_text(json.dumps(audits, indent=2))

def load_audits():
    """Load audits from JSON file"""
    audits_file = Path("data/audits.json")
    if audits_file.exists():
        try:
            return json.loads(audits_file.read_text())
        except:
            return {}
    return {}
