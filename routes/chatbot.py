# services/avomo_incident_structure.py - AVOMO OSHA-Compliant Incident Structure
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re

# AVOMO Sites from the form
AVOMO_SITES = [
    "Austin Stassney",
    "Atlanta Plymouth", 
    "Atlanta Manheim"
]

# Severe Event Criteria (exactly as defined in AVOMO form)
SEVERE_EVENT_CRITERIA = {
    "av_collision": "AV collision resulting in calling emergency services, internal/frame damage to the vehicle, or injury to employees, vendors, or vulnerable road users",
    "fatality_hospitalization": "Fatality/Hospitalization/Amputation/Loss of an Eye or Life-Threatening",
    "site_emergency": "Site-wide emergency that requires calling 911",
    "security_breach": "Physical security or cybersecurity breach", 
    "system_outage": "System outage over 15 minutes",
    "chemical_spill": "Chemical spill of more than 1 gallon"
}

# Event Types from AVOMO form
EVENT_TYPES = {
    "safety_concern": {
        "label": "Safety Concern",
        "description": "You noticed something unsafe or unusual, but no one was hurt and nothing was damaged",
        "required_fields": ["description", "corrective_action"],
        "severity_check": False
    },
    "injury_illness": {
        "label": "Injury/Illness", 
        "description": "Someone got hurt or felt sick while working",
        "required_fields": ["injured_employee_name", "job_title", "phone_number", "address", "city", "state", "zip", 
                           "employee_status", "supervisor_name", "supervisor_notification_date", "supervisor_notification_time",
                           "injury_description", "injury_type", "affected_body_parts", "immediate_action", "en
