# PhysiologicPRISM - Appointment Scheduling Module
## Comprehensive Implementation Plan

---

## 📋 Executive Summary

**Goal:** Build an integrated appointment scheduling module for PhysiologicPRISM that:
- Works for solo physiotherapists AND secretaries/receptionists
- Eliminates need for external calendar services (Google Calendar, etc.)
- Keeps all data centralized in Azure Cosmos DB
- Matches existing UI/UX design language
- Bundles with main app with minimal additional pricing

**Target Users:**
1. Solo physiotherapists (self-scheduling)
2. Institute secretaries/receptionists (scheduling for multiple physios)
3. Institute admins (oversight)

**Timeline:** 2-3 weeks
**Pricing:** Bundled with existing plans + small add-on for premium features

---

## 🏗️ System Architecture

### Current vs. New

**Current System:**
```
PhysiologicPRISM (Main App)
├── Patient Management ✅
├── Clinical Assessments ✅
├── AI Suggestions ✅
├── Follow-ups ✅ (basic reminders only)
├── Subscriptions ✅
└── Messaging ✅
```

**New Addition:**
```
PhysiologicPRISM (Enhanced)
├── ... (all existing features)
└── Appointment Scheduling 🆕
    ├── Calendar View
    ├── Appointment Booking
    ├── Patient Pre-Registration
    ├── Automated Reminders
    ├── Check-in System
    └── Secretary/Staff Access
```

### Technical Stack (No Changes Needed)

- **Backend:** Flask (existing)
- **Database:** Azure Cosmos DB (existing)
- **Authentication:** Firebase Auth (existing)
- **Frontend:** Jinja2 templates + vanilla JavaScript (existing)
- **Messaging:** Twilio SMS/WhatsApp (existing)
- **Hosting:** Azure Container Apps (existing)

✅ **Advantage:** No new infrastructure costs!

---

## 🗄️ Database Schema Design

### New Collections in Azure Cosmos DB

#### 1. `appointments` Collection

```python
{
    'id': 'appt_abc123',  # Auto-generated
    'appointment_id': 'appt_abc123',  # For queries

    # Core appointment data
    'patient_id': 'patient_xyz',  # Link to patients collection
    'patient_name': 'John Doe',  # Cached for quick display
    'patient_phone': '+919876543210',  # For reminders

    'physio_id': 'physio@example.com',  # Assigned physiotherapist
    'physio_name': 'Dr. Sarah',  # Cached for display

    # Scheduling
    'appointment_date': '2026-02-15',  # ISO date
    'appointment_time': '14:00',  # 24-hour format
    'duration_minutes': 30,  # Default 30 min, configurable
    'end_time': '14:30',  # Calculated

    # Status
    'status': 'scheduled',  # scheduled, confirmed, checked_in, in_progress, completed, cancelled, no_show
    'checked_in_at': null,  # When patient arrived
    'started_at': null,  # When physio started treatment
    'completed_at': null,  # When completed

    # Details
    'chief_complaint': 'Lower back pain',  # Brief description
    'appointment_type': 'initial_consultation',  # initial_consultation, follow_up, treatment
    'notes': 'First visit, referred by Dr. X',  # Internal notes
    'patient_notes': '',  # Patient's own notes (from intake form)

    # Reminders
    'reminder_24h_sent': false,
    'reminder_2h_sent': false,
    'reminder_24h_sent_at': null,
    'reminder_2h_sent_at': null,

    # Metadata
    'created_by': 'secretary@example.com',  # Who scheduled it
    'created_by_role': 'secretary',  # Role of creator
    'created_at': '2026-02-12T10:30:00Z',
    'updated_at': '2026-02-12T10:30:00Z',
    'updated_by': 'secretary@example.com',

    # Institute/Organization
    'institute_id': 'inst_123',  # For institute patients
    'location': 'Main Clinic',  # For multi-location institutes

    # Integration
    'follow_up_id': null,  # Link to follow_ups collection if created from follow-up
    'patient_record_id': null,  # Link to patient_records if treatment completed

    # Soft delete
    'deleted': false,
    'deleted_at': null
}
```

**Indexes:**
```python
# Required indexes for performance
- appointment_date (for calendar queries)
- physio_id + appointment_date (for physio schedule)
- patient_id + appointment_date (for patient appointments)
- status (for filtering)
- created_at (for sorting)
```

#### 2. `secretary_access` Collection

