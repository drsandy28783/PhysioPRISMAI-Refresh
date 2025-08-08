import os
import io
import json
import csv
import requests
from flask import (Flask, render_template, request, redirect,session, url_for, flash,jsonify, make_response, g)
from datetime import datetime
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from xhtml2pdf import pisa
from functools import wraps
import logging
from google.api_core.exceptions import GoogleAPIError
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin.firestore import SERVER_TIMESTAMP
from google.cloud.firestore_v1.base_query import FieldFilter
import openai
# some versions of the OpenAI pip package don’t expose openai.error
try:
    from openai.error import OpenAIError
except ImportError:
    # fall back so our except‐clauses below still work
    OpenAIError = Exception


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# initialize OpenAI
openai.api_key = os.environ['OPENAI_API_KEY']

FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY')
sa_json = os.environ['GOOGLE_APPLICATION_CREDENTIALS_JSON']
cred_dict = json.loads(sa_json)
# cred_dict['project_id'] = 'YOUR-PROJECT-ID'  # Only needed if your JSON is missing it
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred, {'projectId': cred_dict.get('project_id')})
db = firestore.client()


def get_ai_suggestion(prompt: str) -> str:
    """
        Sends a prompt to OpenAI and returns the assistant's reply.
        """
    # Using the v1+ client syntax
    resp = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{
            "role": "system",
            "content": "You are a helpful clinical reasoning assistant."
        }, {
            "role": "user",
            "content": prompt
        }],
        temperature=0.7,
        max_tokens=200)
    # The path to the text is the same
    return resp.choices[0].message.content


def log_action(user_id, action, details=None):
    """Append an entry into Firestore `audit_logs` collection."""
    entry = {
        'user_id': user_id,
        'action': action,
        'details': details,
        'timestamp': SERVER_TIMESTAMP
    }
    db.collection('audit_logs').add(entry)

def fetch_patient(patient_id):
    """Return a patient dict or None if not found or on error."""
    try:
        doc = db.collection('patients').document(patient_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data['patient_id'] = doc.id
        return data
    except GoogleAPIError as e:
        logger.error(f"Firestore error fetching patient {patient_id}: {e}", exc_info=True)
        return None




app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
app.secret_key =os.environ.get('SECRET_KEY', 'dev_default_key')
app.config['WTF_CSRF_ENABLED'] = True
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d-%m-%Y'):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime(format)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# make sure you set a secret key for sessions + CSRF 
# initialize CSRF protection on *all* POST routes by default
csrf = CSRFProtect(app)


# ─── CSRF ERROR HANDLING ────────────────────────────
@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    flash("The form you submitted is invalid or has expired. Please try again.", "error")
    return redirect(request.referrer or url_for('index')), 400

# ─── EXPOSE CSRF TOKEN TO TEMPLATES & AJAX ───────────
@app.after_request
def set_csrf_cookie(response):
    response.set_cookie('csrf_token', generate_csrf())
    return response

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)




def login_required(approved_only=True):
    def real_decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect('/login')
            if approved_only and session.get('is_admin') != 1 and session.get('approved') == 0:
                return "Access denied. Awaiting approval by admin."
            return f(*args, **kwargs)
        return decorated_function
    return real_decorator


def patient_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        patient_id = kwargs.get('patient_id')
        if not patient_id:
            return "Patient ID is required.", 400

        doc = db.collection('patients').document(patient_id).get()
        if not doc.exists:
            return "Patient not found.", 404

        patient = doc.to_dict()
        if session.get('is_admin') == 0 and patient.get('physio_id') != session.get('user_id'):
            return "Access denied.", 403

        g.patient = patient
        return f(*args, **kwargs)
    return decorated_function




@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect('/register')

        try:
            # Firebase Auth: Create user
            payload = {
                'email': email,
                'password': password,
                'returnSecureToken': True
            }
            r = requests.post(
                f'https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_WEB_API_KEY}',
                json=payload
            )
            result = r.json()

            if 'error' in result:
                flash('Registration failed: ' + result['error']['message'], 'danger')
                return redirect('/register')

            # Firestore: Add user document
            db.collection('users').document(email).set({
                'name': name,
                'email': email,
                'role': 'individual',
                'approved': 1,
                'active': 1,
                'is_admin': 0,
                'created_at': SERVER_TIMESTAMP
            })

            flash('Registration successful. You can now log in.', 'success')
            return redirect('/login')

        except Exception as e:
            print("Registration error:", e)
            flash("Something went wrong. Please try again.", "danger")
            return redirect('/register')

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        try:
            # Firebase Auth login
            payload = {
                'email': email,
                'password': password,
                'returnSecureToken': True
            }
            r = requests.post(
                f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}',
                json=payload
            )
            result = r.json()

            if 'error' in result:
                flash('Invalid credentials', 'danger')
                return redirect('/login')

            # Firestore check
            user_doc = db.collection('users').document(email).get()
            if not user_doc.exists:
                flash('User not found in Firestore.', 'danger')
                return redirect('/login')

            user_data = user_doc.to_dict()

            if user_data.get('approved') == 1 and user_data.get('active') == 1:
                session['user_email'] = email
                session['user_name'] = user_data.get('name')
                session['user_id'] = result['localId']   # <-- Set Firebase UID here!
                session['role'] = 'individual'
                session['is_admin'] = 0
                return redirect('/dashboard')

            else:
                flash('Your account is not approved or is inactive.', 'danger')
                return redirect('/login')

        except Exception as e:
            print("Login error:", e)
            flash("Login failed due to a system error.", "danger")
            return redirect('/login')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/dashboard')
@login_required()
def dashboard():
    return render_template('dashboard.html', name=session.get('user_name'))


@app.route('/admin_dashboard')
@login_required()
def admin_dashboard():
    # only institute‑admins allowed
    if session.get('is_admin') != 1:
        return redirect(url_for('login_institute'))

    # build a query for non‑admin physios in this institute, pending approval
    users_ref = db.collection('users')
    docs = (
        users_ref
        .where(filter=FieldFilter('is_admin',   '==', 0))
        .where(filter=FieldFilter('approved',   '==', 0))
        .where(filter=FieldFilter('institute',  '==', session.get('institute')))
        .stream()
    )

    # pull the documents into a list of dicts
    pending_physios = [doc.to_dict() for doc in docs]

    # render
    return render_template(
        'admin_dashboard.html',
        pending_physios=pending_physios,
        name=session.get('user_name'),
        institute=session.get('institute')
    )


 
