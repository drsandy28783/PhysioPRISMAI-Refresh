# firestore_helpers.py
from typing import Dict, Any, List, Optional
from firebase_admin import firestore
from firebase_admin_init import db

def now_ts():
    return firestore.SERVER_TIMESTAMP

# ---- USERS (/users/{uid}) ----
def upsert_user_profile(uid: str, email: str, partial: Optional[Dict[str, Any]] = None):
    partial = partial or {}
    ref = db.collection("users").document(uid)
    snap = ref.get()
    existing = snap.to_dict() if snap.exists else {}
    payload = {
        "email": email or existing.get("email", ""),
        "name": partial.get("name", existing.get("name")),
        "role": existing.get("role", "physio"),
        "active": existing.get("active", 1),
        "approved": existing.get("approved", 1),
        "created_at": existing.get("created_at", now_ts()),
        "instituteId": partial.get("instituteId", existing.get("instituteId")),
        "tokenBalance": partial.get("tokenBalance", existing.get("tokenBalance")),
        "tokens_allocated": partial.get("tokens_allocated", existing.get("tokens_allocated")),
    }
    ref.set(payload, merge=True)

# ---- PATIENTS (/patients) ----
def create_patient(uid: str, data: Dict[str, Any]) -> str:
    payload = dict(data)
    payload["created_by"] = uid                 # REQUIRED by rules
    payload.setdefault("createdAt", now_ts())
    ref = db.collection("patients").add(payload)[1]
    return ref.id

def list_patients_for_owner(uid: str, limit_n: int = 50) -> List[Dict[str, Any]]:
    q = (db.collection("patients")
         .where("created_by", "==", uid)
         .order_by("createdAt", direction=firestore.Query.DESCENDING)
         .limit(limit_n))
    return [{"id": d.id, **d.to_dict()} for d in q.stream()]

def update_patient(patient_id: str, data: Dict[str, Any]) -> None:
    db.collection("patients").document(patient_id).update(data)

def delete_patient(patient_id: str) -> None:
    db.collection("patients").document(patient_id).delete()

# ---- FOLLOW UPS (/followUps) ----
def create_follow_up(uid: str, patient_id: str, data: Dict[str, Any]) -> str:
    payload = dict(data)
    payload["patientId"] = patient_id
    payload["created_by"] = uid                 # REQUIRED by rules
    payload.setdefault("createdAt", now_ts())
    ref = db.collection("followUps").add(payload)[1]
    return ref.id

def list_followups_for_patient(patient_id: str, limit_n: int = 100) -> List[Dict[str, Any]]:
    q = (db.collection("followUps")
         .where("patientId", "==", patient_id)
         .order_by("createdAt", direction=firestore.Query.DESCENDING)
         .limit(limit_n))
    return [{"id": d.id, **d.to_dict()} for d in q.stream()]