```python
{
    'id': 'access_abc123',
    'secretary_id': 'secretary@example.com',
    'institute_id': 'inst_123',  # Which institute they work for

    # Permissions
    'can_schedule': true,
    'can_cancel': true,
    'can_modify': true,
    'can_view_all': true,  # View all institute appointments

    # Access scope
    'physio_access': ['physio1@example.com', 'physio2@example.com'],  # Empty = all physios
    'location_access': ['Main Clinic', 'Branch Office'],  # Empty = all locations

    # Metadata
    'granted_by': 'admin@example.com',
    'granted_at': '2026-02-01T10:00:00Z',
    'active': true
}
```

#### 3. `working_hours` Collection

```python
{
    'id': 'hours_abc123',
    'physio_id': 'physio@example.com',

    # Weekly schedule
    'schedule': {
        'monday': {
            'enabled': true,
            'slots': [
                {'start': '09:00', 'end': '12:00'},  # Morning
                {'start': '14:00', 'end': '18:00'}   # Afternoon
            ]
        },
        'tuesday': {
            'enabled': true,
            'slots': [
                {'start': '09:00', 'end': '17:00'}
            ]
        },
        // ... rest of week
        'sunday': {
            'enabled': false,
            'slots': []
        }
    },

    # Appointment settings
    'default_duration': 30,  # minutes
    'buffer_between_appointments': 5,  # minutes
    'max_appointments_per_day': 16,

    # Special dates
    'blocked_dates': [
        {
            'date': '2026-12-25',
            'reason': 'Christmas Holiday',
            'all_day': true
        }
    ],

    'created_at': '2026-01-01T00:00:00Z',
    'updated_at': '2026-02-12T10:00:00Z'
}
```

#### 4. `patient_intake_sessions` Collection

```python
{
    'id': 'intake_abc123',
    'token': 'INK-ABC-123',  # 6-character token for patient access

    'appointment_id': 'appt_xyz',  # Linked appointment
    'patient_id': 'patient_123',  # If existing patient

    # Session info
    'status': 'pending',  # pending, in_progress, completed, expired
    'started_at': null,
    'completed_at': null,
    'expires_at': '2026-02-15T15:00:00Z',  # 30 min before appointment

    # Collected data
    'intake_data': {
        'chief_complaint': 'Lower back pain for 2 weeks',
        'pain_level': 7,
        'pain_location': ['lower_back', 'left_leg'],
        'pain_duration': '2 weeks',
        'medical_history': ['diabetes', 'hypertension'],
        'current_medications': ['Metformin', 'Lisinopril'],
        'previous_treatments': ['Physical therapy 2 years ago'],
        'allergies': 'None',
        'emergency_contact': {
            'name': 'Jane Doe',
            'relation': 'Spouse',
            'phone': '+919876543211'
        }
    },

    'created_by': 'secretary@example.com',
    'created_at': '2026-02-15T13:30:00Z'
}
```

---

## 🎨 UI/UX Design

### Color Scheme (Match Existing)

```css
/* Use existing PhysiologicPRISM colors */
--primary: #1a5f5a           /* Teal green - main brand */
--primary-light: #4a7c7a     /* Lighter teal */
--primary-hover: #005f56     /* Darker on hover */

--accent-blue: #3498db       /* For calendar events */
--accent-green: #2ecc71      /* For confirmed */
--accent-orange: #e67e22     /* For pending */
--success: #27ae60           /* For completed */
--error: #e74c3c             /* For cancelled */
--warning: #f39c12           /* For reminders */
```

### Navigation Addition

**Add to existing navbar:**
```html
<li><a href="{{ url_for('appointments') }}" title="Appointments (Press A)">
    📅 Appointments
</a></li>
```

**Position:** Between "Add Patient" and "Subscription"

### Main Views

#### 1. **Calendar View** (Primary Interface)

```
┌─────────────────────────────────────────────────────────────┐
│  📅 Appointments - February 2026                             │
├─────────────────────────────────────────────────────────────┤
│  [Today] [Week] [Month]   [+ New Appointment]    [Search]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Week View:                                                  │
│                                                              │
│  Time  │ Mon 10 │ Tue 11 │ Wed 12 │ Thu 13 │ Fri 14        │
│  ──────┼────────┼────────┼────────┼────────┼────────       │
│  09:00 │        │   🟢   │        │   🟢   │               │
│  09:30 │        │   🟢   │        │   🟢   │               │
│  10:00 │   🟢   │        │   🔵   │        │   🟡          │
│  10:30 │   🟢   │        │   🔵   │        │   🟡          │
│  11:00 │        │   🟢   │        │        │               │
│  ...   │        │        │        │        │               │
│                                                              │
│  Legend: 🟢 Confirmed  🟡 Pending  🔵 Checked-In  ✅ Done   │
└─────────────────────────────────────────────────────────────┘

Click on slot → Quick booking form
Click on event → View/edit appointment details
```

