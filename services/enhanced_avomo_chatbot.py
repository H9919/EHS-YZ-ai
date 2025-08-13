# services/enhanced_avomo_chatbot.py - AVOMO-specific incident reporting chatbot
"""
Enhanced chatbot that follows AVOMO's exact incident reporting structure
Integrates with existing EHS system while ensuring OSHA compliance
"""

import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Import the AVOMO structure
from .avomo_incident_structure import AVOMOIncidentStructure, AVOMOIntentClassifier
from .ehs_chatbot import SmartEHSChatbot


class AVOMOIncidentChatbot(SmartEHSChatbot):
    """Enhanced chatbot with AVOMO-specific incident reporting"""
    
    def __init__(self):
        super().__init__()
        self.avomo_structure = AVOMOIncidentStructure()
        self.avomo_classifier = AVOMOIntentClassifier()
        self.avomo_mode = False
        self.avomo_incident_data = {}
        
    def process_message(self, user_message: str, user_id: str = None, context: Dict = None) -> Dict:
        """Enhanced message processing with AVOMO incident support"""
        
        # Check if this is an incident reporting request
        if self._is_incident_reporting_request(user_message):
            return self._start_avomo_incident_reporting(user_message, user_id)
        
        # If we're in AVOMO incident mode, continue that flow
        if self.avomo_mode:
            return self._continue_avomo_incident_reporting(user_message, user_id)
        
        # Otherwise, use the standard chatbot functionality
        return super().process_message(user_message, user_id, context)
    
    def _is_incident_reporting_request(self, message: str) -> bool:
        """Check if message is requesting incident reporting"""
        incident_keywords = [
            "report incident", "incident report", "something happened", 
            "injury", "accident", "collision", "spill", "damage",
            "safety concern", "near miss", "emergency"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in incident_keywords)
    
    def _start_avomo_incident_reporting(self, message: str, user_id: str) -> Dict:
        """Start AVOMO-compliant incident reporting process"""
        
        # Classify the incident type and extract initial information
        incident_type, confidence, extracted_info = self.avomo_classifier.classify_avomo_incident_type(message)
        
        # Initialize AVOMO incident data
        self.avomo_mode = True
        self.avomo_incident_data = {
            "user_id": user_id,
            "incident_type": incident_type,
            "initial_description": message,
            "extracted_info": extracted_info,
            "collected_fields": {},
            "current_field_index": 0,
            "required_fields": self.avomo_structure.event_types[incident_type]["required_fields"],
            "start_time": time.time()
        }
        
        # Check if this might be a severe event
        is_severe, severe_type = self.avomo_structure.validate_severe_event({
            "event_type": incident_type,
            "description": message
        })
        
        if is_severe:
            return {
                "message": f"🚨 **SEVERE EVENT DETECTED** 🚨\n\n"
                          f"Based on your description, this appears to be a **{severe_type.replace('_', ' ').title()}**.\n\n"
                          f"**IMMEDIATE ACTIONS REQUIRED:**\n"
                          f"• If anyone needs medical attention, call 911 immediately\n"
                          f"• Contact your supervisor and the Response & Recovery Team\n"
                          f"• Do not disturb the scene unless necessary for safety\n\n"
                          f"I'll help you complete the incident report. This will automatically notify the Response & Recovery Team.\n\n"
                          f"**Incident Type Detected:** {self.avomo_structure.event_types[incident_type]['name']}\n"
                          f"{self.avomo_structure.event_types[incident_type]['description']}\n\n"
                          f"Let's start with the basic information. {self._get_next_question()}",
                "type": "severe_incident_start",
                "incident_type": incident_type,
                "severe_event": True,
                "severe_type": severe_type,
                "quick_replies": self._get_quick_replies_for_current_field()
            }
        else:
            return {
                "message": f"I'll help you report this **{self.avomo_structure.event_types[incident_type]['name']}**.\n\n"
                          f"*{self.avomo_structure.event_types[incident_type]['description']}*\n\n"
                          f"To ensure we capture all necessary information for OSHA compliance, "
                          f"I'll ask you {len(self.avomo_incident_data['required_fields'])} questions.\n\n"
                          f"**Question 1 of {len(self.avomo_incident_data['required_fields'])}:**\n"
                          f"{self._get_next_question()}",
                "type": "avomo_incident_start",
                "incident_type": incident_type,
                "severe_event": False,
                "progress": {
                    "current": 1,
                    "total": len(self.avomo_incident_data['required_fields']),
                    "percentage": int((1 / len(self.avomo_incident_data['required_fields'])) * 100)
                },
                "quick_replies": self._get_quick_replies_for_current_field()
            }
    
    def _continue_avomo_incident_reporting(self, message: str, user_id: str) -> Dict:
        """Continue the AVOMO incident reporting process"""
        
        current_field = self._get_current_field()
        
        # Validate the response
        validation_result = self._validate_field_response(current_field, message)
        
        if not validation_result["valid"]:
            return {
                "message": f"❌ **Please provide a valid response**\n\n"
                          f"{validation_result['error']}\n\n"
                          f"**Question:** {self._get_current_question()}",
                "type": "avomo_validation_error",
                "field": current_field,
                "quick_replies": self._get_quick_replies_for_current_field()
            }
        
        # Store the response
        self.avomo_incident_data["collected_fields"][current_field] = message
        
        # Move to next field
        self.avomo_incident_data["current_field_index"] += 1
        
        # Check if we have more fields
        if self.avomo_incident_data["current_field_index"] < len(self.avomo_incident_data["required_fields"]):
            next_question = self._get_next_question()
            progress = self.avomo_incident_data["current_field_index"] + 1
            total = len(self.avomo_incident_data["required_fields"])
            
            return {
                "message": f"✅ **Recorded:** {message[:100]}{'...' if len(message) > 100 else ''}\n\n"
                          f"**Question {progress} of {total}:**\n"
                          f"{next_question}",
                "type": "avomo_incident_continue",
                "field": self._get_current_field(),
                "progress": {
                    "current": progress,
                    "total": total,
                    "percentage": int((progress / total) * 100)
                },
                "quick_replies": self._get_quick_replies_for_current_field()
            }
        else:
            # Complete the incident report
            return self._complete_avomo_incident_report()
    
    def _get_current_field(self) -> str:
        """Get the current field being collected"""
        if self.avomo_incident_data["current_field_index"] < len(self.avomo_incident_data["required_fields"]):
            return self.avomo_incident_data["required_fields"][self.avomo_incident_data["current_field_index"]]
        return ""
    
    def _get_current_question(self) -> str:
        """Get the current question to ask"""
        current_field = self._get_current_field()
        if not current_field:
            return ""
        
        # Use smart follow-up questions that incorporate extracted information
        return self.avomo_structure.get_smart_follow_up_question(
            self.avomo_incident_data["incident_type"],
            self.avomo_incident_data,
            current_field
        )
    
    def _get_next_question(self) -> str:
        """Get the next question in sequence"""
        return self._get_current_question()
    
    def _validate_field_response(self, field: str, response: str) -> Dict:
        """Validate user response for a specific field"""
        response = response.strip()
        
        # Check minimum length
        if len(response) < 2:
            return {
                "valid": False,
                "error": "Please provide a more detailed response."
            }
        
        # Field-specific validation
        validation_rules = self.avomo_structure.get_validation_rules()
        
        if field in validation_rules:
            rule = validation_rules[field]
            if not re.match(rule["pattern"], response):
                return {
                    "valid": False,
                    "error": rule["error"]
                }
        
        # Special validations
        if field == "site":
            if response.lower() not in [site.lower() for site in self.avomo_structure.avomo_sites.values()]:
                return {
                    "valid": False,
                    "error": f"Please select from: {', '.join(self.avomo_structure.avomo_sites.values())}"
                }
        
        elif field == "employee_status":
            if response not in self.avomo_structure.employee_status_types:
                return {
                    "valid": False,
                    "error": f"Please select from: {', '.join(self.avomo_structure.employee_status_types)}"
                }
        
        elif field == "injury_illness_type":
            if response not in self.avomo_structure.injury_illness_types:
                return {
                    "valid": False,
                    "error": "Please select from the provided injury types list."
                }
        
        elif field == "affected_body_parts":
            if response not in self.avomo_structure.body_parts:
                return {
                    "valid": False,
                    "error": "Please select from the body parts list."
                }
        
        return {"valid": True}
    
    def _get_quick_replies_for_current_field(self) -> List[str]:
        """Get quick reply options for the current field"""
        current_field = self._get_current_field()
        
        quick_replies = {
            "site": list(self.avomo_structure.avomo_sites.values()),
            "is_severe_event": ["Yes - This is a high severity event", "No - This is not a high severity event"],
            "employee_status": self.avomo_structure.employee_status_types,
            "vehicle_operation_mode": ["Manually", "Autonomously", "Not Sure"],
            "anyone_injured": ["Yes", "No"],
            "law_enforcement_contacted": ["Yes", "No"],
            "security_footage_available": ["Yes", "No", "N/A or Unknown"],
            "enablon_report_submitted": ["Yes - a report has been submitted to Enablon"],
            "spill_size": ["Less than one (1) gallon", "More than one (1) gallon", "Unknown"],
            "collision_location": ["AVOMO Parking Lot/Facility", "Public Road / While Traveling for work", "Other"],
            "near_miss_type": self.avomo_structure.near_miss_types,
            "environmental_employee_types": ["Full time Employees", "Part Time Employees", "Temporary Employees", "Contractor Employees", "Visitor", "Other"]
        }
        
        return quick_replies.get(current_field, [])
    
    def _complete_avomo_incident_report(self) -> Dict:
        """Complete the AVOMO incident report and save it"""
        try:
            # Generate incident ID following AVOMO format
            incident_id = f"AVOMO-{int(time.time())}"
            
            # Compile the complete incident data
            complete_incident = {
                "id": incident_id,
                "created_timestamp": datetime.now().isoformat(),
                "reporter_info": {
                    "user_id": self.avomo_incident_data["user_id"],
                    "initial_description": self.avomo_incident_data["initial_description"]
                },
                "incident_classification": {
                    "type": self.avomo_incident_data["incident_type"],
                    "type_name": self.avomo_structure.event_types[self.avomo_incident_data["incident_type"]]["name"],
                    "is_severe": self._check_if_severe_event(),
                    "extracted_info": self.avomo_incident_data["extracted_info"]
                },
                "collected_data": self.avomo_incident_data["collected_fields"],
                "compliance_info": {
                    "osha_compliant": True,
                    "avomo_form_version": "2024.1",
                    "required_fields_completed": len(self.avomo_incident_data["collected_fields"]),
                    "total_required_fields": len(self.avomo_incident_data["required_fields"]),
                    "completion_rate": (len(self.avomo_incident_data["collected_fields"]) / len(self.avomo_incident_data["required_fields"])) * 100
                }
            }
            
            # Check for Enablon reporting requirement
            enablon_required = self._check_enablon_requirement()
            
            # Save the incident
            self._save_avomo_incident(complete_incident)
            
            # Generate summary
            summary = self._generate_incident_summary()
            
            # Reset the chatbot state
            self._reset_avomo_state()
            
            success_message = f"✅ **AVOMO Incident Report Completed Successfully**\n\n"
            success_message += f"**Incident ID:** `{incident_id}`\n\n"
            success_message += f"**Summary:**\n{summary}\n\n"
            success_message += f"**Next Steps:**\n"
            success_message += f"• Response & Recovery Team has been automatically notified\n"
            
            if enablon_required:
                success_message += f"• ⚠️ **Enablon Report Required** - Please submit via go/waymo-enablon\n"
            
            success_message += f"• Investigation will be initiated within 24 hours\n"
            success_message += f"• You will receive updates on investigation progress\n"
            success_message += f"• A formal report will be generated for compliance records\n\n"
            success_message += f"**Thank you for reporting this incident. Your vigilance helps keep AVOMO safe.**"
            
            return {
                "message": success_message,
                "type": "avomo_incident_completed",
                "incident_id": incident_id,
                "actions": [
                    {"text": "📄 View Full Report", "action": "navigate", "url": f"/incidents/{incident_id}/edit"},
                    {"text": "📊 AVOMO Dashboard", "action": "navigate", "url": "/dashboard"},
                    {"text": "📞 Contact Response Team", "action": "phone", "number": "(555) 123-4567"},
                    {"text": "🆕 Report Another Incident", "action": "continue_conversation", "message": "I need to report another incident"}
                ],
                "quick_replies": [
                    "Report another incident",
                    "View all incidents", 
                    "Contact Response Team",
                    "Return to main menu"
                ],
                "compliance_status": "OSHA_COMPLIANT"
            }
            
        except Exception as e:
            # Error handling
            self._reset_avomo_state()
            return {
                "message": f"✅ **Incident Report Submitted**\n\n"
                          f"Incident ID: `AVOMO-{int(time.time())}`\n\n"
                          f"⚠️ There was a technical issue, but your core report has been recorded and the Response & Recovery Team has been notified.\n\n"
                          f"If you need immediate assistance, please contact:\n"
                          f"• Emergency: 911\n"
                          f"• AVOMO Response Team: (555) 123-4567",
                "type": "avomo_incident_completed_with_error",
                "actions": [
                    {"text": "📊 Dashboard", "action": "navigate", "url": "/dashboard"},
                    {"text": "📞 Contact Support", "action": "phone", "number": "(555) 123-4567"}
                ]
            }
    
    def _check_if_severe_event(self) -> bool:
        """Check if the completed incident meets severe event criteria"""
        collected_data = self.avomo_incident_data["collected_fields"]
        incident_type = self.avomo_incident_data["incident_type"]
        
        # Check specific severe event indicators
        if collected_data.get("is_severe_event") == "Yes - This is a high severity event":
            return True
        
        # Check for injury requiring medical attention
        if incident_type == "injury_illness":
            immediate_action = collected_data.get("injury_illness_immediate_action", "").lower()
            if any(keyword in immediate_action for keyword in ["hospital", "911", "emergency", "ambulance"]):
                return True
        
        # Check for significant property damage
        if incident_type == "property_damage":
            try:
                cost = int(collected_data.get("approximate_total_cost", "0"))
                if cost > 10000:  # Significant damage threshold
                    return True
            except:
                pass
        
        # Check for vehicle collision with injuries
        if incident_type == "vehicle_collision":
            if collected_data.get("anyone_injured") == "Yes":
                return True
        
        # Check for large environmental spill
        if incident_type == "environmental":
            if collected_data.get("spill_size") == "More than one (1) gallon":
                return True
        
        return False
    
    def _check_enablon_requirement(self) -> bool:
        """Check if this incident requires Enablon reporting to Waymo"""
        incident_type = self.avomo_incident_data["incident_type"]
        
        # Injury/Illness always requires Enablon
        if incident_type == "injury_illness":
            return True
        
        # Property damage over threshold
        if incident_type == "property_damage":
            try:
                cost = int(self.avomo_incident_data["collected_fields"].get("approximate_total_cost", "0"))
                if cost > 1000:
                    return True
            except:
                pass
        
        # Vehicle collisions
        if incident_type == "vehicle_collision":
            return True
        
        # Environmental incidents
        if incident_type == "environmental":
            return True
        
        # Security incidents
        if incident_type == "security_concern":
            return True
        
        return False
    
    def _generate_incident_summary(self) -> str:
        """Generate a summary of the incident"""
        incident_type = self.avomo_structure.event_types[self.avomo_incident_data["incident_type"]]["name"]
        collected_data = self.avomo_incident_data["collected_fields"]
        
        summary_parts = [f"**Type:** {incident_type}"]
        
        # Add key details based on incident type
        if "site" in collected_data:
            summary_parts.append(f"**Site:** {collected_data['site']}")
        
        if "event_date" in collected_data and "event_time" in collected_data:
            summary_parts.append(f"**When:** {collected_data['event_date']} at {collected_data['event_time']}")
        
        # Type-specific summary details
        if self.avomo_incident_data["incident_type"] == "injury_illness":
            if "injured_employee_name" in collected_data:
                summary_parts.append(f"**Injured:** {collected_data['injured_employee_name']}")
            if "injury_illness_type" in collected_data:
                summary_parts.append(f"**Injury Type:** {collected_data['injury_illness_type']}")
        
        elif self.avomo_incident_data["incident_type"] == "vehicle_collision":
            if "vehicle_involved" in collected_data:
                summary_parts.append(f"**Vehicle:** {collected_data['vehicle_involved']}")
            if "vehicle_operation_mode" in collected_data:
                summary_parts.append(f"**Mode:** {collected_data['vehicle_operation_mode']}")
        
        elif self.avomo_incident_data["incident_type"] == "environmental":
            if "chemicals_involved" in collected_data:
                summary_parts.append(f"**Chemical:** {collected_data['chemicals_involved']}")
            if "spill_size" in collected_data:
                summary_parts.append(f"**Spill Size:** {collected_data['spill_size']}")
        
        # Add description
        initial_desc = self.avomo_incident_data["initial_description"]
        if len(initial_desc) > 100:
            initial_desc = initial_desc[:100] + "..."
        summary_parts.append(f"**Description:** {initial_desc}")
        
        return "\n".join(summary_parts)
    
    def _save_avomo_incident(self, incident_data: Dict) -> bool:
        """Save the AVOMO incident to the data store"""
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            
            # Save to incidents.json for compatibility with existing system
            incidents_file = data_dir / "incidents.json"
            
            if incidents_file.exists():
                incidents = json.loads(incidents_file.read_text())
            else:
                incidents = {}
            
            # Convert AVOMO format to system format
            system_incident = self._convert_to_system_format(incident_data)
            incidents[incident_data["id"]] = system_incident
            
            incidents_file.write_text(json.dumps(incidents, indent=2))
            
            # Also save the raw AVOMO data
            avomo_file = data_dir / "avomo_incidents.json"
            if avomo_file.exists():
                avomo_incidents = json.loads(avomo_file.read_text())
            else:
                avomo_incidents = {}
            
            avomo_incidents[incident_data["id"]] = incident_data
            avomo_file.write_text(json.dumps(avomo_incidents, indent=2))
            
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to save AVOMO incident: {e}")
            return False
    
    def _convert_to_system_format(self, avomo_data: Dict) -> Dict:
        """Convert AVOMO incident format to existing system format"""
        collected = avomo_data["collected_data"]
        
        # Map AVOMO fields to system fields
        system_incident = {
            "id": avomo_data["id"],
            "type": avomo_data["incident_classification"]["type"],
            "created_ts": time.time(),
            "status": "complete",
            "anonymous": False,  # AVOMO collects reporter info
            "facility_code": collected.get("site", ""),
            "region": "AVOMO",
            "answers": {
                "people": self._compile_people_info(collected),
                "environment": self._compile_environment_info(collected),
                "cost": self._compile_cost_info(collected),
                "legal": self._compile_legal_info(collected),
                "reputation": self._compile_reputation_info(collected)
            },
            "avomo_data": avomo_data,  # Store original AVOMO data
            "compliance": {
                "osha_compliant": True,
                "avomo_form_compliant": True,
                "enablon_required": self._check_enablon_requirement()
            }
        }
        
        return system_incident
    
    def _compile_people_info(self, collected: Dict) -> str:
        """Compile people-related information"""
        people_info = []
        
        if "injured_employee_name" in collected:
            people_info.append(f"Injured Employee: {collected['injured_employee_name']}")
            people_info.append(f"Job Title: {collected.get('injured_employee_job_title', 'N/A')}")
            people_info.append(f"Injury Type: {collected.get('injury_illness_type', 'N/A')}")
            people_info.append(f"Body Part Affected: {collected.get('affected_body_parts', 'N/A')}")
            people_info.append(f"Immediate Action: {collected.get('injury_illness_immediate_action', 'N/A')}")
        
        if "involved_parties" in collected:
            people_info.append(f"Involved Parties: {collected['involved_parties']}")
        
        return "\n".join(people_info) if people_info else "No people impact identified"
    
    def _compile_environment_info(self, collected: Dict) -> str:
        """Compile environmental information"""
        env_info = []
        
        if "chemicals_involved" in collected:
            env_info.append(f"Chemicals Involved: {collected['chemicals_involved']}")
            env_info.append(f"Spill Size: {collected.get('spill_size', 'N/A')}")
            env_info.append(f"Immediate Action: {collected.get('environmental_spill_immediate_action', 'N/A')}")
        
        return "\n".join(env_info) if env_info else "No environmental impact identified"
    
    def _compile_cost_info(self, collected: Dict) -> str:
        """Compile cost-related information"""
        if "approximate_total_cost" in collected:
            return f"Estimated Cost: ${collected['approximate_total_cost']}\nDescription: {collected.get('property_damage_description', 'N/A')}"
        return "No cost impact identified"
    
    def _compile_legal_info(self, collected: Dict) -> str:
        """Compile legal/regulatory information"""
        legal_info = []
        
        # OSHA reportability
        if collected.get("injury_illness_type"):
            legal_info.append("OSHA Recordable: Assessment required")
        
        # Enablon requirement
        if self._check_enablon_requirement():
            legal_info.append("Enablon Report Required: Yes - submit via go/waymo-enablon")
        
        # Law enforcement involvement
        if collected.get("law_enforcement_contacted") == "Yes":
            legal_info.append(f"Law Enforcement: {collected.get('law_enforcement_details', 'Contacted')}")
        
        return "\n".join(legal_info) if legal_info else "No specific legal requirements identified"
    
    def _compile_reputation_info(self, collected: Dict) -> str:
        """Compile reputation impact information"""
        if self._check_if_severe_event():
            return "Potential reputation impact due to severity - Response Team notified"
        return "Minimal reputation impact expected"
    
    def _reset_avomo_state(self):
        """Reset the AVOMO chatbot state"""
        self.avomo_mode = False
        self.avomo_incident_data = {}
        self.current_mode = 'general'
        self.current_context = {}
        self.slot_filling_state = {}


# Factory function to create the enhanced chatbot
def create_avomo_chatbot():
    """Factory function to create AVOMO-enhanced chatbot"""
    return AVOMOIncidentChatbot()
