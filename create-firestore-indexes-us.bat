@echo off
echo Creating Firestore indexes for US project...
echo.

gcloud config set project physiologicprism-us

echo Creating indexes...
echo.

REM Index 1: ai_analytics - event_type + timestamp DESC
gcloud firestore indexes composite create ^
  --collection-group=ai_analytics ^
  --query-scope=COLLECTION ^
  --field-config=field-path=event_type,order=ASCENDING ^
  --field-config=field-path=timestamp,order=DESCENDING ^
  --quiet

REM Index 2: ai_analytics - event_type + timestamp ASC
gcloud firestore indexes composite create ^
  --collection-group=ai_analytics ^
  --query-scope=COLLECTION ^
  --field-config=field-path=event_type,order=ASCENDING ^
  --field-config=field-path=timestamp,order=ASCENDING ^
  --quiet

REM Index 3: audit_logs - user_id + timestamp
gcloud firestore indexes composite create ^
  --collection-group=audit_logs ^
  --query-scope=COLLECTION ^
  --field-config=field-path=user_id,order=ASCENDING ^
  --field-config=field-path=timestamp,order=DESCENDING ^
  --quiet

REM Index 4: follow_ups - patient_id + session_date
gcloud firestore indexes composite create ^
  --collection-group=follow_ups ^
  --query-scope=COLLECTION ^
  --field-config=field-path=patient_id,order=ASCENDING ^
  --field-config=field-path=session_date,order=DESCENDING ^
  --quiet

REM Index 5: follow_ups - patient_id + session_number
gcloud firestore indexes composite create ^
  --collection-group=follow_ups ^
  --query-scope=COLLECTION ^
  --field-config=field-path=patient_id,order=ASCENDING ^
  --field-config=field-path=session_number,order=ASCENDING ^
  --quiet

REM Index 6: invoices - user_id + invoice_date
gcloud firestore indexes composite create ^
  --collection-group=invoices ^
  --query-scope=COLLECTION ^
  --field-config=field-path=user_id,order=ASCENDING ^
  --field-config=field-path=invoice_date,order=DESCENDING ^
  --quiet

REM Index 7: notifications - user_id + read
gcloud firestore indexes composite create ^
  --collection-group=notifications ^
  --query-scope=COLLECTION ^
  --field-config=field-path=user_id,order=ASCENDING ^
  --field-config=field-path=read,order=ASCENDING ^
  --quiet

REM Index 8: notifications - user_id + read + category
gcloud firestore indexes composite create ^
  --collection-group=notifications ^
  --query-scope=COLLECTION ^
  --field-config=field-path=user_id,order=ASCENDING ^
  --field-config=field-path=read,order=ASCENDING ^
  --field-config=field-path=category,order=ASCENDING ^
  --quiet

REM Index 9: patients - created_by + created_at
gcloud firestore indexes composite create ^
  --collection-group=patients ^
  --query-scope=COLLECTION ^
  --field-config=field-path=created_by,order=ASCENDING ^
  --field-config=field-path=created_at,order=ASCENDING ^
  --quiet

REM Index 10: users - approved + is_admin
gcloud firestore indexes composite create ^
  --collection-group=users ^
  --query-scope=COLLECTION ^
  --field-config=field-path=approved,order=ASCENDING ^
  --field-config=field-path=is_admin,order=ASCENDING ^
  --quiet

REM Index 11: users - institute + is_admin
gcloud firestore indexes composite create ^
  --collection-group=users ^
  --query-scope=COLLECTION ^
  --field-config=field-path=institute,order=ASCENDING ^
  --field-config=field-path=is_admin,order=ASCENDING ^
  --quiet

REM Index 12: users - is_admin + approved + institute
gcloud firestore indexes composite create ^
  --collection-group=users ^
  --query-scope=COLLECTION ^
  --field-config=field-path=is_admin,order=ASCENDING ^
  --field-config=field-path=approved,order=ASCENDING ^
  --field-config=field-path=institute,order=ASCENDING ^
  --quiet

echo.
echo ========================================
echo Essential indexes created successfully!
echo ========================================
echo.
echo Note: Some indexes may take a few minutes to build.
echo Check status at: https://console.firebase.google.com/project/physiologicprism-us/firestore/indexes
echo.
pause