**Features:**
- ✅ Week/Month/Day views
- ✅ Color-coded by status
- ✅ Drag-and-drop to reschedule
- ✅ Click empty slot to book
- ✅ Today highlight
- ✅ Filter by physio (for institutes)
- ✅ Search appointments

#### 2. **New Appointment Form**

```
┌──────────────────────────────────────────────┐
│  New Appointment                             │
├──────────────────────────────────────────────┤
│                                              │
│  Patient:                                    │
│  ┌──────────────────────────────────────┐   │
│  │ [Search or Create New]          [⌄] │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  Physiotherapist: (if secretary)             │
│  ┌──────────────────────────────────────┐   │
│  │ Dr. Sarah Khan              [⌄]     │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  Date & Time:                                │
│  ┌──────────────┐  ┌──────────────┐         │
│  │ 2026-02-15   │  │ 14:00  [⌄]  │         │
│  └──────────────┘  └──────────────┘         │
│                                              │
│  Duration:                                   │
│  ⚪ 30 min  ⚫ 45 min  ⚪ 60 min             │
│                                              │
│  Appointment Type:                           │
│  ⚫ Initial Consultation                     │
│  ⚪ Follow-up                                │
│  ⚪ Treatment Session                        │
│                                              │
│  Chief Complaint:                            │
│  ┌──────────────────────────────────────┐   │
│  │ [Brief description]                  │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  Notes (Internal):                           │
│  ┌──────────────────────────────────────┐   │
│  │ [Optional notes]                     │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ☑ Send confirmation SMS/WhatsApp           │
│  ☑ Send reminder 24 hours before            │
│  ☑ Send reminder 2 hours before             │
│                                              │
│  [Cancel]              [Schedule]            │
└──────────────────────────────────────────────┘
```

#### 3. **Today's Appointments Dashboard**

```
┌─────────────────────────────────────────────────────┐
│  Today - Friday, February 14, 2026                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌───────────────────────────────────────────┐     │
│  │  Upcoming (3)                             │     │
│  ├───────────────────────────────────────────┤     │
│  │  09:00 AM - John Doe                      │     │
│  │  Initial Consultation | Lower back pain   │     │
│  │  [Check In] [View] [Reschedule] [Cancel]  │     │
│  ├───────────────────────────────────────────┤     │
│  │  10:30 AM - Jane Smith                    │     │
│  │  Follow-up | Knee rehabilitation          │     │
│  │  ✅ Checked In (10:25 AM)                 │     │
│  │  [Start Treatment] [View] [Cancel]        │     │
│  ├───────────────────────────────────────────┤     │
│  │  02:00 PM - Mike Johnson                  │     │
│  │  Treatment | Shoulder pain                │     │
│  │  [Check In] [View] [Reschedule] [Cancel]  │     │
│  └───────────────────────────────────────────┘     │
│                                                     │
│  ┌───────────────────────────────────────────┐     │
│  │  Completed (2)                            │     │
│  ├───────────────────────────────────────────┤     │
│  │  08:00 AM - Sarah Williams ✓              │     │
│  │  09:00 AM - Tom Brown ✓                   │     │
│  └───────────────────────────────────────────┘     │
│                                                     │
│  Statistics:                                        │
│  Total: 5 | Completed: 2 | Remaining: 3            │
└─────────────────────────────────────────────────────┘
```

#### 4. **Patient Quick Registration** (For Walk-ins)

```
┌──────────────────────────────────────┐
│  Quick Patient Registration          │
├──────────────────────────────────────┤
│                                      │
│  Full Name: *                        │
│  ┌────────────────────────────┐     │
│  │ [Patient name]             │     │
│  └────────────────────────────┘     │
│                                      │
│  Phone: *                            │
│  ┌────────────────────────────┐     │
│  │ +91 [Number]               │     │
│  └────────────────────────────┘     │
│                                      │
│  Age:          Gender:               │
│  ┌────────┐   ⚫ Male  ⚪ Female     │
│  │ [Age]  │   ⚪ Other              │
│  └────────┘                          │
│                                      │
│  Chief Complaint: *                  │
│  ┌────────────────────────────┐     │
│  │ [Brief description]        │     │
│  └────────────────────────────┘     │
│                                      │
│  [Cancel]      [Save & Schedule]     │
└──────────────────────────────────────┘
```

