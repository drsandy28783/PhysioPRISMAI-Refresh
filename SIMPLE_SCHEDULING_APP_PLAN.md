# PhysioPRISM Schedule - Simple Implementation Plan

## 🎯 Goal: Familiar, Simple Scheduling App

Build a lightweight scheduling app that:
- ✅ Looks like Google Calendar / Calendly (familiar UI)
- ✅ Completely bundled (no extra charges)
- ✅ Works for physios AND secretaries
- ✅ Minimal learning curve
- ✅ PWA installable on phone
- ✅ Shares database with main app

**Future:** Add patient auto-scheduling chatbot, intake forms, etc.

---

## 📁 Folder Structure (New Separate App)

```
D:\New folder\New folder\PhysioSchedule\
│
├── app.py                           # Main Flask app (lightweight)
├── requirements.txt                 # Minimal dependencies
├── .env.example                     # Environment template
├── .env                            # Your credentials
│
├── config.py                        # App configuration
├── database.py                      # Cosmos DB connection (shared)
├── auth.py                         # Firebase auth (shared)
│
├── models/
│   ├── appointment.py              # Appointment model
│   └── user.py                     # User model (from main app)
│
├── routes/
│   ├── calendar.py                 # Calendar view routes
│   ├── appointments.py             # Appointment CRUD routes
│   └── api.py                      # API endpoints
│
├── templates/
│   ├── base.html                   # Base template (lightweight)
│   ├── calendar.html               # Calendar view (main screen)
│   ├── day_view.html               # Day view
│   ├── week_view.html              # Week view
│   ├── book_appointment.html       # Booking modal
│   └── login.html                  # Login page
│
├── static/
│   ├── css/
│   │   └── style.css               # Simple, minimal CSS
│   ├── js/
│   │   ├── calendar.js             # Calendar logic
│   │   └── appointments.js         # Appointment handling
│   ├── icons/
│   │   ├── icon-192.png            # PWA icons
│   │   └── icon-512.png
│   ├── manifest.json               # PWA manifest
│   └── service-worker.js           # Offline support
│
├── utils/
│   ├── helpers.py                  # Helper functions
│   └── notifications.py            # SMS/WhatsApp (reuse from main)
│
└── README.md                       # Setup instructions
```

---

## 🎨 UI Design - Familiar Calendar Interface

### **Inspiration: Google Calendar Style**

Simple, clean, intuitive - users already know how to use it.

### **Main Screen - Week View** (Default)

```
┌──────────────────────────────────────────────────────────────┐
│ PhysioPRISM Schedule          Feb 10-16, 2026      👤 Dr. Sarah│
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ [Today] [Day] [Week] [Month]         [+ New Appointment]     │
│                                                               │
├─────┬──────┬──────┬──────┬──────┬──────┬──────┬─────────────┤
│     │ Mon  │ Tue  │ Wed  │ Thu  │ Fri  │ Sat  │ Sun         │
│     │  10  │  11  │  12  │  13  │  14  │  15  │  16         │
├─────┼──────┼──────┼──────┼──────┼──────┼──────┼─────────────┤
│     │      │      │      │      │      │      │             │
│ 8am │      │      │      │      │      │      │             │
│     │      │      │      │      │      │      │             │
├─────┼──────┼──────┼──────┼──────┼──────┼──────┼─────────────┤
│     │      │┌─────┐      │┌─────┐      │      │             │
│ 9am │      ││John ││      ││Jane ││      │      │             │
│     │      ││Doe  ││      ││Smith││      │      │             │
│     │      │└─────┘      │└─────┘      │      │             │
├─────┼──────┼──────┼──────┼──────┼──────┼──────┼─────────────┤
│     │┌─────┐      │┌─────┐      │      │      │             │
│10am ││Sarah││      ││Mike ││      │      │      │             │
│     ││Will ││      ││John ││      │      │      │             │
│     │└─────┘      │└─────┘      │      │      │             │
├─────┼──────┼──────┼──────┼──────┼──────┼──────┼─────────────┤
│     │      │      │      │      │      │      │             │
│11am │      │      │      │      │      │      │             │
│     │      │      │      │      │      │      │             │
├─────┼──────┼──────┼──────┼──────┼──────┼──────┼─────────────┤
│     │      │      │      │      │      │      │             │
│12pm │      │      │      │      │      │      │             │
│     │      │      │      │      │      │      │             │
└─────┴──────┴──────┴──────┴──────┴──────┴──────┴─────────────┘

Click empty slot → Book appointment
Click appointment → View/Edit/Cancel
```

