# services/avomo_incident_structure.py - AVOMO Compliant Incident Reporting
"""
AVOMO Incident Reporting Structure based on the OSHA-compliant form
This module defines the exact fields, validation, and workflow for AVOMO incident reporting
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

class AVOMOIncidentStructure:
    """AVOMO-specific incident reporting structure following OSHA requirements"""
    
    def __init__(self):
        # AVOMO Sites mapping
        self.avomo_sites = {
            "austin_stassney": "Austin Stassney",
            "atlanta_plymouth": "Atlanta Plymouth", 
            "atlanta_manheim": "Atlanta Manheim"
        }
        
        # Severe event criteria as defined in AVOMO form
        self.severe_event_criteria = {
            "av_collision_emergency": "AV collision resulting in calling emergency services, internal/frame damage to the vehicle, or injury to employees, vendors, or vulnerable road users",
            "fatality_hospitalization": "Fatality/Hospitalization/Amputation/Loss of an Eye or Life-Threatening",
            "site_emergency_911": "Site-wide emergency that requires calling 911",
            "security_breach": "Physical security or cybersecurity breach", 
            "system_outage_15min": "System outage over 15 minutes",
            "chemical_spill_1gal": "Chemical spill of more than 1 gallon"
        }
        
        # Event types from AVOMO form
        self.event_types = {
            "safety_concern": {
                "name": "Safety Concern",
                "description": "You noticed something unsafe or unusual, but no one was hurt and nothing was damaged",
                "required_fields": ["safety_concern_description", "safety_concern_corrective_action"]
            },
            "injury_illness": {
                "name": "Injury/Illness", 
                "description": "Someone got hurt or felt sick while working",
                "required_fields": [
                    "injured_employee_name", "injured_employee_job_title", "injured_employee_phone",
                    "injured_employee_address", "injured_employee_city", "injured_employee_state", 
                    "injured_employee_zip", "employee_status", "supervisor_name", 
                    "date_supervisor_notified", "time_supervisor_notified", "injury_illness_description",
                    "injury_illness_type", "affected_body_parts", "injury_illness_immediate_action",
                    "enablon_report_submitted"
                ]
            },
            "property_damage": {
                "name": "Property Damage",
                "description": "Something got broken, damaged, or was lost (equipment, tools, facility, etc.)",
                "required_fields": [
                    "property_damage_description", "approximate_total_cost", 
                    "property_damage_immediate_action", "enablon_report_submitted"
                ]
            },
            "security_concern": {
                "name": "Security Concern",
                "description": "You noticed something suspicious, such as unauthorized access, theft, or any risk to people or property security",
                "required_fields": [
                    "security_event_types", "security_concern_description", "involved_names_descriptions",
                    "involved_parties_type", "law_enforcement_contacted", "security_footage_available",
                    "security_corrective_actions", "enablon_report_submitted"
                ]
            },
            "vehicle_collision": {
                "name": "Vehicle Collision", 
                "description": "An autonomous vehicle (or another vehicle on site) was involved in a crash or hit something",
                "required_fields": [
                    "collision_location", "involved_parties", "vehicle_involved", "what_vehicle_hit",
                    "anyone_injured", "vehicle_operation_mode", "vehicle_collision_description",
                    "vehicle_collision_immediate_action", "enablon_report_submitted"
                ]
            },
            "environmental": {
                "name": "Environmental",
                "description": "A spill, leak, or other issue that could harm people, the environment, or violate environmental rules",
                "required_fields": [
                    "environmental_involved_parties", "environmental_employee_types", "spill_size",
                    "chemicals_involved", "environmental_spill_description", 
                    "environmental_spill_immediate_action", "enablon_report_submitted"
                ]
            },
            "depot_event": {
                "name": "Depot Event",
                "description": "A site-wide outage or emergency occurred",
                "required_fields": [
                    "depot_event_description", "depot_immediate_actions", "depot_outcome_lessons"
                ]
            },
            "near_miss": {
                "name": "Near Miss",
                "description": "Something almost went wrong. No one was hurt, and nothing was damaged, but it could've been worse",
                "required_fields": [
                    "near_miss_type", "near_miss_description", "near_miss_corrective_action"
                ]
            }
        }
        
        # Injury/Illness specific fields
        self.injury_illness_types = [
            "Cut, Laceration, or Puncture", "Burn (thermal, chemical, electrical, or radiation)",
            "Fracture (broken bones from falls or impacts)", "Bruise/Contusion (caused by impact with objects)",
            "Sprain or Strain (overexertion, awkward movements, lifting injuries)",
            "Dislocation (joints forced out of position)", "Crush Injury (body part caught between objects)",
            "Carpal Tunnel Syndrome", "Tendonitis", "Bursitis", "Muscle Strain",
            "Hearing Loss", "Respiratory Condition", "Skin Disorder", 
            "Heat Stress/Heat Stroke", "Cold Stress - Frostbite/Hypothermia",
            "Chemical Burn", "Radiation Exposure", "Electrical Shock", "Biological Exposure"
        ]
        
        self.body_parts = [
            "Scalp", "Skull", "Eyes", "Ears", "Nose", "Mouth", "Teeth", "Neck",
            "Shoulders", "Upper Back", "Lower Back", "Upper Arm", "Elbow", "Forearm",
            "Wrist", "Hand", "Fingers", "Torso", "Chest", "Ribs", "Abdomen", "Pelvis",
            "Hips", "Thighs", "Knees", "Lower Legs", "Ankles", "Feet", "Toes"
        ]
        
        self.employee_status_types = ["Full time", "Part Time", "Temporary", "Contractor", "Visitor"]
        
        # Security event types
        self.security_event_types = [
            "Break-in / Forced Entry", "Found Illicit Substance/Paraphernalia or Weapon in ADV",
            "Found Sharps or Medication in ADV", "Property Damage", "Suspicious Activity",
            "Theft", "Trespassing", "Vandalism", "Workplace Violence / Threat", "Other"
        ]
        
        # Near miss types
        self.near_miss_types = [
            "Potential Injury", "Potential Property Damage", 
            "Potential Environmental Damage", "Potential Damage to Company Image"
        ]

    def get_field_questions(self) -> Dict[str, str]:
        """Return user-friendly questions for each field"""
        return {
            # Basic Information
            "event_date": "What date did this event occur? (MM/DD/YYYY)",
            "event_time": "What time did this event occur? (24-hour format, e.g., 1430 for 2:30 PM)",
            "reporter_name": "What is your name? (This will be kept confidential)",
            "reporter_email": "What is your email address for follow-up?",
            "site": "Which AVOMO site did this occur at?",
            
            # Severity Assessment
            "is_severe_event": "Does this event meet the severe event criteria? (See criteria list)",
            "severe_event_type": "What type of severe event is this?",
            "severe_event_description": "Please provide detailed description including locations, timings, people/systems involved, and actions taken",
            
            # Safety Concern Fields
            "safety_concern_description": "What did you see, and where did it happen?",
            "safety_concern_corrective_action": "Did you do anything to help, or do you have an idea to fix it?",
            
            # Injury/Illness Fields
            "injured_employee_name": "What is the injured employee's full name?",
            "injured_employee_job_title": "What is their job title?",
            "injured_employee_phone": "What is their phone number?",
            "injured_employee_address": "What is their address?",
            "injured_employee_city": "What city do they live in?",
            "injured_employee_state": "What state?",
            "injured_employee_zip": "What is their ZIP code?",
            "employee_status": "What is their employment status?",
            "supervisor_name": "Who is their supervisor?",
            "date_supervisor_notified": "When was the supervisor notified? (MM/DD/YYYY)",
            "time_supervisor_notified": "What time was the supervisor notified? (24-hour format)",
            "injury_illness_description": "Please describe the injury/illness event in detail",
            "injury_illness_type": "What type of injury or illness occurred?",
            "affected_body_parts": "Which body part(s) were affected?",
            "injury_illness_immediate_action": "What immediate action was taken?",
            "enablon_report_submitted": "Has an Enablon report been submitted to Waymo?",
            
            # Property Damage Fields
            "property_damage_description": "Please describe the property damage event",
            "approximate_total_cost": "What is the approximate total cost of loss & repairs? (in dollars)",
            "property_damage_immediate_action": "What immediate corrective action was taken?",
            
            # Security Concern Fields
            "security_event_types": "What type of security event occurred? (Select all that apply)",
            "security_concern_description": "Please describe the security concern event",
            "involved_names_descriptions": "Please provide name(s), job title(s), or description(s) of involved parties",
            "involved_parties_type": "What type of parties were involved?",
            "law_enforcement_contacted": "Was law enforcement or emergency services contacted?",
            "law_enforcement_details": "List agency, time called, and any report number or officer name",
            "security_footage_available": "Is security footage available?",
            "security_corrective_actions": "What corrective actions were taken? (e.g., site secured, access restricted, police called)",
            
            # Vehicle Collision Fields
            "collision_location": "Where did the collision happen?",
            "involved_parties": "Who were the involved parties? (Full names)",
            "vehicle_involved": "Which vehicle was involved? (Include vehicle number or description)",
            "what_vehicle_hit": "What did the vehicle hit? (e.g., another car, fence)",
            "anyone_injured": "Was anyone injured in the collision?",
            "vehicle_operation_mode": "Was the vehicle being operated manually or autonomously?",
            "vehicle_collision_description": "Please describe the vehicle collision event",
            "vehicle_collision_immediate_action": "What immediate corrective action was taken?",
            
            # Environmental Fields
            "environmental_involved_parties": "Who were the involved parties? (Full names)",
            "environmental_employee_types": "What types of employees were involved?",
            "spill_size": "How large was the spill?",
            "chemicals_involved": "What chemical(s) was involved in the spill?",
            "environmental_spill_description": "Please describe the environmental spill event",
            "environmental_spill_immediate_action": "What immediate corrective action was taken?",
            
            # Depot Event Fields
            "depot_event_description": "What happened during this depot event?",
            "depot_immediate_actions": "Describe the actions that were taken",
            "depot_outcome_lessons": "What was the outcome? What did you learn? What would you do differently next time?",
            
            # Near Miss Fields
            "near_miss_type": "What type of near miss was this?",
            "near_miss_description": "What did you see, and where did it happen?",
            "near_miss_corrective_action": "Did you do anything to help, or do you have an idea to fix it?"
        }

    def validate_severe_event(self, event_data: Dict) -> Tuple[bool, str]:
        """Check if event meets severe event criteria"""
        event_type = event_data.get("event_type")
        description = event_data.get("description", "").lower()
        
        # AV collision with emergency services/damage/injury
        if event_type == "vehicle_collision":
            if any(keyword in description for keyword in ["emergency", "911", "damage", "injury", "hurt"]):
                return True, "av_collision_emergency"
        
        # Fatality/Hospitalization indicators  
        if any(keyword in description for keyword in ["death", "died", "fatal", "hospital", "amputation", "life threatening"]):
            return True, "fatality_hospitalization"
            
        # Site-wide emergency
        if any(keyword in description for keyword in ["site emergency", "911", "evacuation", "site-wide"]):
            return True, "site_emergency_911"
            
        # Security breach
        if event_type == "security_concern" and any(keyword in description for keyword in ["breach", "unauthorized access", "cyber"]):
            return True, "security_breach"
            
        # System outage
        if "outage" in description and any(keyword in description for keyword in ["15 min", "fifteen min", "hours"]):
            return True, "system_outage_15min"
            
        # Chemical spill > 1 gallon
        if event_type == "environmental" and any(keyword in description for keyword in ["gallon", "large spill", "major spill"]):
            return True, "chemical_spill_1gal"
            
        return False, ""

    def extract_info_from_description(self, description: str, event_type: str) -> Dict:
        """Extract structured information from free-text description"""
        extracted = {}
        desc_lower = description.lower()
        
        # Extract time information
        time_patterns = [
            r"at (\d{1,2}):(\d{2})\s*(am|pm)",
            r"around (\d{1,2})\s*(am|pm)",
            r"(\d{1,2}):(\d{2})"
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, desc_lower)
            if match:
                extracted["estimated_time"] = match.group(0)
                break
        
        # Extract location information
        location_keywords = ["in", "at", "near", "by", "location", "area", "building", "floor", "room"]
        for keyword in location_keywords:
            pattern = f"{keyword}\\s+([^.!?\\n]+)"
            match = re.search(pattern, desc_lower)
            if match:
                extracted["estimated_location"] = match.group(1).strip()
                break
        
        # Event-specific extraction
        if event_type == "injury_illness":
            # Extract body parts
            for body_part in self.body_parts:
                if body_part.lower() in desc_lower:
                    extracted["likely_body_part"] = body_part
                    break
            
            # Extract injury type indicators
            injury_indicators = {
                "cut": "Cut, Laceration, or Puncture",
                "laceration": "Cut, Laceration, or Puncture", 
                "burn": "Burn (thermal, chemical, electrical, or radiation)",
                "fracture": "Fracture (broken bones from falls or impacts)",
                "broken": "Fracture (broken bones from falls or impacts)",
                "bruise": "Bruise/Contusion (caused by impact with objects)",
                "sprain": "Sprain or Strain (overexertion, awkward movements, lifting injuries)",
                "strain": "Sprain or Strain (overexertion, awkward movements, lifting injuries)"
            }
            
            for indicator, injury_type in injury_indicators.items():
                if indicator in desc_lower:
                    extracted["likely_injury_type"] = injury_type
                    break
        
        elif event_type == "vehicle_collision":
            # Extract vehicle operation mode
            if any(word in desc_lower for word in ["manual", "manually", "driving", "driver"]):
                extracted["likely_operation_mode"] = "Manually"
            elif any(word in desc_lower for word in ["autonomous", "auto", "self-driving"]):
                extracted["likely_operation_mode"] = "Autonomously"
        
        elif event_type == "environmental":
            # Extract spill size indicators
            if any(word in desc_lower for word in ["large", "major", "significant", "gallon", "liters"]):
                extracted["likely_spill_size"] = "More than one (1) gallon"
            elif any(word in desc_lower for word in ["small", "minor", "drops", "splash"]):
                extracted["likely_spill_size"] = "Less than one (1) gallon"
        
        return extracted

    def get_smart_follow_up_question(self, event_type: str, collected_data: Dict, current_field: str) -> str:
        """Generate smart follow-up questions based on collected data"""
        base_questions = self.get_field_questions()
        base_question = base_questions.get(current_field, f"Please provide {current_field.replace('_', ' ')}")
        
        # Add context from extracted information
        extracted = collected_data.get("extracted_info", {})
        
        if current_field == "event_time" and "estimated_time" in extracted:
            base_question += f" (You mentioned '{extracted['estimated_time']}' - please confirm or provide exact time)"
        
        elif current_field in ["safety_concern_description", "injury_illness_description"] and "estimated_location" in extracted:
            base_question += f" (I noticed you mentioned '{extracted['estimated_location']}' - please provide complete details)"
        
        elif current_field == "affected_body_parts" and "likely_body_part" in extracted:
            base_question += f" (Based on your description, it seems like {extracted['likely_body_part']} was involved - please confirm)"
        
        elif current_field == "injury_illness_type" and "likely_injury_type" in extracted:
            base_question += f" (It sounds like this might be: {extracted['likely_injury_type']} - is this correct?)"
        
        elif current_field == "vehicle_operation_mode" and "likely_operation_mode" in extracted:
            base_question += f" (Based on your description, it seems the vehicle was operating {extracted['likely_operation_mode']} - please confirm)"
        
        return base_question

    def get_validation_rules(self) -> Dict:
        """Return validation rules for each field type"""
        return {
            "event_date": {
                "pattern": r"^\d{2}/\d{2}/\d{4}$",
                "error": "Please use MM/DD/YYYY format"
            },
            "event_time": {
                "pattern": r"^\d{4}$",
                "error": "Please use 24-hour format (e.g., 1430 for 2:30 PM)"
            },
            "injured_employee_phone": {
                "pattern": r"^\d{10}$",
                "error": "Please provide 10-digit phone number"
            },
            "injured_employee_zip": {
                "pattern": r"^\d{5}$",
                "error": "Please provide 5-digit ZIP code"
            },
            "approximate_total_cost": {
                "pattern": r"^\d+$",
                "error": "Please provide cost in dollars (numbers only)"
            }
        }

# Integration with existing chatbot system
class AVOMOIntentClassifier:
    """Enhanced intent classifier for AVOMO-specific incident types"""
    
    def __init__(self):
        self.avomo_structure = AVOMOIncidentStructure()
    
    def classify_avomo_incident_type(self, description: str) -> Tuple[str, float, Dict]:
        """Classify incident type based on AVOMO categories"""
        desc_lower = description.lower()
        scores = {}
        
        # Score each event type based on keywords
        event_type_keywords = {
            "safety_concern": ["unsafe", "concern", "observation", "hazard", "risk", "dangerous"],
            "injury_illness": ["injury", "injured", "hurt", "pain", "medical", "sick", "illness"],
            "property_damage": ["damage", "broken", "destroyed", "lost", "equipment", "facility"],
            "security_concern": ["security", "theft", "unauthorized", "suspicious", "trespassing"],
            "vehicle_collision": ["collision", "crash", "hit", "accident", "vehicle", "av"],
            "environmental": ["spill", "leak", "chemical", "environmental", "contamination"],
            "depot_event": ["outage", "emergency", "site-wide", "depot", "system"],
            "near_miss": ["near miss", "almost", "close call", "could have", "nearly"]
        }
        
        for event_type, keywords in event_type_keywords.items():
            score = sum(1 for keyword in keywords if keyword in desc_lower)
            if score > 0:
                scores[event_type] = score / len(keywords)
        
        if not scores:
            return "safety_concern", 0.5, {}  # Default to safety concern
        
        best_type = max(scores, key=scores.get)
        confidence = min(0.95, scores[best_type] + 0.3)
        
        # Extract additional information
        extracted_info = self.avomo_structure.extract_info_from_description(description, best_type)
        
        return best_type, confidence, extracted_info