**Flow:** Register → Auto-redirect to appointment booking with patient pre-selected

#### 5. **Patient Intake Kiosk** (Optional - Phase 2)

**Access:** Tablet in waiting room with token-based access

```
┌────────────────────────────────────────┐
│  Welcome to PhysiologicPRISM           │
├────────────────────────────────────────┤
│                                        │
│  Please enter your intake code:        │
│                                        │
│  ┌──────────────────────────────┐     │
│  │  I N K - [___] [___] [___]   │     │
│  └──────────────────────────────┘     │
│                                        │
│  Or scan the QR code:                  │
│  ┌────────┐                            │
│  │  📱 QR │                            │
│  └────────┘                            │
│                                        │
│  [Continue]                            │
└────────────────────────────────────────┘
```

**After entering code:**
```
┌────────────────────────────────────────┐
│  Patient Intake Form                   │
│  Step 1 of 4                           │
├────────────────────────────────────────┤
│  ━━━━━━━━━━░░░░░░░░░░░░ 25%           │
│                                        │
│  How are you feeling today?            │
│                                        │
│  Pain Level:                           │
│  ┌────────────────────────────────┐   │
│  │  0 ──────●───────────── 10     │   │
│  │  No pain            Worst pain │   │
│  └────────────────────────────────┘   │
│                                        │
│  Where is the pain? (Tap on body)      │
│  ┌────────────────────────────────┐   │
│  │     👤 Body Diagram            │   │
│  │                                │   │
│  └────────────────────────────────┘   │
│                                        │
│  [Back]              [Next Step →]     │
└────────────────────────────────────────┘
```

---

## 🔐 Role-Based Permissions

### User Roles & Access

```python
APPOINTMENT_PERMISSIONS = {
    'super_admin': {
        'can_view_all': True,
        'can_schedule': True,
        'can_modify': True,
        'can_cancel': True,
        'can_delete': True,
        'can_manage_settings': True,
        'can_grant_access': True,
        'view_scope': 'all_institutes'
    },

    'physio': {  # Solo physiotherapist
        'can_view_all': True,  # Own appointments only
        'can_schedule': True,
        'can_modify': True,
        'can_cancel': True,
        'can_delete': False,
        'can_manage_settings': True,  # Own working hours
        'can_grant_access': False,
        'view_scope': 'own_appointments'
    },

    'institute_admin': {
        'can_view_all': True,  # All institute appointments
        'can_schedule': True,
        'can_modify': True,
        'can_cancel': True,
        'can_delete': False,
        'can_manage_settings': True,
        'can_grant_access': True,  # Can add secretaries
        'view_scope': 'institute_appointments'
    },

    'secretary': {  # NEW ROLE
        'can_view_all': True,  # Institute appointments only
        'can_schedule': True,
        'can_modify': True,
        'can_cancel': True,
        'can_delete': False,
        'can_manage_settings': False,
        'can_grant_access': False,
        'view_scope': 'assigned_physios'
    },

    'patient_intake': {  # Token-based, no login
        'can_view_all': False,
        'can_schedule': False,
        'can_modify': False,
        'can_cancel': False,
        'can_delete': False,
        'can_manage_settings': False,
        'can_grant_access': False,
        'view_scope': 'own_intake_only'
    }
}
```

### Access Control Examples

```python
# Solo Physio
- Can see only their own appointments
- Can schedule for their own patients
- Can set their own working hours
- Cannot access other physios' schedules

# Institute Secretary
- Can see all appointments for assigned physios
- Can schedule for any physio in their institute
- Can check-in patients
- Can register new patients
- Cannot modify working hours
- Cannot access billing/treatment details

# Institute Admin
- Full access to all institute appointments
- Can manage secretary access
- Can view all physios' schedules
- Can configure institute settings
```

---

## 🔄 Integration with Existing Features

### 1. **Integration with Patient Management**

**Existing:** `patients` collection
**New:** Link appointments to patients

```python
# When scheduling appointment
patient = get_patient(patient_id)
appointment['patient_name'] = patient['name']  # Cache for display
appointment['patient_phone'] = patient['phone']  # For reminders

# When viewing patient
patient_appointments = get_appointments_by_patient(patient_id)
# Show appointment history on patient detail page
```

**UI Addition:**
```html
<!-- On patient detail page -->
<section class="appointments-section">
    <h3>📅 Appointments</h3>
    <button onclick="scheduleAppointment('{{ patient_id }}')">
        + Schedule Appointment
    </button>

    <div class="appointments-list">
        <!-- Show upcoming and past appointments -->
    </div>
</section>
```