**Features:**
- Clean grid layout
- Color-coded appointments (by status)
- Easy drag-and-drop (future)
- Click anywhere to book

### **Day View** (For Busy Days)

```
┌────────────────────────────────────────────┐
│ Wednesday, Feb 12, 2026          [< Today >]│
├────────────────────────────────────────────┤
│                                            │
│ 9:00 AM  ┌──────────────────────────────┐ │
│          │ John Doe                     │ │
│          │ Initial Consultation         │ │
│          │ +919876543210                │ │
│          │ Lower back pain              │ │
│ 9:30 AM  │ [View] [Check In] [Edit]     │ │
│          └──────────────────────────────┘ │
│                                            │
│ 10:00 AM ┌──────────────────────────────┐ │
│          │ Jane Smith                   │ │
│          │ Follow-up                    │ │
│          │ +919876543211                │ │
│ 10:30 AM │ Knee rehabilitation          │ │
│          │ [View] [Check In] [Edit]     │ │
│          └──────────────────────────────┘ │
│                                            │
│ 11:00 AM                                   │
│          [+ Add Appointment]               │
│                                            │
│ 11:30 AM                                   │
│                                            │
│ 12:00 PM                                   │
│                                            │
└────────────────────────────────────────────┘
```

### **Booking Modal** (Simple Form)

```
┌──────────────────────────────────────┐
│ New Appointment                  [×] │
├──────────────────────────────────────┤
│                                      │
│ Patient                              │
│ ┌────────────────────────────────┐  │
│ │ Search patient...          [🔍]│  │
│ └────────────────────────────────┘  │
│ [+ Add New Patient]                  │
│                                      │
│ Date & Time                          │
│ ┌──────────────┐  ┌──────────────┐  │
│ │ Feb 15, 2026 │  │ 2:00 PM  [▼]│  │
│ └──────────────┘  └──────────────┘  │
│                                      │
│ Duration                             │
│ [30 min] [45 min] [60 min]           │
│                                      │
│ Appointment Type                     │
│ [Initial] [Follow-up] [Treatment]    │
│                                      │
│ Chief Complaint                      │
│ ┌────────────────────────────────┐  │
│ │                                │  │
│ └────────────────────────────────┘  │
│                                      │
│ ☑ Send SMS reminder                 │
│                                      │
│ [Cancel]              [Book]         │
└──────────────────────────────────────┘
```

### **Mobile View** (Responsive)

```
┌─────────────────────────┐
│ ☰  Schedule      [+ New]│
├─────────────────────────┤
│ Today - Wed, Feb 12     │
│ ━━━━━━━━━━━━━━━━━━━━━  │
│                         │
│ ┌─────────────────────┐ │
│ │ 9:00 AM             │ │
│ │ John Doe            │ │
│ │ Initial Consultation│ │
│ │ [Check In]          │ │
│ └─────────────────────┘ │
│                         │
│ ┌─────────────────────┐ │
│ │ 10:00 AM            │ │
│ │ Jane Smith          │ │
│ │ Follow-up           │ │
│ │ [Check In]          │ │
│ └─────────────────────┘ │
│                         │
│ [+ New Appointment]     │
│                         │
├─────────────────────────┤
│ [Today] [Week] [Month]  │
└─────────────────────────┘
```

---

## 🗄️ Database Schema (Simplified)