@app.route('/view_patients')
@login_required()
def view_patients():
    name_f = request.args.get('name')
    id_f = request.args.get('patient_id')

    try:
        # Get the current user's Firebase UID from the session
        current_uid = session.get('user_id')  # Should be Firebase UID

        # Start query with filter
        q = db.collection('patients').where('physiotherapistId', '==', current_uid)

        # Apply filters
        if name_f:
            # This is a workaround; Firestore does not support contains, only prefix with >= and < queries.
            q = q.where('patientName', '>=', name_f).where('patientName', '<=', name_f + '\uf8ff')
        if id_f:
            q = q.where('id', '==', id_f)

        docs = q.stream()
        patients = [doc.to_dict() for doc in docs]

    except Exception as e:
        logger.error(f"Firestore error in view_patients: {e}", exc_info=True)
        flash("Could not load your patients list. Please try again later.", "error")
        return redirect(url_for('dashboard'))

    return render_template('view_patients.html', patients=patients)




@app.route('/register_institute', methods=['GET', 'POST'])
def register_institute():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        phone = request.form['phone'].strip()
        password = request.form['password']
        institute = request.form['institute'].strip()

        try:
            # Firebase Auth: Create user
            payload = {
                'email': email,
                'password': password,
                'returnSecureToken': True
            }
            r = requests.post(
                f'https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_WEB_API_KEY}',
                json=payload
            )
            result = r.json()

            if 'error' in result:
                flash('Registration failed: ' + result['error']['message'], 'danger')
                return redirect('/register_institute')

            # Firestore: Save admin user
            db.collection('users').document(email).set({
                'name': name,
                'email': email,
                'phone': phone,
                'institute': institute,
                'role': 'institute_admin',
                'approved': 1,
                'active': 1,
                'is_admin': 1,
                'created_at': SERVER_TIMESTAMP
            })

            flash('Institute admin registered successfully. You can now log in.', 'success')
            return redirect('/login_institute')

        except Exception as e:
            print("Register institute error:", e)
            flash("Something went wrong. Please try again.", "danger")
            return redirect('/register_institute')

    return render_template('register_institute.html')

@app.route('/login_institute', methods=['GET', 'POST'])
def login_institute():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        try:
            # Firebase Auth login
            payload = {
                'email': email,
                'password': password,
                'returnSecureToken': True
            }
            r = requests.post(
                f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}',
                json=payload
            )
            result = r.json()

            if 'error' in result:
                flash('Invalid credentials', 'danger')
                return redirect('/login_institute')

            # Firestore check
            user_doc = db.collection('users').document(email).get()
            if not user_doc.exists:
                flash('User not found in Firestore.', 'danger')
                return redirect('/login_institute')

            user_data = user_doc.to_dict()

            if user_data.get('approved') == 1 and user_data.get('active') == 1:
                session['user_email'] = email
                session['user_name'] = user_data.get('name')
                session['user_id'] = result['localId'] # Use Firebase UID
                session['role'] = user_data.get('role')
                session['is_admin'] = user_data.get('is_admin', 0)
                session['institute'] = user_data.get('institute')

                if user_data.get('is_admin') == 1:
                    return redirect('/admin_dashboard')
                else:
                    return redirect('/dashboard')
            else:
                flash('Your account is not approved or is inactive.', 'danger')
                return redirect('/login_institute')

        except Exception as e:
            print("Login institute error:", e)
            flash("Login failed due to a system error.", "danger")
            return redirect('/login_institute')

    return render_template('login_institute.html')


@app.route('/register_with_institute', methods=['GET', 'POST'])
def register_with_institute():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        phone = request.form['phone'].strip()
        password = request.form['password']
        institute = request.form['institute'].strip()

        try:
            # Firebase Auth: Create account
            payload = {
                'email': email,
                'password': password,
                'returnSecureToken': True
            }
            r = requests.post(
                f'https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_WEB_API_KEY}',
                json=payload
            )
            result = r.json()

            if 'error' in result:
                flash('Registration failed: ' + result['error']['message'], 'danger')
                return redirect('/register_with_institute')

            # Save as unapproved institute physio
            db.collection('users').document(email).set({
                'name': name,
                'email': email,
                'phone': phone,
                'institute': institute,
                'role': 'institute_physio',
                'approved': 0,
                'active': 1,
                'is_admin': 0,
                'created_at': SERVER_TIMESTAMP
            })

            flash('Registration request submitted. Please wait for admin approval.', 'info')
            return redirect('/login_institute')

        except Exception as e:
            print("Register with institute error:", e)
            flash("Something went wrong. Please try again.", 'danger')
            return redirect('/register_with_institute')

    # Dropdown list: Get all institute names from approved admins
    institute_admins = db.collection('users').where('is_admin', '==', 1).stream()
    institutes = [{'institute': admin.to_dict().get('institute')} for admin in institute_admins]

    return render_template('register_with_institute.html', institutes=institutes)

    

@app.route('/approve_physios', methods=['GET', 'POST'])
@login_required()
def approve_physios():
    current_user_email = session.get('user_email')
    current_user_doc = db.collection('users').document(current_user_email).get()

    if not current_user_doc.exists:
        flash('Current user not found.', 'danger')
        return redirect('/admin_dashboard')

    current_user_data = current_user_doc.to_dict()
    institute_name = current_user_data.get('institute')

    # Fetch all physios from the same institute who are not approved
    pending = db.collection('users') \
        .where('role', '==', 'institute_physio') \
        .where('approved', '==', 0) \
        .where('institute', '==', institute_name) \
        .stream()

    pending_physios = [doc.to_dict() for doc in pending]

    return render_template('approve_physios.html', physios=pending_physios)