### 2. **Integration with Follow-ups**

**Existing:** `follow_ups` collection
**Enhancement:** Convert follow-up to appointment

```python
# Add button on follow-up page
def schedule_from_followup(followup_id):
    followup = get_followup(followup_id)

    # Pre-fill appointment form
    appointment = {
        'patient_id': followup['patient_id'],
        'appointment_date': followup['followup_date'],
        'appointment_type': 'follow_up',
        'follow_up_id': followup_id,
        # ... other fields
    }

    return render_template('schedule_appointment.html', appointment=appointment)
```

**UI Addition:**
```html
<!-- On follow-up page -->
<button class="btn-primary" onclick="convertToAppointment('{{ followup_id }}')">
    📅 Schedule Appointment
</button>
```

### 3. **Integration with Messaging System**

**Existing:** SMS/WhatsApp messaging
**New:** Automated appointment reminders

```python
# Use existing messaging infrastructure
from messaging_service import MessagingService
from message_templates import MessageTemplates

def send_appointment_reminders():
    # 24-hour reminders
    appointments_24h = get_appointments_in_24_hours()
    for appt in appointments_24h:
        if not appt['reminder_24h_sent']:
            MessagingService.send_with_fallback(
                user_id=appt['patient_id'],
                template_name='APPOINTMENT_REMINDER_24H',
                app_link=f'/appointments/{appt["id"]}'
            )
            mark_reminder_sent(appt['id'], '24h')

    # 2-hour reminders (similar)
```

**Reuse existing templates:**
- `APPOINTMENT_REMINDER_24H`
- `APPOINTMENT_REMINDER_2H`
- `APPOINTMENT_CONFIRMED`
- `APPOINTMENT_CANCELLED`

### 4. **Integration with Dashboard**

**Existing:** Dashboard shows patient stats, AI usage, etc.
**Addition:** Show today's appointments

```html
<!-- Add to dashboard.html -->
<div class="dashboard-widget">
    <h3>📅 Today's Appointments</h3>
    <div class="appointment-summary">
        <span class="stat">{{ total_today }}</span> appointments
        <span class="stat success">{{ completed }}</span> completed
        <span class="stat pending">{{ upcoming }}</span> remaining
    </div>
    <a href="{{ url_for('appointments') }}" class="btn-link">
        View All →
    </a>
</div>
```

### 5. **Integration with Notifications**

**Existing:** `NotificationService`
**Enhancement:** Appointment notifications

```python
# When appointment is scheduled
NotificationService.create_notification(
    user_id=physio_id,
    title='New Appointment Scheduled',
    message=f'Appointment with {patient_name} on {date} at {time}',
    category='appointment',
    action_url=f'/appointments/{appointment_id}'
)

# When patient checks in
NotificationService.create_notification(
    user_id=physio_id,
    title='Patient Checked In',
    message=f'{patient_name} has arrived for their {time} appointment',
    category='appointment',
    action_url=f'/appointments/{appointment_id}'
)
```

---

## 💰 Pricing & Monetization Strategy

### Recommended Pricing Model

**Option 1: Included in Base Plans** (Recommended for Launch)

```
Solo Plan (₹4,200/month):
✅ Unlimited appointments
✅ Calendar view
✅ SMS/WhatsApp reminders
✅ Basic reporting
❌ No secretary access

Team Plans (₹19,999-39,999/month):
✅ Everything in Solo
✅ Multi-physio scheduling
✅ Secretary access (2 seats included)
✅ Advanced reporting
✅ Patient intake kiosk

Institute Plans (₹10,999-14,499/month):
✅ Everything in Team
✅ Secretary access (3-5 seats included)
✅ Multi-location support
✅ Centralized dashboard
```

**Option 2: Add-On Pricing** (For Extra Seats)

```
Base Plans: Include basic scheduling

Add-Ons:
+ Secretary Seat: ₹499/month per seat
+ Patient Intake Kiosk: ₹999/month (unlimited tokens)
+ Advanced Analytics: ₹1,499/month
```

**My Recommendation:** Option 1
- **Why:** Bundling increases perceived value
- **Upsell:** Institute plans get more secretary seats
- **Differentiation:** Scheduling becomes a key feature, not an add-on
- **Simplicity:** Easier to explain to customers

### Value Proposition

**For Solo Physios:**
- "Stop using Google Calendar - manage everything in one place"
- "Never miss an appointment with automated SMS reminders"
- "Save time with patient self-check-in"