### **Only 2 Collections Needed**

#### 1. `appointments` Collection

```python
{
    'id': 'appt_abc123',

    # Patient info (from main app)
    'patient_id': 'patient_xyz',
    'patient_name': 'John Doe',      # Cached for display
    'patient_phone': '+919876543210', # For reminders

    # Physio (who's treating)
    'physio_id': 'physio@example.com',
    'physio_name': 'Dr. Sarah',

    # Appointment details
    'date': '2026-02-15',            # ISO format YYYY-MM-DD
    'time': '14:00',                 # 24-hour format HH:MM
    'duration': 30,                  # minutes
    'end_time': '14:30',             # calculated

    # Type & notes
    'type': 'initial',               # initial, followup, treatment
    'chief_complaint': 'Lower back pain',
    'notes': '',

    # Status
    'status': 'scheduled',           # scheduled, confirmed, checked_in, completed, cancelled, no_show
    'checked_in_at': null,

    # Reminders
    'reminder_sent_24h': false,
    'reminder_sent_2h': false,

    # Metadata
    'created_by': 'secretary@example.com',
    'created_at': '2026-02-12T10:30:00Z',
    'updated_at': '2026-02-12T10:30:00Z',

    # For multi-user
    'institute_id': 'inst_123' or null  # For institute accounts
}
```

**Indexes:**
- `date` - for calendar queries
- `physio_id` + `date` - for physio's schedule
- `patient_id` - for patient's appointments

#### 2. `working_hours` Collection (Optional - Phase 2)

```python
{
    'id': 'hours_abc123',
    'physio_id': 'physio@example.com',

    # Simple weekly schedule
    'monday': {'start': '09:00', 'end': '17:00', 'enabled': true},
    'tuesday': {'start': '09:00', 'end': '17:00', 'enabled': true},
    'wednesday': {'start': '09:00', 'end': '17:00', 'enabled': true},
    'thursday': {'start': '09:00', 'end': '17:00', 'enabled': true},
    'friday': {'start': '09:00', 'end': '17:00', 'enabled': true},
    'saturday': {'start': '09:00', 'end': '13:00', 'enabled': true},
    'sunday': {'enabled': false},

    # Defaults
    'default_duration': 30,  # minutes
    'slot_interval': 30      # minutes
}
```

**That's it!** Keep it simple.

---

## 🔧 Implementation Steps

### **Phase 1: Basic Setup** (Day 1)

**1. Create New Folder & Files**

```bash
mkdir PhysioSchedule
cd PhysioSchedule

# Create files
touch app.py
touch config.py
touch database.py
touch auth.py
touch requirements.txt
touch .env.example
```

**2. Install Dependencies**

```python
# requirements.txt
Flask==3.1.0
azure-cosmos==4.7.0
firebase-admin==6.6.0
python-dotenv==1.0.0
gunicorn==22.0.0
```

```bash
pip install -r requirements.txt
```

**3. Setup Environment**

```env
# .env.example
# Copy to .env and fill in values

# Cosmos DB (same as main app)
COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOS_KEY=your-key-here
COSMOS_DATABASE=PhysiologicPRISM

# Firebase (same as main app)
FIREBASE_PROJECT_ID=your-project-id

# App settings
SECRET_KEY=your-secret-key
APP_NAME=PhysioPRISM Schedule
```

**4. Basic App Structure**

```python
# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Import routes (will create these)
# from routes import calendar, appointments, api

@app.route('/')
def index():
    """Main calendar view"""
    return render_template('calendar.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
```

### **Phase 2: Database Connection** (Day 1)

