  // ---- 7. Objective Assessment Screen ----
  if (document.getElementById('objective-assessment-form')) {
    const prevAdd    = JSON.parse(localStorage.getItem('add_patient_data')    || '{}');
    const prevSubj   = JSON.parse(localStorage.getItem('subjective_inputs')   || '{}');
    const prevPersp  = JSON.parse(localStorage.getItem('perspectives_inputs')|| '{}');
    const prevAssess = JSON.parse(localStorage.getItem('initial_plan_assessments')|| '{}');

    const allPrev = {
      age_sex:         prevAdd.age_sex         || '',
      present_history: prevAdd.present_history || '',
      past_history:    prevAdd.past_history    || '',
      subjective:      prevSubj,
      perspectives:    prevPersp,
      assessments:     prevAssess
    };

    document.querySelectorAll('#objective-assessment-form .ai-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const field = btn.dataset.field;
        const popup = document.getElementById(field + '_popup');
        popup.textContent = 'Thinking…';
        popup.style.display = 'block';
        try {
          allPrev.assessments[field] = { choice: document.getElementById(field).value };
          localStorage.setItem('initial_plan_assessments', JSON.stringify(allPrev.assessments));
          const res = await fetch(`/ai_suggestion/objective_assessment/${field}`, {
            method: 'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ previous: allPrev, value: allPrev.assessments[field].choice })
          });
          const { suggestion, error } = await res.json();
          if (error) throw new Error(error);
          popup.textContent = suggestion.trim();
        } catch (err) {
          popup.textContent = 'Error: ' + err.message;
          console.error(err);
        }
      });
    });

    document.getElementById('gen_provisional_dx')?.addEventListener('click', async () => {
      try {
        allPrev.assessments.plan.details = document.getElementById('plan_details').value.trim();
        localStorage.setItem('initial_plan_assessments', JSON.stringify(allPrev.assessments));
        const res = await fetch(`/ai_suggestion/provisional_diagnosis`, {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ age_sex: allPrev.age_sex, present_history: allPrev.present_history, past_history: allPrev.past_history })
        });
        const { suggestion, error } = await res.json();
        if (error) throw new Error(error);
        alert("Provisional Diagnosis:\n\n" + suggestion.trim());
      } catch (err) {
        alert("Error: " + err.message);
        console.error(err);
      }
    });
  }

  // ---- 8. SMART Goals and Treatment Plan ----
  document.querySelectorAll('.ai-btn[data-screen="smart_goals"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const field = btn.dataset.field;
      const popup = document.getElementById(field + '_popup');
      const input = document.getElementById(field).value;
      popup.textContent = 'Thinking…';
      popup.style.display = 'block';
      try {
        const resp = await fetch(`/ai_suggestion/smart_goals/${field}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            patient_id: window.patientId,
            previous: JSON.parse(localStorage.getItem('add_patient_data')    || '{}'),
            previous_subjective: JSON.parse(localStorage.getItem('subjective_inputs')   || '{}'),
            previous_perspectives: JSON.parse(localStorage.getItem('perspectives_inputs') || '{}'),
            previous_assessments: JSON.parse(localStorage.getItem('initial_plan_assessments')  || '{}'),
            input
          })
        });
        const { suggestion, error } = await resp.json();
        popup.textContent = error || suggestion;
      } catch (err) {
        console.error(err);
        popup.textContent = 'Error fetching suggestion';
      }
    });
  });

  // Treatment Plan (per-field, generic ai-btn)
  document.querySelectorAll('.ai-btn').forEach(btn => {
    if (btn.closest('[data-screen="treatment_plan"]')) {
      btn.addEventListener('click', async () => {
        const field = btn.dataset.field;
        const popup = document.getElementById(field + '_popup');
        popup.textContent = 'Loading…';
        popup.style.display = 'block';
        try {
          const resp = await fetch(`/ai_suggestion/treatment_plan/${field}`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({
              patient_id: window.patientId,
              input: document.getElementById(field).value
            })
          });
          const data = await resp.json();
          popup.textContent = data.suggestion || data.error || 'No suggestion';
        } catch (err) {
          popup.textContent = 'Error fetching suggestion';
          console.error(err);
        }
      });
    }
  });

  // Treatment Plan Summary
  const genSummaryBtn = document.getElementById('gen_summary');
  if (genSummaryBtn) {
    genSummaryBtn.addEventListener('click', async () => {
      try {
        const resp = await fetch(`/ai_suggestion/treatment_plan_summary/${window.patientId}`);
        const data = await resp.json();
        alert("Treatment Summary:\n\n" + (data.summary || data.error));
      } catch (err) {
        console.error(err);
        alert('Error generating summary');
      }
    });
  }

  // ---- 9. Follow-up Suggestions ----
  document.querySelectorAll('.ai-btn').forEach(btn => {
    if (btn.closest('[data-screen="followup"]')) {
      btn.addEventListener('click', async () => {
        const textarea = btn.previousElementSibling;
        const field    = textarea.id;
        const popup    = document.getElementById(field + '_popup');
        popup.textContent = 'Thinking…';
        popup.style.display = 'block';
        try {
          const resp = await fetch(`/ai_followup_suggestion/${window.patientId}`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({
              session_number: document.querySelector('input[name="session_number"]').value,
              session_date:   document.querySelector('input[name="session_date"]').value,
              grade:          document.querySelector('select[name="grade"]').value,
              perception:     document.querySelector('select[name="belief_treatment"]').value,
              feedback:       document.querySelector('textarea[name="belief_feedback"]').value
            })
          });
          const data = await resp.json();
          popup.textContent = data.suggestion || 'No suggestion available';
        } catch(err) {
          console.error(err);
          popup.textContent = 'Error fetching suggestion';
        }
      });
    }
  });