**For Institutes:**
- "Empower your receptionist to manage all physios' schedules"
- "Reduce wait times with patient intake forms"
- "Centralized appointment dashboard for better oversight"

---

## 🚀 Implementation Roadmap

### Phase 1: Core Scheduling (Week 1)

**Backend:**
- ✅ Create database schema
- ✅ Add `appointments` collection
- ✅ Add `working_hours` collection
- ✅ Add `secretary_access` collection
- ✅ Create API endpoints:
  - `POST /api/appointments` - Create appointment
  - `GET /api/appointments` - List appointments
  - `GET /api/appointments/<id>` - Get appointment details
  - `PUT /api/appointments/<id>` - Update appointment
  - `DELETE /api/appointments/<id>` - Cancel appointment
  - `POST /api/appointments/<id>/checkin` - Check in patient
  - `GET /api/appointments/today` - Today's appointments
  - `GET /api/appointments/calendar` - Calendar data

**Frontend:**
- ✅ Create calendar view page
- ✅ Create appointment form
- ✅ Add "Appointments" to navbar
- ✅ Integrate with existing patients
- ✅ Style matching existing theme

**Testing:**
- ✅ Solo physio can schedule
- ✅ View calendar
- ✅ Edit/cancel appointments

**Deliverable:** Working appointment scheduling for solo physios

---

### Phase 2: Secretary & Multi-User (Week 2)

**Backend:**
- ✅ Add `secretary` role
- ✅ Implement permission system
- ✅ Secretary access management
- ✅ API endpoints:
  - `POST /api/secretary/access` - Grant secretary access
  - `GET /api/secretary/physios` - Get assigned physios
  - `GET /api/secretary/appointments` - View institute appointments

**Frontend:**
- ✅ Secretary access management UI (for admins)
- ✅ Multi-physio selector in appointment form
- ✅ Filter by physio in calendar
- ✅ Today's appointments dashboard

**Testing:**
- ✅ Secretary can schedule for multiple physios
- ✅ Permissions work correctly
- ✅ Institute admin can manage access

**Deliverable:** Full multi-user scheduling system

---

### Phase 3: Reminders & Integration (Week 2-3)

**Backend:**
- ✅ Integrate with existing messaging system
- ✅ Cron jobs for reminders:
  - 24-hour reminder job
  - 2-hour reminder job
- ✅ Integration with follow-ups
- ✅ Dashboard widgets

**Frontend:**
- ✅ Add appointment widgets to dashboard
- ✅ Link from patient detail page
- ✅ Link from follow-up page
- ✅ Notification integration

**Testing:**
- ✅ Reminders sent correctly
- ✅ Follow-up conversion works
- ✅ Dashboard shows appointments

**Deliverable:** Fully integrated scheduling with reminders

---

### Phase 4: Patient Intake (Optional - Week 4)

**Backend:**
- ✅ Add `patient_intake_sessions` collection
- ✅ Token generation system
- ✅ API endpoints:
  - `POST /api/intake/start` - Generate intake session
  - `GET /api/intake/<token>` - Get intake form
  - `POST /api/intake/<token>/submit` - Submit form

**Frontend:**
- ✅ Tablet-optimized intake form
- ✅ QR code generation
- ✅ Body diagram for pain location
- ✅ Progress indicator
- ✅ Auto-logout after submission

**Testing:**
- ✅ Token access works
- ✅ Data saves correctly
- ✅ Physio sees intake data
- ✅ Session expires properly

**Deliverable:** Patient self-service intake kiosk

---

## 📊 Success Metrics

### Key Performance Indicators (KPIs)

**Adoption:**
- % of users who enable scheduling
- Average appointments per physio per week
- Secretary adoption rate (for institutes)

**Usage:**
- Appointments scheduled per month
- Reminders sent per month
- Check-in rate (% of appointments with check-in)
- Cancellation rate
- No-show rate (without reminder vs. with reminder)

**Business:**
- Upgrade rate from Solo to Team/Institute (for scheduling features)
- Secretary seat add-ons purchased
- Customer satisfaction with scheduling module

**Expected Impact:**
- Reduce no-shows by 30-40% (with reminders)
- Save 5-10 minutes per appointment (with intake forms)
- Eliminate need for Google Calendar (100% adoption target)

---

## 🔧 Technical Considerations

### 1. **Timezone Handling**