```python
# database.py
import os
from azure.cosmos import CosmosClient, PartitionKey

def get_cosmos_client():
    """Get Cosmos DB client (shared with main app)"""
    endpoint = os.getenv('COSMOS_ENDPOINT')
    key = os.getenv('COSMOS_KEY')

    client = CosmosClient(endpoint, key)
    database = client.get_database_client(os.getenv('COSMOS_DATABASE'))

    return database

def get_appointments_container():
    """Get appointments container"""
    db = get_cosmos_client()
    return db.get_container_client('appointments')

def get_patients_container():
    """Get patients container (from main app)"""
    db = get_cosmos_client()
    return db.get_container_client('patients')

def get_users_container():
    """Get users container (from main app)"""
    db = get_cosmos_client()
    return db.get_container_client('users')
```

### **Phase 3: Authentication** (Day 1)

```python
# auth.py
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from flask import session, redirect, url_for, request
from functools import wraps
import os

# Initialize Firebase (reuse from main app)
if not firebase_admin._apps:
    cred = credentials.Certificate('path-to-firebase-key.json')
    firebase_admin.initialize_app(cred)

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def verify_token(id_token):
    """Verify Firebase ID token"""
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None
```

### **Phase 4: Calendar View** (Day 2)

**templates/base.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}PhysioPRISM Schedule{% endblock %}</title>

    <!-- PWA -->
    <link rel="manifest" href="{{ url_for('static', filename='manifest.json') }}">
    <meta name="theme-color" content="#1a5f5a">

    <!-- CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">

    {% block head %}{% endblock %}
</head>
<body>
    <nav class="navbar">
        <div class="nav-left">
            <h1>📅 PhysioPRISM Schedule</h1>
        </div>
        <div class="nav-right">
            <span>{{ current_user.name }}</span>
            <a href="{{ url_for('logout') }}">Logout</a>
        </div>
    </nav>

    <main class="container">
        {% block content %}{% endblock %}
    </main>

    <script src="{{ url_for('static', filename='js/calendar.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

**templates/calendar.html**

```html
{% extends "base.html" %}

{% block content %}
<div class="calendar-container">
    <!-- Header with view switcher -->
    <div class="calendar-header">
        <div class="view-switcher">
            <button class="btn-view" data-view="day">Day</button>
            <button class="btn-view active" data-view="week">Week</button>
            <button class="btn-view" data-view="month">Month</button>
        </div>

        <div class="date-navigation">
            <button id="prev-period">←</button>
            <h2 id="current-period">Feb 10-16, 2026</h2>
            <button id="next-period">→</button>
            <button id="today-btn">Today</button>
        </div>

        <button class="btn-primary" id="new-appointment">
            + New Appointment
        </button>
    </div>

    <!-- Calendar grid -->
    <div id="calendar-grid" class="week-view">
        <!-- JavaScript will populate this -->
    </div>
</div>

<!-- Booking modal -->
<div id="booking-modal" class="modal" style="display: none;">
    <div class="modal-content">
        <span class="close">&times;</span>
        <h2>New Appointment</h2>

        <form id="booking-form">
            <label>Patient</label>
            <input type="text" id="patient-search" placeholder="Search patient...">

            <label>Date</label>
            <input type="date" id="appointment-date" required>

            <label>Time</label>
            <input type="time" id="appointment-time" required>

            <label>Duration</label>
            <select id="duration">
                <option value="30">30 minutes</option>
                <option value="45">45 minutes</option>
                <option value="60">60 minutes</option>
            </select>

            <label>Type</label>
            <select id="appointment-type">
                <option value="initial">Initial Consultation</option>
                <option value="followup">Follow-up</option>
                <option value="treatment">Treatment</option>
            </select>

            <label>Chief Complaint</label>
            <textarea id="chief-complaint" rows="3"></textarea>

            <label>
                <input type="checkbox" id="send-reminder" checked>
                Send SMS reminder
            </label>

            <div class="form-actions">
                <button type="button" class="btn-secondary" id="cancel-booking">Cancel</button>
                <button type="submit" class="btn-primary">Book Appointment</button>
            </div>
        </form>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/appointments.js') }}"></script>
{% endblock %}
```

### **Phase 5: JavaScript Calendar Logic** (Day 2-3)

**static/js/calendar.js**