@app.route('/approve_user/<user_email>', methods=['POST'])
@login_required()
def approve_user(user_email):
    user_email = user_email.lower()
    try:
        db.collection('users').document(user_email).update({
            'approved': 1
        })
        flash('User approved successfully.', 'success')
    except Exception as e:
        print("Approval error:", e)
        flash('Error approving user.', 'danger')
    return redirect('/approve_physios')


@app.route('/reject_user/<user_email>', methods=['POST'])
@login_required()
def reject_user(user_email):
    user_email = user_email.lower()
    try:
        db.collection('users').document(user_email).delete()
        flash('User rejected and deleted successfully.', 'info')
    except Exception as e:
        print("Rejection error:", e)
        flash('Error rejecting user.', 'danger')
    return redirect('/approve_physios')




@app.route('/audit_logs')
@login_required()
def audit_logs():
    logs = []

    if session.get('is_admin') == 1:
        # Admin: fetch logs for all users in their institute
        users = db.collection('users') \
                  .where('institute', '==', session['institute']) \
                  .stream()
        user_map = {u.id: u.to_dict() for u in users}
        user_ids = list(user_map.keys())

        for uid in user_ids:
            entries = db.collection('audit_logs').where('user_id', '==', uid).stream()
            for e in entries:
                data = e.to_dict()
                data['name'] = user_map[uid]['name']
                logs.append(data)

    elif session.get('is_admin') == 0:
        # Individual physio: only their logs
        entries = db.collection('audit_logs').where('user_id', '==', session['user_id']).stream()
        for e in entries:
            data = e.to_dict()
            data['name'] = session['user_name']
            logs.append(data)

    # Sort by timestamp descending
    logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

    return render_template('audit_logs.html', logs=logs)

@app.route('/export_audit_logs')
@login_required()
def export_audit_logs():
    if session.get('is_admin') != 1:
        return redirect('/login_institute')

    users = db.collection('users') \
              .where('institute', '==', session['institute']) \
              .stream()
    user_map = {u.id: u.to_dict() for u in users}
    user_ids = list(user_map.keys())

    logs = []
    for uid in user_ids:
        entries = db.collection('audit_logs').where('user_id', '==', uid).stream()
        for e in entries:
            log = e.to_dict()
            logs.append([
                user_map[uid]['name'],
                log.get('action', ''),
                log.get('details', ''),
                log.get('timestamp', '')
            ])

    # Prepare CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['User', 'Action', 'Details', 'Timestamp'])
    writer.writerows(logs)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=audit_logs.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


@app.route('/add_patient', methods=['GET', 'POST'])
@login_required()
def add_patient():
    if request.method == 'POST':
        # 1) collect form values
        data = {
            'physio_id':       session.get('user_id'),
            'name':            request.form['name'],
            'age_sex':         request.form['age_sex'],
            'contact':         request.form['contact'],
            'present_history': request.form['present_history'],
            'past_history':    request.form.get('past_history', '').strip(),
            'institute':       session.get('institute'),
            'created_at':      SERVER_TIMESTAMP
        }

        # 2) Create a new patient document with an auto-generated ID
        new_patient_ref = db.collection('patients').document()
        pid = new_patient_ref.id
        data['patient_id'] = pid

        # 3) Set the data for the new patient
        new_patient_ref.set(data)

        log_action(session.get('user_id'),
                   'Add Patient',
                   f"Added {data['name']} (ID: {pid})")

        # 4) redirect to the next screen
        return redirect(url_for('subjective', patient_id=pid))

    # GET → render the blank form
    return render_template('add_patient.html')





