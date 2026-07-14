"""
Backfill the 'institute' field on patient documents that don't have one.

Mobile-created patients never wrote an 'institute' field (web-created patients
already have it). This finds every patient doc missing 'institute', looks up
the owning physio's own institute, and stamps it onto the patient -- only if
the owner actually belongs to an institute (genuinely solo-physio patients are
left alone, printed as skipped).

Usage:
    python backfill_patient_institute.py            # dry run, prints only
    python backfill_patient_institute.py --apply     # actually writes updates
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from azure_cosmos_db import get_cosmos_db
db = get_cosmos_db()

APPLY = '--apply' in sys.argv


def main():
    mode = "APPLY" if APPLY else "DRY RUN"
    print(f"Running in {mode} mode\n")

    scanned = 0
    updated = 0
    skipped_solo = 0
    skipped_no_user = 0

    for patient_doc in db.collection('patients').stream():
        patient = patient_doc.to_dict()
        if patient.get('institute'):
            continue

        scanned += 1
        physio_id = patient.get('physio_id')
        if not physio_id:
            skipped_no_user += 1
            continue

        user_doc = db.collection('users').document(physio_id).get()
        if not user_doc.exists:
            print(f"  [skip] patient {patient_doc.id}: owner {physio_id} not found")
            skipped_no_user += 1
            continue

        owner_institute = user_doc.to_dict().get('institute', '')
        if not owner_institute:
            skipped_solo += 1
            continue

        print(f"  [{'apply' if APPLY else 'would apply'}] patient {patient_doc.id} "
              f"(owner {physio_id}): institute -> '{owner_institute}'")
        if APPLY:
            db.collection('patients').document(patient_doc.id).update({'institute': owner_institute})
        updated += 1

    print(f"\nScanned (missing institute): {scanned}")
    print(f"Updated{'':1}: {updated}")
    print(f"Skipped (owner is solo, no institute): {skipped_solo}")
    print(f"Skipped (owner not found): {skipped_no_user}")
    if not APPLY:
        print("\nDry run only -- re-run with --apply to write these updates.")


if __name__ == '__main__':
    main()