```javascript
// Calendar state
let currentDate = new Date();
let currentView = 'week';

// Initialize calendar
document.addEventListener('DOMContentLoaded', function() {
    renderCalendar();
    setupEventListeners();
    loadAppointments();
});

function renderCalendar() {
    const grid = document.getElementById('calendar-grid');

    if (currentView === 'week') {
        renderWeekView(grid);
    } else if (currentView === 'day') {
        renderDayView(grid);
    } else {
        renderMonthView(grid);
    }
}

function renderWeekView(grid) {
    // Calculate week start (Monday)
    const weekStart = getMonday(currentDate);

    // Create time slots
    const timeSlots = generateTimeSlots('08:00', '18:00', 30);

    // Build HTML
    let html = '<div class="week-grid">';

    // Header row (days)
    html += '<div class="time-column">Time</div>';
    for (let i = 0; i < 7; i++) {
        const day = new Date(weekStart);
        day.setDate(day.getDate() + i);

        const dayName = day.toLocaleDateString('en-US', { weekday: 'short' });
        const dayNum = day.getDate();

        html += `<div class="day-column">
            <div class="day-header">${dayName} ${dayNum}</div>
        </div>`;
    }

    // Time rows
    timeSlots.forEach(time => {
        html += `<div class="time-label">${time}</div>`;

        for (let i = 0; i < 7; i++) {
            const day = new Date(weekStart);
            day.setDate(day.getDate() + i);
            const dateStr = day.toISOString().split('T')[0];

            html += `<div class="time-slot"
                data-date="${dateStr}"
                data-time="${time}"
                onclick="openBookingModal('${dateStr}', '${time}')">
            </div>`;
        }
    });

    html += '</div>';
    grid.innerHTML = html;
}

function loadAppointments() {
    // Fetch appointments from API
    fetch('/api/appointments?' + new URLSearchParams({
        start_date: getWeekStart(),
        end_date: getWeekEnd()
    }))
    .then(response => response.json())
    .then(appointments => {
        renderAppointments(appointments);
    })
    .catch(error => console.error('Error loading appointments:', error));
}

function renderAppointments(appointments) {
    appointments.forEach(appt => {
        const slot = document.querySelector(
            `[data-date="${appt.date}"][data-time="${appt.time}"]`
        );

        if (slot) {
            const apptDiv = document.createElement('div');
            apptDiv.className = `appointment status-${appt.status}`;
            apptDiv.innerHTML = `
                <div class="appt-time">${appt.time}</div>
                <div class="appt-patient">${appt.patient_name}</div>
                <div class="appt-type">${appt.type}</div>
            `;
            apptDiv.onclick = (e) => {
                e.stopPropagation();
                viewAppointment(appt.id);
            };

            slot.appendChild(apptDiv);
        }
    });
}

function openBookingModal(date, time) {
    const modal = document.getElementById('booking-modal');
    document.getElementById('appointment-date').value = date;
    document.getElementById('appointment-time').value = time;
    modal.style.display = 'block';
}

// Helper functions
function getMonday(date) {
    const day = date.getDay();
    const diff = date.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(date.setDate(diff));
}

function generateTimeSlots(start, end, interval) {
    const slots = [];
    let current = start;

    while (current <= end) {
        slots.push(current);

        // Add interval
        const [hours, minutes] = current.split(':').map(Number);
        const totalMinutes = hours * 60 + minutes + interval;
        const newHours = Math.floor(totalMinutes / 60);
        const newMinutes = totalMinutes % 60;
        current = `${String(newHours).padStart(2, '0')}:${String(newMinutes).padStart(2, '0')}`;
    }

    return slots;
}

function setupEventListeners() {
    // View switcher
    document.querySelectorAll('.btn-view').forEach(btn => {
        btn.addEventListener('click', function() {
            currentView = this.dataset.view;
            document.querySelectorAll('.btn-view').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            renderCalendar();
            loadAppointments();
        });
    });

    // Date navigation
    document.getElementById('prev-period').addEventListener('click', () => {
        navigatePeriod(-1);
    });

    document.getElementById('next-period').addEventListener('click', () => {
        navigatePeriod(1);
    });

    document.getElementById('today-btn').addEventListener('click', () => {
        currentDate = new Date();
        renderCalendar();
        loadAppointments();
    });

    // Modal close
    document.querySelector('.close').addEventListener('click', () => {
        document.getElementById('booking-modal').style.display = 'none';
    });
}

function navigatePeriod(direction) {
    if (currentView === 'week') {
        currentDate.setDate(currentDate.getDate() + (direction * 7));
    } else if (currentView === 'month') {
        currentDate.setMonth(currentDate.getMonth() + direction);
    } else {
        currentDate.setDate(currentDate.getDate() + direction);
    }

    renderCalendar();
    loadAppointments();
}
```