```python
# Store all times in UTC
from datetime import datetime, timezone

appointment['appointment_datetime_utc'] = datetime(2026, 2, 15, 14, 0, tzinfo=timezone.utc)

# Display in user's timezone
user_timezone = get_user_timezone(user_id)
local_time = appointment['appointment_datetime_utc'].astimezone(user_timezone)
```

### 2. **Conflict Detection**

```python
def check_appointment_conflict(physio_id, date, start_time, end_time, exclude_appointment_id=None):
    """Check if appointment slot is available"""

    # Query overlapping appointments
    conflicts = db.collection('appointments').where([
        ('physio_id', '==', physio_id),
        ('appointment_date', '==', date),
        ('status', 'in', ['scheduled', 'confirmed', 'checked_in']),
        ('deleted', '==', False)
    ]).get()

    for appt in conflicts:
        if appt.id == exclude_appointment_id:
            continue  # Skip self when editing

        # Check if time ranges overlap
        if times_overlap(start_time, end_time, appt['appointment_time'], appt['end_time']):
            return {
                'conflict': True,
                'appointment': appt.to_dict()
            }

    return {'conflict': False}
```

### 3. **Calendar Generation**

```python
def generate_calendar_data(physio_id, start_date, end_date):
    """Generate calendar view data"""

    # Get working hours
    working_hours = get_working_hours(physio_id)

    # Get appointments in date range
    appointments = get_appointments(physio_id, start_date, end_date)

    # Generate time slots
    calendar_data = {
        'dates': [],
        'time_slots': [],
        'appointments': {},
        'available_slots': {}
    }

    # ... (generate data structure for frontend)

    return calendar_data
```

### 4. **Performance Optimization**

```python
# Use indexes for common queries
@app.route('/api/appointments/today')
def get_todays_appointments():
    # Optimized query with index on (physio_id, appointment_date)
    today = datetime.now().date()

    appointments = db.collection('appointments') \
        .where('physio_id', '==', current_user.id) \
        .where('appointment_date', '==', str(today)) \
        .where('deleted', '==', False) \
        .order_by('appointment_time') \
        .get()

    # Cache for 5 minutes
    cache.set(f'appointments_today_{current_user.id}', appointments, timeout=300)

    return jsonify([a.to_dict() for a in appointments])
```

### 5. **Data Integrity**

```python
# Soft delete appointments (don't actually delete)
def cancel_appointment(appointment_id, reason):
    appointment = db.collection('appointments').document(appointment_id)

    appointment.update({
        'status': 'cancelled',
        'cancelled_at': SERVER_TIMESTAMP,
        'cancelled_by': current_user.id,
        'cancellation_reason': reason,
        'deleted': False  # Keep for history
    })

    # Send cancellation notification
    send_cancellation_sms(appointment)
```

---

## 🎯 Launch Strategy

### Beta Testing (Week 3)

**Internal Testing:**
1. Use with 3-5 pilot users (solo physios)
2. Collect feedback on UI/UX
3. Fix critical bugs
4. Optimize performance

**Institute Testing:**
1. Select 1-2 institute partners
2. Train secretaries
3. Monitor usage patterns
4. Gather feature requests

### Soft Launch (Week 4)

**Rollout Plan:**
1. Enable for existing Solo plan users
2. Announce via email newsletter
3. Add feature highlights to pricing page
4. Update documentation

**Communication:**
- Email: "New Feature: Integrated Appointment Scheduling"
- Blog post: "Say Goodbye to Google Calendar"
- Tutorial video: "How to Schedule Your First Appointment"

### Full Launch (Month 2)

**Marketing:**
- Featured on homepage
- Case study with institute partner
- Comparison: PhysiologicPRISM vs. External Calendar Tools
- Social media campaign

**Upsell:**
- Email to Solo users: "Upgrade to Team for Secretary Access"
- In-app promotion for secretary seats

---

## 📝 Documentation Needed

### User Documentation

1. **Quick Start Guide:**
   - "Scheduling Your First Appointment"
   - "Setting Your Working Hours"
   - "Managing Appointments"

2. **Secretary Guide:**
   - "Getting Started as a Secretary"
   - "Scheduling for Multiple Physios"
   - "Using the Check-In System"

3. **Admin Guide:**
   - "Granting Secretary Access"
   - "Managing Institute Schedules"
   - "Appointment Analytics"

4. **Patient Guide:**
   - "Filling Out Your Intake Form"
   - "Checking In for Your Appointment"

### Technical Documentation

1. **API Documentation:**
   - Appointment endpoints
   - Request/response formats
   - Error codes

2. **Database Schema:**
   - Collection structures
   - Indexes
   - Relationships

