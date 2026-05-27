"""
Quick script to delete a duplicate patient from Firestore
Usage: python delete_patient.py <patient_id>
Example: python delete_patient.py sandy-002
"""
import sys
import os
from google.cloud import firestore
from datetime import datetime

def delete_patient(patient_id):
    """Delete a patient by ID"""
    try:
        # Initialize Firestore
        db = firestore.Client()

        # Get patient document
        patient_ref = db.collection('patients').document(patient_id)
        patient_doc = patient_ref.get()

        if not patient_doc.exists:
            print(f"❌ Error: Patient '{patient_id}' not found")
            return False

        patient_data = patient_doc.to_dict()

        # Show patient details for confirmation
        print(f"\n📋 Patient Details:")
        print(f"   ID: {patient_id}")
        print(f"   Name: {patient_data.get('name', 'N/A')}")
        print(f"   Age/Sex: {patient_data.get('age_sex', 'N/A')}")
        print(f"   Contact: {patient_data.get('contact', 'N/A')}")
        print(f"   Created: {patient_data.get('created_at', 'N/A')}")
        print(f"   Physio: {patient_data.get('physio_id', 'N/A')}")

        # Confirm deletion
        confirm = input(f"\n⚠️  Are you sure you want to delete this patient? (yes/no): ")

        if confirm.lower() != 'yes':
            print("❌ Deletion cancelled")
            return False

        # Delete the patient
        patient_ref.delete()

        print(f"\n✅ Successfully deleted patient '{patient_id}'")
        print(f"   Note: This does NOT decrement your patient quota (by design)")

        return True

    except Exception as e:
        print(f"❌ Error deleting patient: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python delete_patient.py <patient_id>")
        print("Example: python delete_patient.py sandy-002")
        sys.exit(1)

    patient_id = sys.argv[1]
    success = delete_patient(patient_id)

    sys.exit(0 if success else 1)