**static/js/appointments.js**

```javascript
// Handle appointment booking
document.getElementById('booking-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const appointment = {
        patient_id: document.getElementById('patient-search').dataset.patientId,
        date: document.getElementById('appointment-date').value,
        time: document.getElementById('appointment-time').value,
        duration: parseInt(document.getElementById('duration').value),
        type: document.getElementById('appointment-type').value,
        chief_complaint: document.getElementById('chief-complaint').value,
        send_reminder: document.getElementById('send-reminder').checked
    };

    try {
        const response = await fetch('/api/appointments', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(appointment)
        });

        if (response.ok) {
            // Close modal
            document.getElementById('booking-modal').style.display = 'none';

            // Refresh calendar
            loadAppointments();

            // Show success message
            alert('Appointment booked successfully!');
        } else {
            alert('Failed to book appointment');
        }
    } catch (error) {
        console.error('Error booking appointment:', error);
        alert('Error booking appointment');
    }
});

function viewAppointment(appointmentId) {
    // Fetch appointment details
    fetch(`/api/appointments/${appointmentId}`)
        .then(response => response.json())
        .then(appointment => {
            showAppointmentDetails(appointment);
        });
}

function showAppointmentDetails(appointment) {
    // Show appointment details modal
    // (Similar to booking modal but with view/edit options)
    console.log('View appointment:', appointment);
}
```

### **Phase 6: API Routes** (Day 3)

**routes/api.py**

