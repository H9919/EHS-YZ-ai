# routes/contractors.py - Enhanced contractor management
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify

contractors_bp = Blueprint("contractors", __name__)

@contractors_bp.route("/")
def contractors_list():
    """List all contractors"""
    contractors = load_contractors()
    contractor_list = sorted(contractors.values(), key=lambda x: x.get("created_date", 0), reverse=True)
    
    # Calculate statistics
    stats = {
        "total": len(contractor_list),
        "active": len([c for c in contractor_list if c.get("status") == "approved"]),
        "pending": len([c for c in contractor_list if c.get("status") == "pending_approval"]),
        "training_required": len([c for c in contractor_list if not c.get("safety_training_completed")])
    }
    
    return render_template("contractors_list.html", contractors=contractor_list, stats=stats)

@contractors_bp.route("/register", methods=["GET", "POST"])
def register_contractor():
    """Register new contractor"""
    if request.method == "GET":
        return render_template("contractor_register.html")
    
    contractor_data = {
        "id": str(int(time.time() * 1000)),
        "company_name": request.form.get("company_name"),
        "contact_person": request.form.get("contact_person"),
        "phone": request.form.get("phone"),
        "email": request.form.get("email"),
        "work_description": request.form.get("work_description"),
        "insurance_expiry": request.form.get("insurance_expiry"),
        "safety_training_completed": False,
        "status": "pending_approval",
        "created_date": time.time(),
        "requirements": {
            "insurance": request.files.get("insurance_file") is not None,
            "safety_training": False,
            "competency_verification": False,
            "site_orientation": False
        },
        "work_locations": request.form.getlist("work_locations"),
        "hazard_exposure": request.form.getlist("hazard_exposure")
    }
    
    save_contractor(contractor_data)
    flash("Contractor registration submitted. Safety orientation required before site access.", "info")
    return redirect(url_for("contractors.contractor_detail", contractor_id=contractor_data["id"]))

@contractors_bp.route("/<contractor_id>")
def contractor_detail(contractor_id):
    """View contractor details"""
    contractors = load_contractors()
    contractor = contractors.get(contractor_id)
    if not contractor:
        flash("Contractor not found", "error")
        return redirect(url_for("contractors.contractors_list"))
    return render_template("contractor_detail.html", contractor=contractor)

@contractors_bp.route("/visitors/checkin", methods=["GET", "POST"])
def visitor_checkin():
    """Visitor check-in system"""
    if request.method == "GET":
        return render_template("visitor_checkin.html")
    
    visitor_data = {
        "id": str(int(time.time() * 1000)),
        "name": request.form.get("name"),
        "company": request.form.get("company"),
        "purpose": request.form.get("purpose"),
        "host": request.form.get("host"),
        "areas_authorized": request.form.getlist("areas"),
        "safety_briefing_completed": request.form.get("safety_briefing") == "on",
        "checkin_time": time.time(),
        "status": "checked_in",
        "expected_duration": request.form.get("duration"),
        "emergency_contact": request.form.get("emergency_contact"),
        "has_ppe": request.form.get("has_ppe") == "on"
    }
    
    save_visitor(visitor_data)
    flash(f"Visitor {visitor_data['name']} checked in successfully", "success")
    return render_template("visitor_badge.html", visitor=visitor_data)

def save_contractor(contractor_data):
    """Save contractor data"""
    contractors = load_contractors()
    contractors[contractor_data["id"]] = contractor_data
    save_contractors(contractors)

def save_contractors(contractors):
    """Save contractors dictionary to file"""
    data_dir = Path("data")
    contractors_file = data_dir / "contractors.json"
    data_dir.mkdir(exist_ok=True)
    contractors_file.write_text(json.dumps(contractors, indent=2))

def load_contractors():
    """Load contractors from JSON file"""
    contractors_file = Path("data/contractors.json")
    if contractors_file.exists():
        try:
            return json.loads(contractors_file.read_text())
        except:
            return {}
    return {}

def save_visitor(visitor_data):
    """Save visitor data"""
    data_dir = Path("data")
    visitors_file = data_dir / "visitors.json"
    
    if visitors_file.exists():
        visitors = json.loads(visitors_file.read_text())
    else:
        visitors = {}
    
    visitors[visitor_data["id"]] = visitor_data
    
    data_dir.mkdir(exist_ok=True)
    visitors_file.write_text(json.dumps(visitors, indent=2))

def load_visitors():
    """Load visitors from JSON file"""
    visitors_file = Path("data/visitors.json")
    if visitors_file.exists():
        try:
            return json.loads(visitors_file.read_text())
        except:
            return {}
    return {}
