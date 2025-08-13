# =============================
# services/avomo_incident_structure.py
# =============================
# AVOMO Incident Reporting Structure based on the OSHA-compliant form
# (Updated: stronger Injury/Illness detection and clarified property-damage keywords)

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

class AVOMOIncidentStructure:
    """AVOMO-specific incident reporting structure following OSHA requirements"""
    
    def __init__(self):
        # AVOMO Sites mapping (sample — extend as needed)
        self.avomo_sites = {
            "austin_stassney": "Austin Stassney",
            "atlanta_plymouth": "Atlanta Plymouth", 
            "atlanta_manheim": "Atlanta Manheim"
        }
        
        # Severe event criteria (truncated for brevity — keep your original list if longer)
        self.severe_event_criteria = {
            "av_collision_emergency": "AV collision resulting in serious injury or significant property damage",
            "fatality": "Fatality or life-threatening injury",
        }
        
        # Event types and required fields — keep your original long list if present; this is representative
        self.event_types: Dict[str, Dict] = {
            "safety_concern": {
                "name": "Safety Concern",
                "description": "You noticed something unsafe or unusual, but no one was hurt and nothing was damaged",
                "required_fields": ["safety_concern_description", "safety_concern_corrective_action"]
            },
            "injury_illness": {
                "name": "Injury/Illness", 
                "description": "Someone got hurt or felt sick while working",
                # Keep your full OSHA/AVOMO set; representative subset shown here
                "required_fields": [
                    "event_date", "event_time", "site", "exact_location",
                    "injured_employee_name", "injured_employee_job_title", "employee_status",
                    "injury_illness_description", "injury_illness_type", "affected_body_parts",
                    "injury_illness_immediate_action", "ppe_in_use", "medical_treatment_level",
                    "supervisor_name", "date_supervisor_notified", "time_supervisor_notified",
                    "enablon_report_submitted"
                ]
            },
            "property_damage": {
                "name": "Property Damage",
                "description": "Something (equipment/facility/tool/vehicle) got damaged, broken, or lost",
                "required_fields": [
                    "event_date", "event_time", "site", "exact_location",
                    "property_damage_description", "approximate_total_cost", 
                    "property_damage_immediate_action", "enablon_report_submitted"
                ]
            },
            "vehicle_collision": {
                "name": "Vehicle Collision",
                "description": "Collision involving AV or yard vehicle",
                "required_fields": [
                    "event_date", "event_time", "site", "exact_location",
                    "vehicles_involved", "collision_description", "injuries_reported",
                    "law_enforcement_contacted", "enablon_report_submitted"
                ]
            },
            "environmental": {
                "name": "Environmental Event",
                "description": "Spill, leak, or environmental release",
                "required_fields": [
                    "event_date", "event_time", "site", "exact_location",
                    "substance_name", "estimated_volume", "containment_actions", "agency_notified",
                    "enablon_report_submitted"
                ]
            },
            "near_miss": {
                "name": "Near Miss",
                "description": "Something almost went wrong; no injury/damage but credible risk",
                "required_fields": [
                    "event_date", "event_time", "site", "exact_location",
                    "near_miss_type", "near_miss_description", "near_miss_corrective_action",
                    "enablon_report_submitted"
                ]
            }
        }

    # ------------------
    # Validation & prompts (representative; keep your originals if more complete)
    # ------------------
    def get_validation_rules(self) -> Dict[str, Dict[str, str]]:
        return {
            "event_date": {"pattern": r"^\d{4}-\d{2}-\d{2}$", "error": "Use YYYY-MM-DD."},
            "event_time": {"pattern": r"^\d{2}:\d{2}$", "error": "Use HH:MM in 24h."},
            "injured_employee_phone": {"pattern": r"^[0-9\-\+\s\(\)]{7,}$", "error": "Enter a valid phone number."},
            "approximate_total_cost": {"pattern": r"^\$?\d+(,\d{3})*(\.\d{2})?$", "error": "Enter a number like 1000 or 1,000.00."}
        }

    def get_field_questions(self) -> Dict[str, str]:
        return {
            "event_date": "What is the event date? (YYYY-MM-DD)",
            "event_time": "What time did it happen? (HH:MM 24h)",
            "site": f"Which site? ({', '.join(self.avomo_sites.values())})",
            "exact_location": "Where exactly at the site? (building/room/area)",
            "injured_employee_name": "What is the injured employee's full name?",
            "injured_employee_job_title": "Their job title?",
            "employee_status": "Employee status? (Full-time, Part-time, Contractor)",
            "injury_illness_description": "Describe how the injury/illness occurred.",
            "injury_illness_type": "Select the injury/illness type (e.g., Fracture, Laceration, Burn, Strain)",
            "affected_body_parts": "Which body parts were affected?",
            "injury_illness_immediate_action": "What immediate actions were taken?",
            "ppe_in_use": "Was PPE worn? If yes, which?",
            "medical_treatment_level": "What treatment level? (First aid, Clinic, Hospitalization)",
            "supervisor_name": "Who is the supervisor?",
            "date_supervisor_notified": "When was the supervisor notified? (YYYY-MM-DD)",
            "time_supervisor_notified": "What time was the supervisor notified? (HH:MM)",
            "enablon_report_submitted": "Has the Enablon report been submitted? (Yes/No)",
            "property_damage_description": "Describe the property damage and cause.",
            "approximate_total_cost": "Approximate total cost?",
            "property_damage_immediate_action": "What immediate actions were taken?",
            "vehicles_involved": "List vehicles involved.",
            "collision_description": "Describe the collision events.",
            "injuries_reported": "Any injuries reported? If yes, details.",
            "law_enforcement_contacted": "Was law enforcement contacted? (Yes/No)",
            "substance_name": "What substance was released?",
            "estimated_volume": "Estimated volume released?",
            "containment_actions": "What containment/cleanup actions were taken?",
            "agency_notified": "Any agency notified? (EPA/State/Local)"
        }

    def get_quick_replies(self, field: str) -> List[str]:
        if field == "site":
            return list(self.avomo_sites.values())
        if field == "employee_status":
            return ["Full-time", "Part-time", "Contractor"]
        if field == "enablon_report_submitted":
            return ["Yes", "No"]
        if field == "medical_treatment_level":
            return ["First aid", "Clinic", "Hospitalization"]
        return []

    def get_smart_follow_up_question(self, event_type: str, collected_data: Dict, current_field: str) -> str:
        base = self.get_field_questions().get(current_field, f"Please provide {current_field.replace('_',' ')}")
        extracted = collected_data.get("extracted_info", {})
        if current_field == "event_time" and extracted.get("estimated_time"):
            base += f" (You mentioned '{extracted['estimated_time']}' — confirm or provide exact time)"
        if current_field == "exact_location" and extracted.get("estimated_location"):
            base += f" (I noticed '{extracted['estimated_location']}')"
        if current_field == "affected_body_parts" and extracted.get("likely_body_part"):
            base += f" (Likely body part: {extracted['likely_body_part']})"
        return base

    def validate_severe_event(self, info: Dict) -> Tuple[bool, Optional[str]]:
        # Simple stub; keep your richer logic
        et = info.get("event_type", "")
        if et == "vehicle_collision":
            return True, "av_collision_emergency"
        return False, None