3. **Integration Guide:**
   - Linking appointments to patients
   - Follow-up integration
   - Messaging integration

---

## ❓ Open Questions / Decisions Needed

### 1. **Appointment Duration Options**

**Question:** What durations should we offer?
**Options:**
- A) Fixed: 30, 45, 60 minutes
- B) Flexible: Custom duration input
- C) Both: Preset + custom

**Recommendation:** C (Both) - Flexibility with convenience

### 2. **Recurring Appointments**

**Question:** Support recurring appointments?
**Options:**
- A) Yes - Phase 1
- B) Yes - Phase 2
- C) No - Keep it simple

**Recommendation:** B (Phase 2) - Nice-to-have, not essential for MVP

### 3. **Waitlist**

**Question:** If slot is full, allow waitlist?
**Options:**
- A) Yes - Notify if cancellation occurs
- B) No - Just show next available
- C) Later feature

**Recommendation:** C (Later) - Adds complexity

### 4. **Mobile App vs. Web**

**Question:** Build mobile app or web-only?
**Options:**
- A) Web-only (responsive)
- B) Mobile app for patient intake
- C) Both

**Recommendation:** A (Web-only) - Responsive web works on all devices, no app store approval needed

### 5. **Integration with External Calendars**

**Question:** Allow sync with Google Calendar?
**Options:**
- A) Yes - Two-way sync
- B) Yes - One-way export only
- C) No - Keep data centralized

**Recommendation:** B (One-way export) - Users can export to GCal if needed, but primary source is PhysiologicPRISM

---

## 🚦 Next Steps

### Immediate Actions (This Week)

1. ✅ **Review This Plan** - Approve approach
2. ✅ **Finalize Design Decisions** - Answer open questions
3. ✅ **Start Phase 1 Development** - Begin backend schema
4. ✅ **Create UI Mockups** - Finalize calendar design

### Before Development

- [ ] **User Research** - Interview 2-3 potential users
- [ ] **Competitor Analysis** - How do others handle this?
- [ ] **Pricing Finalization** - Confirm bundling strategy

### During Development

- [ ] **Weekly Progress Updates** - Track against timeline
- [ ] **User Testing** - Get feedback early and often
- [ ] **Documentation** - Write as we build

---

## 📞 Support & Maintenance

### Post-Launch Support

**Expected Issues:**
- Users learning new feature
- Permission confusion (secretary vs. physio)
- Reminder delivery issues
- Timezone confusion

**Support Plan:**
- FAQ section in docs
- Video tutorials
- Email support
- In-app help tooltips

### Maintenance

**Regular Tasks:**
- Monitor reminder delivery
- Check database performance
- Review user feedback
- Fix bugs

**Updates:**
- Monthly feature improvements
- Performance optimizations
- User-requested enhancements

---

## 🎊 Summary

### What We're Building

**A simple, integrated appointment scheduling module that:**
- ✅ Works for solo physios AND institutes with secretaries
- ✅ Eliminates need for Google Calendar
- ✅ Keeps all data in PhysiologicPRISM
- ✅ Matches existing UI/design
- ✅ Bundles with current pricing
- ✅ Integrates with existing features (patients, follow-ups, messaging)

### Why This Will Succeed

**User Pain Point:** "I hate switching between apps and calendars"
**Our Solution:** "Everything in one place"

**Value Props:**
1. **Convenience** - No more Google Calendar tab switching
2. **Integration** - Linked to patients, follow-ups, reminders
3. **Automation** - SMS reminders reduce no-shows
4. **Efficiency** - Patient intake saves physio time
5. **Collaboration** - Secretaries can help manage schedules

### Timeline

- **Week 1:** Core scheduling for solo physios ✅
- **Week 2:** Secretary access & multi-user ✅
- **Week 3:** Reminders & integration ✅
- **Week 4:** Patient intake (optional) ✅
- **Month 2:** Full launch & marketing 🚀

---

## ✍️ Your Input Needed

Before I start building, please confirm:

1. **Approve this plan?** Any changes needed?
2. **Pricing strategy:** Bundled (Option 1) or Add-on (Option 2)?
3. **Phase 4 (Patient Intake):** Build now or later?
4. **Open questions:** Which options do you prefer?
5. **Timeline:** 2-3 weeks realistic for your launch?

**Ready to proceed?** I can start building Phase 1 (Core Scheduling) immediately! 🚀

---

**Last Updated:** February 12, 2026
**Document Version:** 1.0
**Author:** Implementation Planning Team
