@app.route('/objective_assessment/<patient_id>/suggest', methods=['POST'])
@csrf.exempt
@login_required(approved_only=False)
@patient_access_required
def objective_assessment_suggest(patient_id):
    data = request.get_json() or {}
    field  = (data.get('field') or '').strip()
    choice = (data.get('value') or '').strip()

    # enrich with patient + previous context
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return jsonify({'error': 'Patient not found'}), 404
    patient = doc.to_dict()

    prev = _collect_prev(data, patient)

    subj_summary = "\n".join(
        f"- {k.replace('_',' ').title()}: {v}" for k, v in prev["subjective"].items() if v
    )
    assess_summary = "\n".join(
        f"- {k.replace('_',' ').title()}: {(v.get('choice','') if isinstance(v, dict) else v)}"
        for k, v in prev["assessments"].items()
        if (v if not isinstance(v, dict) else (v.get('choice') or v.get('details')))
    )

    prompt = (
        "A physiotherapist is selecting options during an objective assessment (do not use patient names or identifiers).\n"
        f"Age/Sex: {_nz(prev['age_sex'], 'Unknown')}\n"
        f"Present history: {_nz(prev['present_history'])}\n"
        f"Past history: {_nz(prev['past_history'])}\n"
        f"Subjective summary:\n{_nz(subj_summary)}\n"
        f"Assessments so far:\n{_nz(assess_summary)}\n\n"
        f"For the **{field.replace('_',' ').title()}** section, they have chosen: {_nz(choice)}.\n"
        "List 3–5 specific next assessment actions/tests and what positive/negative findings would suggest.\n"
        "Return only a numbered list (3–5 items), no extra commentary."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500


@app.route('/ai_suggestion/objective_assessment/<field>', methods=['POST'])
@csrf.exempt
@login_required(approved_only=False)
def objective_assessment_field_suggest(field):
    """Suggest 3–5 specific objective assessments based on the selected field."""
    data = request.get_json() or {}
    choice = (data.get('value') or '').strip()

    prev = _collect_prev(data)

    subj_summary = "\n".join(
        f"- {k.replace('_',' ').title()}: {v}" for k, v in prev["subjective"].items() if v
    )
    assess_summary = "\n".join(
        f"- {k.replace('_',' ').title()}: {(v.get('choice','') if isinstance(v, dict) else v)}"
        for k, v in prev["assessments"].items()
        if (v if not isinstance(v, dict) else (v.get('choice') or v.get('details')))
    )

    prompt = (
        "A physiotherapist is selecting options during an objective assessment (no names/identifiers).\n"
        f"Age/Sex: {_nz(prev['age_sex'], 'Unknown')}\n"
        f"Present history: {_nz(prev['present_history'])}\n"
        f"Past history: {_nz(prev['past_history'])}\n"
        f"Subjective summary:\n{_nz(subj_summary)}\n"
        f"Prior assessments:\n{_nz(assess_summary)}\n\n"
        f"For the **{field.replace('_',' ').title()}** section, they selected: {_nz(choice)}.\n"
        "List 3–5 next assessment actions/tests (numbered list only)."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500



@app.route('/provisional_diagnosis_suggest/<patient_id>')
@csrf.exempt
@login_required()
@patient_access_required
def provisional_diagnosis_suggest(patient_id):
    field = (request.args.get('field', '') or '').strip()

    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return jsonify({'suggestion': ''}), 404
    patient = doc.to_dict()

    # Build a richer prior summary from patient record
    prev = {
        'age_sex':          _age_sex_from({}, patient),
        'present_history': (patient.get('present_history') or patient.get('present_complaint') or '').strip(),
        'past_history':    (patient.get('past_history') or '').strip(),
        'subjective':       patient.get('subjective_inputs') or {},
        'perspectives':     patient.get('perspectives_inputs') or {},
        'assessments':      patient.get('initial_plan_assessments') or {},
    }

    subj_summary = "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in prev['subjective'].items() if v)
    persp_summary = "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in prev['perspectives'].items() if v)
    assess_summary = "\n".join(
        f"- {k.replace('_',' ').title()}: {(v.get('choice','') if isinstance(v, dict) else v)}"
        for k, v in prev['assessments'].items()
        if (v if not isinstance(v, dict) else (v.get('choice') or v.get('details')))
    )

    templates = {
        'likelihood':
            "Given the following clinical context (no identifiers):\n"
            f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
            f"Present history: {_nz(prev['present_history'])}\n"
            f"Past history: {_nz(prev['past_history'])}\n"
            f"Subjective:\n{_nz(subj_summary)}\n"
            f"Patient perspectives:\n{_nz(persp_summary)}\n"
            f"Assessments:\n{_nz(assess_summary)}\n\n"
            "List 3 likely provisional diagnoses with a one-line rationale each (numbered).",

        'structure_fault':
            "Based on the case (no identifiers):\n"
            f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
            f"Present history: {_nz(prev['present_history'])}\n"
            f"Assessments:\n{_nz(assess_summary)}\n\n"
            "List key anatomical structures likely at fault (3–5 bullets).",

        'symptom':
            "Using this case (no identifiers):\n"
            f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
            f"Present history: {_nz(prev['present_history'])}\n"
            f"Subjective:\n{_nz(subj_summary)}\n\n"
            "Suggest 3–5 clarifying questions focused on the main symptom (numbered).",

        'findings_support':
            "From this case (no identifiers):\n"
            f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
            f"Present history: {_nz(prev['present_history'])}\n"
            f"Assessments:\n{_nz(assess_summary)}\n\n"
            "List 3–5 clinical findings that would support the leading provisional diagnosis.",

        'findings_reject':
            "From this case (no identifiers):\n"
            f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
            f"Present history: {_nz(prev['present_history'])}\n"
            f"Assessments:\n{_nz(assess_summary)}\n\n"
            "List 3–5 findings that would rule out the leading provisional diagnosis."
    }

    prompt = templates.get(field,
        "You are a physiotherapy assistant (no identifiers). Provide 3 concise points on: " + (field or "provisional diagnosis")
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        logger.info(f"[server] provisional_diagnosis_suggest {field}: {suggestion}")
        return jsonify({'suggestion': suggestion})
    except OpenAIError as e:
        logger.error(f"OpenAI API error in provisional_diagnosis_suggest: {e}", exc_info=True)
        return jsonify({'suggestion': '', 'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception as e:
        logger.error(f"Unexpected error in provisional_diagnosis_suggest: {e}", exc_info=True)
        return jsonify({'suggestion': '', 'error': 'An unexpected error occurred.'}), 500






@app.route('/ai_suggestion/smart_goals/<field>', methods=['POST'])
@csrf.exempt
@login_required()
def ai_smart_goals(field):
    data = request.get_json() or {}

    # main.js sends these blobs; normalize them
    prev = {
        "age_sex":         _age_sex_from({"previous": data.get("previous") or {}}),
        "present_history": (data.get("previous", {}).get("present_history") or "").strip(),
        "past_history":    (data.get("previous", {}).get("past_history") or "").strip(),
        "subjective":       data.get("previous_subjective") or {},
        "perspectives":     data.get("previous_perspectives") or {},
        "assessments":      data.get("previous_assessments") or {},
    }
    text = (data.get('input') or '').strip()

    assess_summary = "\n".join(
        f"- {k.replace('_',' ').title()}: {(v.get('choice','') if isinstance(v, dict) else v)}"
        for k, v in prev["assessments"].items()
        if (v if not isinstance(v, dict) else (v.get('choice') or v.get('details')))
    )

    prompts = {
        'patient_goal':
            "Draft one concise patient-centric SMART goal (numbered list with 1 item).",
        'baseline_status':
            "State a clear baseline status for tracking the SMART goal (1 bullet).",
        'measurable_outcome':
            "List 2–3 measurable outcomes for the goal (numbered).",
        'time_duration':
            "Suggest a realistic timeframe (weeks/months) aligned to the goal (1–2 bullets)."
    }

    base = (
        "You are a physiotherapy assistant. Do not include or request identifiers.\n"
        f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
        f"Present history: {_nz(prev['present_history'])}\n"
        f"Assessments:\n{_nz(assess_summary)}\n"
    )
    if text:
        base += f"\nFocus area: {_nz(text)}\n"

    prompt = base + "\n" + prompts.get(
        field,
        f"Provide a concise SMART-goal suggestion for **{field.replace('_',' ').title()}** (1–3 bullets)."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error'}), 500





# 13) Treatment Plan Suggestions
# 13) Treatment Plan Suggestions
@app.route('/ai_suggestion/treatment_plan/<field>', methods=['POST'])
@csrf.exempt
@login_required()
def treatment_plan_suggest(field):
    data = request.get_json() or {}
    text_input = (data.get('input') or '').strip()
    patient_id = (data.get('patient_id') or '').strip()

    # If a patient_id is provided, pull richer context
    patient = None
    if patient_id:
        pdoc = db.collection('patients').document(patient_id).get()
        if pdoc.exists:
            patient = pdoc.to_dict()

    prev = _collect_prev({}, patient)

    prompt = (
        "You are a physiotherapy assistant. Do not use names or identifiers.\n"
        f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}\n"
        f"Present history: {_nz(prev['present_history'])}\n"
        f"Past history: {_nz(prev['past_history'])}\n"
        f"Subjective present: {_nz(', '.join([k for k,v in prev['subjective'].items() if v]))}\n"
        f"Assessments: {_nz(', '.join([k for k,v in prev['assessments'].items() if v]))}\n\n"
        f"Focus area (**{field.replace('_',' ').title()}**): {_nz(text_input)}\n\n"
        "Propose 3 concise, evidence-aligned treatment actions (bulleted)."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'field': field, 'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500



@app.route('/ai_suggestion/treatment_plan_summary/<patient_id>')
@csrf.exempt
@login_required()
@patient_access_required
def treatment_plan_summary(patient_id):
    """Gather saved screens and produce a concise, PHI-safe treatment plan summary."""
    pat_doc = db.collection('patients').document(patient_id).get()
    patient_info = pat_doc.to_dict() if pat_doc.exists else {}

    def fetch_latest(collection_name):
        coll = (
            db.collection(collection_name)
              .where('patient_id', '==', patient_id)
              .order_by('timestamp', direction=_fa_fs.Query.DESCENDING)
              .limit(1)
              .get()
        )
        return coll[0].to_dict() if coll else {}

    subj      = fetch_latest('subjective_examination')
    persp     = fetch_latest('patient_perspectives')
    assess    = fetch_latest('objective_assessments')
    patho     = fetch_latest('patho_mechanism')
    chronic   = fetch_latest('chronic_diseases')
    flags     = fetch_latest('clinical_flags')
    objective = fetch_latest('objective_assessments')
    prov_dx   = fetch_latest('provisional_diagnosis')
    goals     = fetch_latest('smart_goals')
    tx_plan   = fetch_latest('treatment_plan')

    prompt = (
        "You are a PHI-safe clinical summarization assistant. Do not use any patient names or IDs.\n\n"
        f"Patient demographics: {patient_info.get('age_sex', 'N/A')}; "
        f"Sex: {patient_info.get('sex', 'N/A')}; "
        f"Past medical history: {patient_info.get('past_history', 'N/A')}.\n\n"
        "Subjective examination:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in subj.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Patient perspectives (ICF):\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in persp.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Initial plan of assessment:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v.get('choice','') if isinstance(v, dict) else v}" for k, v in assess.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Pathophysiological mechanism:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in patho.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Chronic disease factors:\n"
        f"- Maintenance causes: {chronic.get('maintenance_causes','')}\n"
        f"- Specific factors: {chronic.get('specific_factors','')}\n\n"
        "Clinical flags:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in flags.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Objective assessment:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in objective.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Provisional diagnosis:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in prov_dx.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "SMART goals:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in goals.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Treatment plan:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v}" for k, v in tx_plan.items() if k not in ('patient_id','timestamp') and v) + "\n\n"
        "Create a concise treatment plan summary that links history, exam findings, goals, and interventions.\n"
        "Return 3–5 numbered points. No preamble."
    )

    try:
        summary = get_ai_suggestion(prompt).strip()
        return jsonify({'summary': summary})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500



@app.route('/ai_followup_suggestion/<patient_id>', methods=['POST'])
@csrf.exempt
@login_required()
@patient_access_required
def ai_followup_suggestion(patient_id):
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return jsonify({'error': 'Patient not found'}), 404
    patient = doc.to_dict()

    data = request.get_json() or {}
    prev = _collect_prev({}, patient)

    session_no    = data.get('session_number')
    session_date  = data.get('session_date')
    grade         = data.get('grade')
    perception    = data.get('perception')
    feedback      = data.get('feedback')

    case_summary = "\n".join(filter(None, [
        f"Age/Sex: {_nz(prev['age_sex'],'Unknown')}",
        f"Present history: {_nz(prev['present_history'])}",
        f"Past history: {_nz(prev['past_history'])}",
        f"Subjective: {_nz(', '.join([k for k,v in prev['subjective'].items() if v]))}",
        f"Assessments: {_nz(', '.join([k for k,v in prev['assessments'].items() if v]))}",
    ]))

    prompt = (
        "You are a PHI-safe clinical reasoning assistant for physiotherapy. Never include patient names or IDs.\n\n"
        "Case summary so far:\n"
        f"{case_summary}\n\n"
        "New follow-up session details:\n"
        f"- Session number: {_nz(session_no)} on {_nz(session_date)}\n"
        f"- Grade: {_nz(grade)}\n"
        f"- Perception: {_nz(perception)}\n"
        f"- Feedback: {_nz(feedback)}\n\n"
        "Suggest the next treatment session focus (2–3 bullets) aligned with prior findings and any SMART goals."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error occurred.'}), 500