@app.route('/subjective/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def subjective(patient_id):
    patient = g.patient
    if request.method == 'POST':
        fields = [
            'body_structure', 'body_function', 'activity_performance',
            'activity_capacity', 'contextual_environmental',
            'contextual_personal'
        ]
        entry = {f: request.form[f] for f in fields}
        entry['patient_id'] = patient_id
        entry['timestamp'] = SERVER_TIMESTAMP
        db.collection('subjective_examination').add(entry)
        return redirect(f'/perspectives/{patient_id}')
    return render_template('subjective.html', patient_id=patient_id, patient=patient)



@app.route('/perspectives/<path:patient_id>', methods=['GET','POST'])
@login_required()
@patient_access_required
def perspectives(patient_id):
    if request.method == 'POST':
        # ← UPDATED TO MATCH YOUR HTML FIELD NAMES
        keys = [
            'knowledge',
            'attribution',
            'expectation',               # was 'illness_duration'
            'consequences_awareness',
            'locus_of_control',
            'affective_aspect'
        ]

        # collect form values safely
        entry = {
            k: request.form.get(k, '')  # use .get() to avoid KeyError
            for k in keys
        }
        entry.update({
            'patient_id': patient_id,
            'timestamp': SERVER_TIMESTAMP
        })

        # save to your collection
        db.collection('patient_perspectives').add(entry)

        # redirect to the next screen
        return redirect(url_for('initial_plan', patient_id=patient_id))

    # GET: render the form
    return render_template('perspectives.html', patient_id=patient_id)


@app.route('/initial_plan/<path:patient_id>', methods=['GET','POST'])
@login_required()
@patient_access_required
def initial_plan(patient_id):
    if request.method == 'POST':
        sections = ['active_movements','passive_movements','passive_over_pressure',
                    'resisted_movements','combined_movements','special_tests','neuro_dynamic_examination']
        entry = {'patient_id': patient_id, 'timestamp': SERVER_TIMESTAMP}
        for s in sections:
            entry[s] = request.form.get(s)
            entry[f"{s}_details"] = request.form.get(f"{s}_details", '')
        db.collection('initial_plan').add(entry)
        return redirect(f'/patho_mechanism/{patient_id}')
    return render_template('initial_plan.html', patient_id=patient_id)



@app.route('/patho_mechanism/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def patho_mechanism(patient_id):
    if request.method == 'POST':
        keys = [
            'area_involved', 'presenting_symptom', 'pain_type', 'pain_nature',
            'pain_severity', 'pain_irritability', 'possible_source',
            'stage_healing'
        ]
        entry = {k: request.form[k] for k in keys}
        entry['patient_id'] = patient_id
        entry['timestamp'] = SERVER_TIMESTAMP
        db.collection('patho_mechanism').add(entry)
        return redirect(f'/chronic_disease/{patient_id}')
    return render_template('patho_mechanism.html', patient_id=patient_id)


@app.route('/chronic_disease/<path:patient_id>', methods=['GET','POST'])
@login_required()
@patient_access_required
def chronic_disease(patient_id):
    if request.method == 'POST':
        # Pull back *all* selected options as a Python list:
        causes = request.form.getlist('maintenance_causes')
        entry = {
            'patient_id': patient_id,
            'causes': causes,                            # <- store the list
            'specific_factors': request.form.get('specific_factors', ''),
            'timestamp': SERVER_TIMESTAMP
        }
        db.collection('chronic_diseases').add(entry)
        return redirect(f'/clinical_flags/{patient_id}')
    return render_template('chronic_disease.html', patient_id=patient_id)


@app.route('/clinical_flags/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def clinical_flags(patient_id):
    if request.method == 'POST':
        entry = {
            'patient_id': patient_id,
            'red_flags':     request.form.get('red_flags', ''),
            'yellow_flags':  request.form.get('yellow_flags', ''),
            'black_flags':   request.form.get('black_flags', ''),
            'blue_flags':    request.form.get('blue_flags', ''),
            'timestamp':     SERVER_TIMESTAMP
        }
        db.collection('clinical_flags').add(entry) 
        return redirect(url_for('objective_assessment', patient_id=patient_id))


    return render_template('clinical_flags.html', patient_id=patient_id)


@app.route('/objective_assessment/<path:patient_id>', methods=['GET','POST'])
@csrf.exempt
@login_required()
@patient_access_required
def objective_assessment(patient_id):
    if request.method == 'POST':
        entry = {
            'patient_id': patient_id,
            'plan':          request.form['plan'],
            'plan_details':  request.form.get('plan_details',''),
            'timestamp':     SERVER_TIMESTAMP
        }
        db.collection('objective_assessments').add(entry)
        return redirect(f'/provisional_diagnosis/{patient_id}')

    return render_template('objective_assessment.html', patient_id=patient_id)



@app.route('/provisional_diagnosis/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def provisional_diagnosis(patient_id):
    if request.method == 'POST':
        keys = [
            'likelihood', 'structure_fault', 'symptom', 'findings_support',
            'findings_reject', 'hypothesis_supported'
        ]
        entry = {k: request.form[k] for k in keys}
        entry['patient_id'] = patient_id
        entry['timestamp'] = SERVER_TIMESTAMP
        db.collection('provisional_diagnosis').add(entry)
        return redirect(f'/smart_goals/{patient_id}')
    return render_template('provisional_diagnosis.html', patient_id=patient_id)


@app.route('/smart_goals/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def smart_goals(patient_id):
    if request.method == 'POST':
        keys = [
            'patient_goal', 'baseline_status', 'measurable_outcome',
            'time_duration'
        ]
        entry = {k: request.form[k] for k in keys}
        entry['patient_id'] = patient_id
        entry['timestamp'] = SERVER_TIMESTAMP
        db.collection('smart_goals').add(entry)
        return redirect(f'/treatment_plan/{patient_id}')
    return render_template('smart_goals.html', patient_id=patient_id)


@app.route('/treatment_plan/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def treatment_plan(patient_id):
    if request.method == 'POST':
        keys = ['treatment_plan', 'goal_targeted', 'reasoning', 'reference']
        entry = {k: request.form[k] for k in keys}
        entry['patient_id'] = patient_id
        entry['timestamp'] = SERVER_TIMESTAMP
        db.collection('treatment_plan').add(entry)
        return redirect('/dashboard')
    return render_template('treatment_plan.html', patient_id=patient_id)

@app.route('/follow_ups/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def follow_ups(patient_id):
    patient = g.patient
    if request.method == 'POST':
        entry = {
            'patient_id':      patient_id,
            'session_number':  int(request.form['session_number']),
            'session_date':    request.form['session_date'],
            'grade':           request.form['grade'],
            'perception':      request.form['belief_treatment'],
            'feedback':        request.form['belief_feedback'],
            'treatment_plan':  request.form['treatment_plan'],
            'timestamp':       SERVER_TIMESTAMP
        }
        db.collection('follow_ups').add(entry)
        log_action(session['user_id'], 'Add Follow-Up',
                   f"Follow-up #{entry['session_number']} for {patient_id}")
        return redirect(f'/follow_ups/{patient_id}')

    # 3) on GET, pull all existing
    docs = (db.collection('follow_ups')
              .where('patient_id', '==', patient_id)
              .order_by('session_number')
              .stream())
    followups = [d.to_dict() for d in docs]

    return render_template('follow_ups.html',                       patient=patient, patient_id=patient_id,
                           followups=followups)

# ─── VIEW FOLLOW-UPS ROUTE ─────────────────────────────────────────────
@app.route('/view_follow_ups/<path:patient_id>')
@login_required()
@patient_access_required
def view_follow_ups(patient_id):
    patient = g.patient
    docs = (db.collection('follow_ups')
              .where('patient_id', '==', patient_id)
              .order_by('session_date', direction=firestore.Query.DESCENDING)
              .stream())
    followups = [d.to_dict() for d in docs]

    return render_template('view_follow_ups.html', patient=patient, followups=followups)


@app.route('/edit_patient/<path:patient_id>', methods=['GET', 'POST'])
@login_required()
@patient_access_required
def edit_patient(patient_id):
    patient = g.patient
    doc_ref = db.collection('patients').document(patient_id)

    if request.method == 'POST':
        updated_data = {
            'name': request.form['name'],
            'age_sex': request.form['age_sex'],
            'contact': request.form['contact']
        }
        doc_ref.update(updated_data)
        log_action(session['user_id'], 'Edit Patient', f"Edited patient {patient_id}")
        return redirect(url_for('view_patients'))

    return render_template('edit_patient.html', patient=patient, patient_id=patient_id)


@app.route('/patient_report/<path:patient_id>')
@login_required()
@patient_access_required
def patient_report(patient_id):
    patient = g.patient
    # fetch each section
    def fetch_one(coll):
        d = db.collection(coll).where('patient_id', '==',
                                      patient_id).limit(1).get()
        return d[0].to_dict() if d else {}

    subjective = fetch_one('subjective_examination')
    perspectives = fetch_one('patient_perspectives')
    diagnosis = fetch_one('provisional_diagnosis')
    treatment = fetch_one('treatment_plan')
    goals = fetch_one('smart_goals')
    return render_template('patient_report.html',
                           patient=patient,
                           subjective=subjective,
                           perspectives=perspectives,
                           diagnosis=diagnosis,
                           goals=goals,
                           treatment=treatment)


@app.route('/download_report/<path:patient_id>')
@login_required()
@patient_access_required
def download_report(patient_id):
    patient = g.patient
    # 2) Fetch each section for the report
    def fetch_one(coll):
        result = db.collection(coll) \
                     .where('patient_id', '==', patient_id) \
                     .limit(1).get()
        return result[0].to_dict() if result else {}

    subjective   = fetch_one('subjective_examination')
    perspectives = fetch_one('patient_perspectives')
    diagnosis    = fetch_one('provisional_diagnosis')
    goals        = fetch_one('smart_goals')
    treatment    = fetch_one('treatment_plan')

    # 3) Render the HTML template
    rendered = render_template(
        'patient_report.html',
        patient=patient,
        subjective=subjective,
        perspectives=perspectives,
        diagnosis=diagnosis,
        goals=goals,
        treatment=treatment
    )

    # 4) Generate PDF
    pdf = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(rendered), dest=pdf)
    if pisa_status.err:
        return "Error generating PDF", 500

    # 5) Return the PDF
    response = make_response(pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = (
        f'attachment; filename={patient_id}_report.pdf'
    )
    log_action(
        session.get('user_id'),
        'Download Report',
        f"Downloaded PDF report for patient {patient_id}"
    )
    return response



@app.route('/manage_users')
@login_required()
def manage_users():
    if session.get('is_admin') != 1:
        return "Access Denied: Admins only."
    docs = db.collection('users')\
             .where('is_admin','==',0)\
             .where('approved','==',1)\
             .where('institute','==',session.get('institute'))\
             .stream()
    users = [d.to_dict() for d in docs]
    return render_template('manage_users.html', users=users)


@app.route('/deactivate_user/<user_email>')
@login_required()
def deactivate_user(user_email):
    if session.get('is_admin') != 1:
        return "Access Denied"
    db.collection('users').document(user_email).update({'active': 0})
    log_action(session.get('user_id'), 'Deactivate User',
               f"User {user_email} was deactivated")
    return redirect('/manage_users')


@app.route('/reactivate_user/<user_email>')
@login_required()
def reactivate_user(user_email):
    if session.get('is_admin') != 1:
        return "Access Denied"
    db.collection('users').document(user_email).update({'active': 1})
    log_action(session.get('user_id'), 'Reactivate User',
               f"User {user_email} was reactivated")
    return redirect('/manage_users')



@app.route('/ai_suggestion/past_questions', methods=['POST'])
@csrf.exempt
@login_required()
def ai_past_questions():
    data = request.get_json() or {}
    age_sex = data.get('age_sex', '').strip()
    present_hist = data.get('present_history', '').strip()

    prompt = (
    "Generate 5 short, clear follow-up questions suitable for a physiotherapy intake form. "
    "Focus only on comorbidities, risk factors, and symptom timeline. "
    "Do not include or request any patient names, identifiers, or location data.\n"
    f"Age/Sex: {age_sex}\n"
    f"Present history: {present_hist}\n"
    "Return the questions as a numbered list."
)
    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500



@app.route('/ai_suggestion/provisional_diagnosis', methods=['POST'])
@csrf.exempt
@login_required()
def ai_provisional_diagnosis():
    data = request.get_json() or {}
    age_sex    = data.get('age_sex', '').strip()
    present_hist = data.get('present_history', '').strip()
    past_hist    = data.get('past_history', '').strip()

    prompt = (
        "Given the following patient case (no names or identifying details):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present_hist}\n"
        f"Past history: {past_hist}\n"
        "List up to two likely provisional diagnoses for physiotherapy with a brief rationale for each. "
        "Format as a numbered list."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500



@app.route('/ai_suggestion/subjective/<field>', methods=['POST'])
@login_required()
def ai_subjective_field(field):
    data = request.get_json() or {}
    age_sex     = data.get('age_sex', '').strip()
    present_hist= data.get('present_history', '').strip()
    past_hist   = data.get('past_history', '').strip()
    inputs      = data.get('inputs', {})

    # Compose a brief summary of relevant prior subjective findings (excluding current field)
    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}"
        for k, v in inputs.items() if k != field and v
    )

    prompt = (
        "You are a physiotherapy clinical assistant. Do not use or request any patient names or identifiers.\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present_hist}\n"
        f"Past history: {past_hist}\n"
        f"Other subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"\nFor **{field.replace('_', ' ').title()}**, suggest 2–3 open-ended questions a physiotherapist should ask to clarify this aspect. "
        "Format as a numbered list."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/ai_suggestion/subjective_diagnosis', methods=['POST'])
@login_required()
def ai_subjective_diagnosis():
    data = request.get_json() or {}
    age_sex     = data.get('age_sex', '').strip()
    present_hist= data.get('present_history', '').strip()
    past_hist   = data.get('past_history', '').strip()
    inputs      = data.get('inputs', {})

    findings = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}"
        for k, v in inputs.items() if v
    )

    prompt = (
        "Given the following (no names or patient identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present_hist}\n"
        f"Past history: {past_hist}\n"
        f"Subjective findings:\n{findings if findings else 'None'}\n"
        "List up to 2 likely provisional diagnoses for physiotherapy, each with a one-sentence rationale. Format as a numbered list."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/ai_suggestion/perspectives/<field>', methods=['POST'])
@login_required()
def ai_perspectives_field(field):
    data = request.get_json() or {}
    prev   = data.get('previous', {})

    age_sex = prev.get('age_sex', '')
    present = prev.get('present_history', '')
    past    = prev.get('past_history', '')
    subj    = prev.get('subjective', {})
    perspectives = prev.get('perspectives', {})

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in perspectives.items() if k != field and v
    )

    prompt = (
        "Given this case (do not use any names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives recorded:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        f"\nFor **{field.replace('_', ' ').title()}**, suggest 2–3 open-ended questions a physiotherapist should ask to clarify this perspective. Format as a numbered list."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/ai_suggestion/perspectives_diagnosis', methods=['POST'])
@login_required()
def ai_perspectives_diagnosis():
    data = request.get_json() or {}
    prev   = data.get('previous', {})

    age_sex = prev.get('age_sex', '')
    present = prev.get('present_history', '')
    past    = prev.get('past_history', '')
    subj    = prev.get('subjective', {})
    persps  = data.get('inputs', {})

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in persps.items() if v
    )

    prompt = (
        "Given this case (do not use any names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        "Based on this information, provide up to 2 provisional clinical impressions for physiotherapy, each 1–2 sentences and integrating the patient perspectives. Format as a numbered list."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500



@app.route('/ai_suggestion/initial_plan/<field>', methods=['POST'])
@login_required()
def ai_initial_plan_field(field):
    data = request.get_json() or {}
    prev      = data.get('previous', {})
    selection = data.get('selection', '').strip()

    age_sex = prev.get('age_sex', '')
    present = prev.get('present_history', '')
    past    = prev.get('past_history', '')
    subj    = prev.get('subjective', {})
    persp   = prev.get('perspectives', {})

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in persp.items() if v
    )

    prompt = (
        "Given this case (no patient names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        f"\nThe therapist marked **{field.replace('_', ' ').title()}** as **{selection}**. "
        "Interpret this category as:\n"
        "- 'Mandatory assessment': essential tests\n"
        "- 'Assessment with precaution': tests needing caution\n"
        "- 'Absolutely contraindicated': tests to avoid\n"
        "List 2–4 specific assessment tests or maneuvers that fit this category as a bullet list."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500



@app.route('/ai_suggestion/initial_plan_summary', methods=['POST'])
@login_required()
def ai_initial_plan_summary():
    data = request.get_json() or {}
    prev        = data.get('previous', {})
    assessments = data.get('assessments', {})

    age_sex = prev.get('age_sex', '')
    present = prev.get('present_history', '')
    past    = prev.get('past_history', '')
    subj    = prev.get('subjective', {})
    persp   = prev.get('perspectives', {})

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in persp.items() if v
    )
    assessments_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {assessments[k]['choice']} ({assessments[k]['details']})"
        for k in assessments if assessments[k].get('choice') or assessments[k].get('details')
    )

    prompt = (
        "Given this case (no patient names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        f"Assessment plan:\n{assessments_summary if assessments_summary else 'None'}\n"
        "In 2–3 sentences, summarize the assessment findings and list up to two likely provisional diagnoses."
    )

    try:
        summary = get_ai_suggestion(prompt)
        return jsonify({'summary': summary})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500


@app.route('/ai_suggestion/patho/possible_source', methods=['POST'])
@csrf.exempt
@login_required()
def ai_patho_source():
    data = request.get_json() or {}
    prev      = data.get('previous', {})
    selection = data.get('selection', '').strip()

    age_sex = prev.get('age_sex', '')
    present = prev.get('present_history', '')
    past    = prev.get('past_history', '')
    subj    = prev.get('subjective', {})
    persp   = prev.get('perspectives', {})
    assess  = prev.get('assessments', {})

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in persp.items() if v
    )
    assessments_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v['choice']}" for k, v in assess.items() if v.get('choice')
    )

    prompt = (
        "Given this case (do not use patient names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        f"Assessment plan:\n{assessments_summary if assessments_summary else 'None'}\n"
        f"\nThe therapist marked Possible Source of Symptoms as: {selection}.\n"
        "Describe 2–3 concise, plausible anatomical or physiological mechanisms explaining how this source could cause the patient's symptoms. Format as a numbered list."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500



@app.route('/ai_suggestion/chronic/specific_factors', methods=['POST'])
@csrf.exempt
@login_required()
def ai_chronic_factors():
    data = request.get_json() or {}
    prev           = data.get('previous', {})
    text_input     = data.get('input', '').strip()
    causes_selected= data.get('causes', [])

    age_sex = prev.get('age_sex', '')
    present = prev.get('present_history', '')
    past    = prev.get('past_history', '')
    subj    = prev.get('subjective', {})
    persp   = prev.get('perspectives', {})
    assess  = prev.get('assessments', {})

    subjective_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in persp.items() if v
    )
    assessments_summary = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v.get('choice')}" for k, v in assess.items() if v.get('choice')
    )

    causes_str = ", ".join(causes_selected) if causes_selected else "None"

    prompt = (
        "Given this case (no patient names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        f"Assessment plan:\n{assessments_summary if assessments_summary else 'None'}\n"
        f"Maintenance causes indicated: {causes_str}\n"
        f"Specific chronic factors described: {text_input if text_input else 'None'}\n"
        "List 3–5 focused, open-ended questions a physiotherapist should ask to clarify these chronic contributing factors."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500



@app.route('/ai_suggestion/clinical_flags/<patient_id>/suggest', methods=['POST'])
@csrf.exempt
@login_required()
@patient_access_required
def clinical_flags_suggest(patient_id):
    data = request.get_json() or {}
    prev  = data.get('previous', {})
    field = data.get('field', '')
    text  = data.get('text', '').strip()

    # Determine relevancy hints (optional, use your existing logic)
    relevancy_hints = []
    if prev.get('subjective', {}).get('pain_irritability') == 'Present':
        relevancy_hints.append('Psychosocial risk factors (Yellow Flags)')
    if prev.get('assessments', {}).get('special_tests', {}).get('choice') == 'Absolutely Contraindicated':
        relevancy_hints.append('System/Environment barriers (Black Flags)')

    age_sex = prev.get('age_sex', '')
    present = prev.get('present_history', '')
    past    = prev.get('past_history', '')
    subj    = prev.get('subjective', {})
    persp   = prev.get('perspectives', {})
    assess  = prev.get('assessments', {})

    subjective_summary = "\n".join(
        f"- {k.title()}: {v}" for k, v in subj.items() if v
    )
    perspectives_summary = "\n".join(
        f"- {k.title()}: {v}" for k, v in persp.items() if v
    )
    assessments_summary = "\n".join(
        f"- {k.title()}: {v.get('choice')}" for k, v in assess.items() if v.get('choice')
    )
    flags_summary = ", ".join(relevancy_hints) if relevancy_hints else "General flags"

    prompt = (
        "Given this case (no patient names or identifiers):\n"
        f"Age/Sex: {age_sex}\n"
        f"Present history: {present}\n"
        f"Past history: {past}\n"
        f"Subjective findings:\n{subjective_summary if subjective_summary else 'None'}\n"
        f"Perspectives:\n{perspectives_summary if perspectives_summary else 'None'}\n"
        f"Assessment plan:\n{assessments_summary if assessments_summary else 'None'}\n"
        f"Relevant clinical flags: {flags_summary}\n"
        f"You are focusing on: {field.replace('_', ' ').title()} - {text}\n"
        "List 3–5 open-ended follow-up questions a physiotherapist should ask to further explore this flag."
    )

    try:
        suggestion = get_ai_suggestion(prompt)
        return jsonify({'suggestions': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error.'}), 500



    # 10) Objective Assessment Suggestions
@app.route('/objective_assessment/<patient_id>/suggest', methods=['POST'])
@login_required(approved_only=False)
@patient_access_required
def objective_assessment_suggest(patient_id):
    data = request.get_json() or {}
    field  = data.get('field')
    choice = data.get('value')

    prompt = (
        "A physiotherapist is selecting options during an objective assessment (do not use patient names or identifiers). "
        f"For the '{field}' section, they have chosen: {choice}. "
        "List 3–5 specific assessment actions or tests that should be performed next."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500

@app.route('/ai_suggestion/objective_assessment/<field>', methods=['POST'])
@login_required(approved_only=False)
def objective_assessment_field_suggest(field):
    """
    Suggest 3–5 specific objective assessments based on the selected field.
    """
    data = request.get_json() or {}
    choice = data.get('value', '')

    prompt = (
        "A physiotherapist is selecting options during an objective assessment (do not use patient names or identifiers). "
        f"For the '{field}' section, they have chosen: {choice}. "
        "List 3–5 specific assessment actions or tests that should be performed next."
    )

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500


@app.route('/provisional_diagnosis_suggest/<patient_id>')
@login_required()
@patient_access_required
def provisional_diagnosis_suggest(patient_id):
    field = request.args.get('field', '')

    # Fetch patient document
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return jsonify({'suggestion': ''}), 404
    patient = doc.to_dict()

    # Build prior data (add more as needed)
    prev = {
        'age_sex': patient.get('age_sex', ''),
        'present_complaint': patient.get('present_complaint', ''),
        # ...extend with more data if required
    }

    # Define PHI-safe prompt templates
    prompts = {
        'likelihood':
            "Given all the prior clinical data (no names or identifiers):\n"
            f"Age/Sex: {prev['age_sex']}\nPresenting complaint: {prev['present_complaint']}\n"
            "Suggest how likely provisional diagnoses should be phrased.",
        'structure_fault':
            "Based on the following patient case (do not use names or identifiers):\n"
            f"Age/Sex: {prev['age_sex']}\nPresenting complaint: {prev['present_complaint']}\n"
            "Suggest which anatomical structures to consider faulty based on the history.",
        'symptom':
            "Given this case (no identifiers):\n"
            f"Age/Sex: {prev['age_sex']}\nPresenting complaint: {prev['present_complaint']}\n"
            "Suggest clarifying questions about the patient's main symptom.",
        'findings_support':
            "From this case (no identifiers):\n"
            f"Age/Sex: {prev['age_sex']}\nPresenting complaint: {prev['present_complaint']}\n"
            "List clinical findings that would support the main provisional diagnosis.",
        'findings_reject':
            "From this case (no identifiers):\n"
            f"Age/Sex: {prev['age_sex']}\nPresenting complaint: {prev['present_complaint']}\n"
            "List common findings that would rule out the main provisional diagnosis."
    }

    prompt = prompts.get(field, f"Help with {field} in a physiotherapy clinical case (do not use any patient names or identifiers).")

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
@login_required()
def ai_smart_goals(field):
    data = request.get_json() or {}

    # Combine all saved prior screen data
    prev = {
        **data.get('previous', {}),
        **data.get('previous_subjective', {}),
        **data.get('previous_per_spectives', {}),
        **data.get('previous_assessments', {})
    }
    text = data.get('input', '').strip()

    # Field-specific PHI-safe prompts
    prompts = {
        'patient_goal':
            "Based on the clinical context, suggest 2–3 patient-centric SMART goals the patient could aim for.",
        'baseline_status':
            "Given those goals and the patient context, what baseline status should be recorded as the starting point?",
        'measurable_outcome':
            "What measurable outcomes would you expect for these goals? List 2–3 concrete metrics.",
        'time_duration':
            "What realistic time duration (e.g., weeks or months) fits those outcomes for this patient's condition?"
    }

    # Fallback for unknown field
    base_prompt = prompts.get(field,
        f"You are a physiotherapy assistant (do not use any patient names or identifiers). Help with '{field}'."
    )

    # Add prior context, if available
    context_lines = []
    for k, v in prev.items():
        if v:
            context_lines.append(f"- {k.replace('_', ' ').title()}: {v}")
    if context_lines:
        base_prompt += "\n\nPatient clinical summary:\n" + "\n".join(context_lines)

    # Add the current input, if present
    if text:
        base_prompt += f"\n\nCurrent input: {text}"

    try:
        suggestion = get_ai_suggestion(base_prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error'}), 500




# 13) Treatment Plan Suggestions
@app.route('/ai_suggestion/treatment_plan/<field>', methods=['POST'])
@login_required()
def treatment_plan_suggest(field):
    data = request.get_json() or {}
    text_input = data.get('input', '').strip()

    # PHI-safe, field-specific prompts
    prompts = {
        'treatment_plan':
            "Given the clinical summary (no patient names or identifiers), outline 3–4 evidence-based interventions for the treatment plan.",
        'goal_targeted':
            "Given the treatment goals and clinical context, what specific goal should be targeted first?",
        'reasoning':
            "Explain the clinical reasoning that links the chosen interventions to the patient's impairments (no identifiers).",
        'reference':
            "Suggest 1–2 key references (articles or guidelines) supporting this treatment plan."
    }
    prompt = prompts.get(field,
        f"You are a physiotherapy assistant (do not use names or identifiers). Help with '{field}'."
    )

    # Optionally, include any current free-text input (without identifiers)
    if text_input:
        prompt += f"\nAdditional info: {text_input}"

    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'field': field, 'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500


@app.route('/ai_suggestion/treatment_plan_summary/<patient_id>')
@login_required()
@patient_access_required
def treatment_plan_summary(patient_id):
    """
    Gathers every saved screen for this patient and asks the AI to produce a concise treatment plan summary.
    """
    # Load patient demographics
    pat_doc = db.collection('patients').document(patient_id).get()
    patient_info = pat_doc.to_dict() if pat_doc.exists else {}

    # Helper to fetch the latest entry from a collection
    def fetch_latest(collection_name):
        coll = db.collection(collection_name) \
            .where('patient_id', '==', patient_id) \
            .order_by('timestamp', direction=firestore.Query.DESCENDING) \
            .limit(1) \
            .get()
        return coll[0].to_dict() if coll else {}

    # Pull in each screen's data
    subj     = fetch_latest('subjective_examination')
    persp    = fetch_latest('subjective_perspectives')
    assess   = fetch_latest('subjective_assessments')
    patho    = fetch_latest('pathophysiological_mechanism')
    chronic  = fetch_latest('chronic_disease_factors')
    flags    = fetch_latest('clinical_flags')
    objective= fetch_latest('objective_assessment')
    prov_dx  = fetch_latest('provisional_diagnosis')
    goals    = fetch_latest('smart_goals')
    tx_plan  = fetch_latest('treatment_plan')

    # Build a single prompt that walks the AI through each section (PHI safe)
    prompt = (
        "You are a PHI-safe clinical summarization assistant. Do not use any patient names or IDs in your answer.\n\n"
        f"Patient demographics: {patient_info.get('age_sex', 'N/A')}; "
        f"Sex: {patient_info.get('sex', 'N/A')}; "
        f"Past medical history: {patient_info.get('past_history', 'N/A')}.\n\n"

        "Subjective examination:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in subj.items() if k not in ('patient_id', 'timestamp') and v) + "\n\n"

        "Patient perspectives (ICF model):\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in persp.items() if k not in ('patient_id', 'timestamp') and v) + "\n\n"

        "Initial plan of assessment:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v.get('choice','') if isinstance(v, dict) else v}" for k, v in assess.items() if k not in ('patient_id', 'timestamp') and v) + "\n\n"

        "Pathophysiological mechanism:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in patho.items() if k not in ('patient_id', 'timestamp') and v) + "\n\n"

        "Chronic disease factors:\n"
        f"- Maintenance causes: {chronic.get('maintenance_causes','')}\n"
        f"- Specific factors: {chronic.get('specific_factors','')}\n\n"

        "Clinical flags:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in flags.items() if k not in ('patient_id', 'timestamp') and v) + "\n\n"

        "Objective assessment:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in objective.items() if k not in ('patient_id', 'timestamp') and v) + "\n\n"

        "Provisional diagnosis:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in prov_dx.items() if k not in ('patient_id', 'timestamp') and v) + "\n\n"

        "SMART goals:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in goals.items() if k not in ('patient_id', 'timestamp') and v) + "\n\n"

        "Finally, the treatment plan:\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in tx_plan.items() if k not in ('patient_id', 'timestamp') and v) + "\n\n"

        "Using all of the above, create a concise treatment plan summary paragraph "
        "that links the history, exam findings, goals, and interventions into a coherent summary (no names or identifiers)."
    )

    try:
        summary = get_ai_suggestion(prompt).strip()
        return jsonify({'summary': summary})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable. Please try again later.'}), 503
    except Exception:
        return jsonify({'error': 'An unexpected error occurred.'}), 500



@app.route('/ai_followup_suggestion/<patient_id>', methods=['POST'])
@login_required()
@patient_access_required
def ai_followup_suggestion(patient_id):
    # 1. Load patient record
    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return jsonify({'error': 'Patient not found'}), 404
    patient = doc.to_dict()

    # 2. Parse the current form data
    data = request.get_json() or {}
    session_no  = data.get('session_number')
    session_date= data.get('session_date')
    grade       = data.get('grade')
    perception  = data.get('perception')
    feedback    = data.get('feedback')

    # 3. Build a PHI-safe summary including SMART Goals
    case_summary_lines = [
        f"Age/Sex: {patient.get('age_sex', 'N/A')}",
        f"History: {patient.get('chief_complaint', '')}",
        f"Subjective: {patient.get('subjective_notes', '')}",
        f"Perspectives: {patient.get('perspectives_summary', '')}",
        f"Initial Plan: {patient.get('initial_plan_summary', '')}",
        f"SMART Goals: {patient.get('smart_goals_summary', '')}"
    ]
    case_summary = "\n".join(
        line for line in case_summary_lines if line.split(":",1)[1].strip()
    )

    # 4. Build a PHI-safe prompt (no IDs, no names)
    prompt = (
        "You are a PHI-safe clinical reasoning assistant for physiotherapy. "
        "Never include patient names or IDs in your answer.\n\n"
        "Case summary so far:\n"
        f"{case_summary}\n\n"
        "New follow-up session details:\n"
        f"- Session number: {session_no} on {session_date}\n"
        f"- Grade: {grade}\n"
        f"- Perception: {perception}\n"
        f"- Feedback: {feedback}\n\n"
        "Based on ICF guidelines, the SMART Goals above, and the new session data, "
        "suggest a focused plan for the next treatment."
    )

    # 5. Call the AI
    try:
        suggestion = get_ai_suggestion(prompt).strip()
        return jsonify({'suggestion': suggestion})
    except OpenAIError:
        return jsonify({'error': 'AI service unavailable.'}), 503
    except Exception:
        return jsonify({'error': 'Unexpected error occurred.'}), 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
