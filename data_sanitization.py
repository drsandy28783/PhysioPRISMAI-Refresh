"""
Data Sanitization Module - PhysiologicPRISM
HIPAA-compliant PHI sanitization for AI prompts and external services
"""

import re


def sanitize_age_sex(age_sex_str):
    """Convert exact age to age range to protect PHI."""
    if not age_sex_str:
        return "Age/Sex not specified"

    # Extract age and sex
    match = re.search(r'(\d+)\s*([MF]|male|female)', age_sex_str.strip(), re.IGNORECASE)
    if not match:
        return "Demographics: Adult"

    age = int(match.group(1))
    sex = match.group(2).upper()[0]  # M or F

    # Convert to age ranges
    if age < 18:
        age_range = "Under 18"
    elif age < 30:
        age_range = "20s"
    elif age < 40:
        age_range = "30s"
    elif age < 50:
        age_range = "40s"
    elif age < 60:
        age_range = "50s"
    elif age < 70:
        age_range = "60s"
    else:
        age_range = "70+"

    return f"{age_range} {sex}"


def sanitize_clinical_text(text):
    """Remove PHI from clinical text while preserving clinical information."""
    if not text:
        return ""

    # Remove common PHI patterns
    sanitized = text

    # Remove specific dates (but keep relative time references)
    sanitized = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '[date removed]', sanitized)
    sanitized = re.sub(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4}\b', '[date removed]', sanitized, flags=re.IGNORECASE)

    # Remove proper names (preserve medical and anatomical terms)
    medical_terms = {
        # Medical abbreviations and facilities
        'MRI', 'CT', 'X-ray', 'PT', 'OT', 'Dr', 'Hospital', 'Clinic', 'Emergency', 'Department',
        # Body parts - general
        'Pain', 'Back', 'Knee', 'Shoulder', 'Hip', 'Neck', 'Arm', 'Leg', 'Ankle', 'Foot', 'Hand',
        'Wrist', 'Elbow', 'Spine', 'Lumbar', 'Thoracic', 'Cervical', 'Chest', 'Abdomen', 'Head',
        'Finger', 'Thumb', 'Toe', 'Heel', 'Calf', 'Thigh', 'Forearm', 'Pelvis', 'Groin', 'Buttock',
        # Directional terms
        'Right', 'Left', 'Bilateral', 'Anterior', 'Posterior', 'Lateral', 'Medial', 'Upper', 'Lower',
        'Proximal', 'Distal', 'Superior', 'Inferior', 'Dorsal', 'Ventral', 'Superficial', 'Deep',
        # Spinal regions
        'Sacral', 'Coccyx', 'Sacrum', 'Vertebral', 'Intervertebral', 'Disc',
        # Joints and structures
        'Joint', 'Muscle', 'Tendon', 'Ligament', 'Bone', 'Tissue', 'Nerve', 'Fascia'
    }
    words = sanitized.split()
    sanitized_words = []
    # Convert medical_terms to lowercase for case-insensitive matching
    medical_terms_lower = {term.lower() for term in medical_terms}
    for word in words:
        clean_word = re.sub(r'[^\w]', '', word)
        # Check if it's a capitalized word that's not a medical term
        if clean_word.istitle() and clean_word.lower() not in medical_terms_lower and len(clean_word) > 2:
            sanitized_words.append('[name removed]')
        else:
            sanitized_words.append(word)
    sanitized = ' '.join(sanitized_words)

    # Remove phone numbers
    sanitized = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[phone removed]', sanitized)

    # Remove addresses (simple pattern)
    sanitized = re.sub(r'\b\d+\s+\w+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)\b', '[address removed]', sanitized, flags=re.IGNORECASE)

    # Clean up multiple spaces
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()

    return sanitized


def sanitize_subjective_data(inputs_dict):
    """Sanitize subjective examination data to remove PHI."""
    if not inputs_dict:
        return {}

    sanitized = {}
    for key, value in inputs_dict.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_clinical_text(value)
        else:
            sanitized[key] = value

    return sanitized


def sanitize_patient_data(data_dict):
    """Comprehensive sanitization of patient data for AI prompts."""
    sanitized = {}

    # Sanitize age/sex
    if 'age_sex' in data_dict:
        sanitized['demographics'] = sanitize_age_sex(data_dict['age_sex'])

    # Sanitize clinical histories
    if 'present_history' in data_dict:
        sanitized['present_history'] = sanitize_clinical_text(data_dict['present_history'])

    if 'past_history' in data_dict:
        sanitized['past_history'] = sanitize_clinical_text(data_dict['past_history'])

    if 'social_history' in data_dict:
        sanitized['social_history'] = sanitize_clinical_text(data_dict['social_history'])

    # Remove direct identifiers
    for field in ['name', 'patient_id', 'email', 'phone', 'address', 'contact']:
        if field in data_dict:
            sanitized[field] = '[redacted]'

    return sanitized


def flatten_docs(docs_dict: dict) -> dict:
    """Flatten nested dict-of-docs into a single {field: value} map, dropping PHI-like keys."""
    if not isinstance(docs_dict, dict):
        return {}
    flat = {}
    for _doc_id, doc in docs_dict.items():
        if not isinstance(doc, dict):
            continue
        for k, v in doc.items():
            if k in ('patient_id', 'timestamp', 'created_by', 'uid', 'mrn'):
                continue
            if v is None or v == "":
                continue
            key = k if k not in flat else f"{k}_{_doc_id}"
            flat[key] = v
    return flat


def hard_limits(text: str, items: int, kind: str = "numbered list") -> str:
    """Append a firm output constraint to a prompt."""
    return (
        text
        + f"\nReturn only a {kind} of up to {items} items. "
          "Do not include headings, explanations, references, or any extra text."
    )