# ----------------------
# Intent classifier (improved)
# ----------------------
class AVOMOIntentClassifier:
    """Enhanced intent classifier for AVOMO-specific incident types"""
    
    def __init__(self):
        self.avomo_structure = AVOMOIncidentStructure()
    
    def classify_avomo_incident_type(self, description: str) -> Tuple[str, float, Dict]:
        """Classify incident type based on AVOMO categories"""
        desc_lower = description.lower()
        scores = {}
        
        # Stronger injury detection; avoid misrouting "broke/broken" to property damage
        injury_keywords = [
            "injury", "injured", "hurt", "pain", "medical", "sick", "illness",
            "fracture", "fractured", "broke", "broken bone", "sprain", "strain",
            "dislocation", "laceration", "cut", "burn", "shock", "amputation",
            "hand", "finger", "arm", "wrist", "leg", "ankle", "foot", "back"
        ]
        property_keywords = [
            "property damage", "equipment damage", "tool damage", "machine damage",
            "asset damage", "facility damage", "window", "door", "roof", "wall",
            "leaking pipe", "broken equipment", "damaged equipment"
        ]
        event_type_keywords = {
            "safety_concern": ["unsafe", "concern", "observation", "hazard", "risk", "dangerous"],
            "injury_illness": injury_keywords,
            "property_damage": property_keywords,
            "security_concern": ["security", "theft", "unauthorized", "suspicious", "trespassing"],
            "vehicle_collision": ["collision", "crash", "hit", "accident", "vehicle", "av"],
            "environmental": ["spill", "leak", "chemical", "environmental", "contamination"],
            "depot_event": ["outage", "emergency", "site-wide", "depot", "system"],
            "near_miss": ["near miss", "almost", "close call", "could have", "nearly"]
        }
        
        for event_type, keywords in event_type_keywords.items():
            score = 0
            for kw in keywords:
                if kw in desc_lower:
                    # Heavier weight for exact injury terms to win over generic "broken"
                    if event_type == "injury_illness" and kw in ("fracture", "fractured", "broke", "broken bone"):
                        score += 2
                    else:
                        score += 1
            if score > 0:
                # Normalize by len but keep some headroom
                scores[event_type] = score / max(6, len(keywords))
        
        if not scores:
            return "safety_concern", 0.5, {}
        best_type = max(scores, key=scores.get)
        confidence = min(0.97, scores[best_type] + 0.25)
        
        # Extract a bit of helpful info
        extracted_info = {}
        if any(x in desc_lower for x in ["hand", "wrist", "arm", "finger"]):
            extracted_info["likely_body_part"] = "upper limb"
        time_match = re.search(r"(\d{1,2}:\d{2}\s?(?:am|pm)?)", desc_lower)
        if time_match:
            extracted_info["estimated_time"] = time_match.group(1)
        # naive location nudge
        if "garage" in desc_lower:
            extracted_info["estimated_location"] = "garage"
        
        return best_type, confidence, extracted_info