```python
from flask import Blueprint, request, jsonify, session
from database import get_appointments_container, get_patients_container
from datetime import datetime, timedelta
import uuid

api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/appointments', methods=['GET'])
def get_appointments():
    """Get appointments for date range"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    physio_id = session.get('user_id')

    container = get_appointments_container()

    # Query appointments
    query = f"""
        SELECT * FROM c
        WHERE c.physio_id = @physio_id
        AND c.date >= @start_date
        AND c.date <= @end_date
        AND c.status != 'cancelled'
        ORDER BY c.date, c.time
    """

    parameters = [
        {'name': '@physio_id', 'value': physio_id},
        {'name': '@start_date', 'value': start_date},
        {'name': '@end_date', 'value': end_date}
    ]

    appointments = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))

    return jsonify(appointments)

@api.route('/appointments', methods=['POST'])
def create_appointment():
    """Create new appointment"""
    data = request.json
    physio_id = session.get('user_id')

    # Get patient details
    patients = get_patients_container()
    patient = patients.read_item(data['patient_id'], partition_key=data['patient_id'])

    # Calculate end time
    start_time = datetime.strptime(data['time'], '%H:%M')
    end_time = start_time + timedelta(minutes=data['duration'])

    appointment = {
        'id': f"appt_{uuid.uuid4().hex[:12]}",
        'patient_id': data['patient_id'],
        'patient_name': patient['name'],
        'patient_phone': patient['phone'],
        'physio_id': physio_id,
        'date': data['date'],
        'time': data['time'],
        'end_time': end_time.strftime('%H:%M'),
        'duration': data['duration'],
        'type': data['type'],
        'chief_complaint': data.get('chief_complaint', ''),
        'status': 'scheduled',
        'reminder_sent_24h': False,
        'reminder_sent_2h': False,
        'created_by': physio_id,
        'created_at': datetime.utcnow().isoformat()
    }

    container = get_appointments_container()
    container.create_item(body=appointment)

    # Send SMS reminder if requested
    if data.get('send_reminder'):
        # TODO: Schedule reminder using existing messaging system
        pass

    return jsonify(appointment), 201

@api.route('/appointments/<appointment_id>', methods=['GET'])
def get_appointment(appointment_id):
    """Get single appointment"""
    container = get_appointments_container()
    appointment = container.read_item(appointment_id, partition_key=appointment_id)
    return jsonify(appointment)

@api.route('/appointments/<appointment_id>', methods=['PUT'])
def update_appointment(appointment_id):
    """Update appointment"""
    data = request.json
    container = get_appointments_container()

    # Get existing appointment
    appointment = container.read_item(appointment_id, partition_key=appointment_id)

    # Update fields
    appointment.update(data)
    appointment['updated_at'] = datetime.utcnow().isoformat()

    container.replace_item(appointment_id, appointment)

    return jsonify(appointment)

@api.route('/appointments/<appointment_id>/checkin', methods=['POST'])
def checkin_appointment(appointment_id):
    """Check in patient"""
    container = get_appointments_container()

    appointment = container.read_item(appointment_id, partition_key=appointment_id)
    appointment['status'] = 'checked_in'
    appointment['checked_in_at'] = datetime.utcnow().isoformat()

    container.replace_item(appointment_id, appointment)

    return jsonify(appointment)

@api.route('/appointments/<appointment_id>', methods=['DELETE'])
def cancel_appointment(appointment_id):
    """Cancel appointment"""
    container = get_appointments_container()

    appointment = container.read_item(appointment_id, partition_key=appointment_id)
    appointment['status'] = 'cancelled'
    appointment['cancelled_at'] = datetime.utcnow().isoformat()

    container.replace_item(appointment_id, appointment)

    return jsonify({'message': 'Appointment cancelled'})
```

### **Phase 7: Simple CSS** (Day 3)

**static/css/style.css**

```css
/* Simple, clean styling - Google Calendar inspired */

:root {
    --primary: #1a5f5a;
    --primary-light: #4a7c7a;
    --border: #e0e0e0;
    --bg-light: #f5f5f5;
    --text: #333;
    --white: #fff;

    /* Status colors */
    --status-scheduled: #3498db;
    --status-confirmed: #27ae60;
    --status-checked-in: #f39c12;
    --status-completed: #95a5a6;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: var(--text);
    background: var(--bg-light);
}

/* Navbar */
.navbar {
    background: var(--white);
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.navbar h1 {
    font-size: 1.5rem;
    color: var(--primary);
}

/* Calendar container */
.calendar-container {
    max-width: 1400px;
    margin: 2rem auto;
    background: var(--white);
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* Calendar header */
.calendar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
}

.view-switcher {
    display: flex;
    gap: 0.5rem;
}

.btn-view {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border);
    background: var(--white);
    cursor: pointer;
    border-radius: 4px;
}

.btn-view.active {
    background: var(--primary);
    color: var(--white);
    border-color: var(--primary);
}

.date-navigation {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.btn-primary {
    background: var(--primary);
    color: var(--white);
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
}

.btn-primary:hover {
    background: var(--primary-light);
}

/* Week grid */
.week-grid {
    display: grid;
    grid-template-columns: 80px repeat(7, 1fr);
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
}

.time-column,
.day-column {
    padding: 1rem;
    border-bottom: 1px solid var(--border);
    border-right: 1px solid var(--border);
    text-align: center;
    font-weight: 600;
}

.time-label {
    padding: 0.5rem;
    border-bottom: 1px solid var(--border);
    border-right: 1px solid var(--border);
    font-size: 0.875rem;
    color: #666;
}

.time-slot {
    min-height: 60px;
    border-bottom: 1px solid var(--border);
    border-right: 1px solid var(--border);
    cursor: pointer;
    position: relative;
}

.time-slot:hover {
    background: #f9f9f9;
}

/* Appointments */
.appointment {
    background: var(--status-scheduled);
    color: var(--white);
    padding: 0.5rem;
    margin: 2px;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
}

.appointment.status-confirmed {
    background: var(--status-confirmed);
}

.appointment.status-checked-in {
    background: var(--status-checked-in);
}

.appointment.status-completed {
    background: var(--status-completed);
}

/* Modal */
.modal {
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.5);
}

.modal-content {
    background: var(--white);
    margin: 5% auto;
    padding: 2rem;
    max-width: 500px;
    border-radius: 8px;
}

.modal-content h2 {
    margin-bottom: 1.5rem;
    color: var(--primary);
}

.modal-content label {
    display: block;
    margin-top: 1rem;
    font-weight: 500;
}

.modal-content input,
.modal-content select,
.modal-content textarea {
    width: 100%;
    padding: 0.75rem;
    margin-top: 0.5rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: 1rem;
}

.form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 2rem;
}

.btn-secondary {
    background: var(--white);
    border: 1px solid var(--border);
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    cursor: pointer;
}

.close {
    float: right;
    font-size: 2rem;
    cursor: pointer;
    color: #999;
}

.close:hover {
    color: var(--text);
}

/* Mobile responsive */
@media (max-width: 768px) {
    .week-grid {
        display: block;
    }

    .calendar-header {
        flex-direction: column;
        gap: 1rem;
    }
}
```

