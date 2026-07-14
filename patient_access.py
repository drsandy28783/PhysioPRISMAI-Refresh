"""Shared patient-ownership access check, used by main.py, mobile_api.py, and mobile_api_ai.py.

A patient is accessible to: its creating physio, any super admin (global access),
or any user who shares a non-empty institute string with the patient (team-wide
access for institute members — admins and regular team members alike).
"""


def patient_access_allowed(patient: dict, actor: dict) -> bool:
    """actor: {'email', 'is_admin', 'is_super_admin', 'institute'}"""
    if not patient or not actor:
        return False

    if patient.get('physio_id') == actor.get('email'):
        return True

    if actor.get('is_super_admin') == 1:
        return True

    institute = actor.get('institute')
    return bool(institute) and patient.get('institute') == institute