---

## 📱 PWA Setup (Day 4)

**static/manifest.json**

```json
{
  "name": "PhysioPRISM Schedule",
  "short_name": "Schedule",
  "description": "Appointment scheduling for PhysioPRISM",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#1a5f5a",
  "background_color": "#ffffff",
  "icons": [
    {
      "src": "/static/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

**static/service-worker.js**

```javascript
const CACHE_NAME = 'physioschedule-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/js/calendar.js',
  '/static/js/appointments.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
```

---

## 🚀 Deployment

### **Option 1: Same Azure Container as Main App**

```python
# In main PhysiologicPRISM app.py
# Add schedule routes

from PhysioSchedule import app as schedule_app

# Mount schedule app at /schedule
main_app.register_blueprint(schedule_app, url_prefix='/schedule')
```

### **Option 2: Separate Azure Container**

Deploy PhysioSchedule as its own container:
- URL: schedule.physiologicprism.com
- Same Cosmos DB connection
- Separate deployment

---

## ✅ Final Checklist

**Minimal Features for Launch:**

- ✅ Week view calendar
- ✅ Book appointment
- ✅ View appointments
- ✅ Check-in patient
- ✅ Cancel appointment
- ✅ Patient search
- ✅ Mobile responsive
- ✅ PWA installable

**Nice-to-Have (Add Later):**

- ⏸️ Day/Month views
- ⏸️ Drag-and-drop reschedule
- ⏸️ Working hours management
- ⏸️ Push notifications
- ⏸️ Patient intake
- ⏸️ Chatbot scheduling
- ⏸️ Analytics/reports

---

## 📖 Summary

**What You're Building:**

A simple, Google Calendar-like scheduling app that:
- Lives in its own folder (`PhysioSchedule/`)
- Shares database with main app (instant sync)
- Familiar UI (users know how to use it)
- Works on phone (PWA)
- Bundled free with all plans
- Works for physios AND secretaries

**Implementation Time:** 3-4 days

**Tech Stack:**
- Flask (lightweight)
- Cosmos DB (shared)
- Firebase Auth (shared)
- Vanilla JS (no framework)
- Simple CSS (500 lines)

**Result:** A fast, familiar scheduling app that just works! 🎯

---

Ready to implement? Start with Phase 1 and work through step-by-step! 🚀
