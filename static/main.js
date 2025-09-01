document.addEventListener('DOMContentLoaded', () => {
  // ---- 1. Add New Patient: AI Past Questions ----
  const ageSexInput      = document.querySelector('input[name="age_sex"]');
  const presentTextarea  = document.querySelector('textarea[name="present_history"]');
  const pastTextarea     = document.getElementById('past_history');
  const brainBtn         = document.getElementById('suggest_questions');
  const genDiagnosisBtn  = document.getElementById('gen_diagnosis');
  const aiResponseDiv    = document.getElementById('ai_response');

  if (brainBtn && ageSexInput && presentTextarea && pastTextarea) {
    brainBtn.addEventListener('click', async () => {
      const payload = {
        age_sex: ageSexInput.value.trim(),
        present_history: presentTextarea.value.trim()
      };
      try {
        const res = await fetch('/ai_suggestion/past_questions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        pastTextarea.value = data.suggestion;
      } catch (err) {
        alert('Error: ' + err.message);
      }
    });
  }

  if (genDiagnosisBtn && ageSexInput && presentTextarea && pastTextarea && aiResponseDiv) {
    genDiagnosisBtn.addEventListener('click', async () => {
      const payload = {
        age_sex:         ageSexInput.value.trim(),
        present_history: presentTextarea.value.trim(),
        past_history:    pastTextarea.value.trim()
      };
      try {
        const res  = await fetch('/ai_suggestion/provisional_diagnosis', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        aiResponseDiv.textContent = data.suggestion;
      } catch (err) {
        alert('Error: ' + err.message);
      }
    });
  }
  
// ---- 1.5 Subjective Examination Screen ----
if (document.getElementById('subjective-form')) {
  const form = document.getElementById('subjective-form');

  const ageSex   = form.querySelector('input[name="age_sex"]')?.value.trim() || '';
  const present  = form.querySelector('input[name="present_history"]')?.value.trim() || '';
  const past     = form.querySelector('input[name="past_history"]')?.value.trim() || '';

  const subjectiveFieldIds = [
    'body_structure',
    'body_function',
    'activity_performance',
    'activity_capacity',
    'contextual_environmental',
    'contextual_personal'
  ];

  function collectInputs() {
    const inputs = {};
    subjectiveFieldIds.forEach(id => {
      const el = document.getElementById(id);
      inputs[id] = (el?.value || '').trim();
    });
    return inputs;
  }

  // Per-field 🧠 buttons -> /ai_suggestion/subjective/<field>
  document.querySelectorAll('#subjective-form .ai-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const field  = btn.dataset.field;              // matches data-field in HTML
      const inputs = collectInputs();                // send all fields so backend can summarize "other findings"
      try {
        const res = await fetch(`/ai_suggestion/subjective/${field}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            age_sex: ageSex,
            present_history: present,
            past_history: past,
            inputs
          })
        });
        const { suggestion, error } = await res.json();
        if (error) throw new Error(error);

        const pop = document.getElementById(`${field}_popup`);
        if (pop) {
          pop.textContent = suggestion || 'No suggestion';
          pop.style.display = 'block';
        }
      } catch (e) {
        alert('Error: ' + e.message);
        console.error(e);
      }
    });
  });

  // 🩺 stethoscope -> /ai_suggestion/subjective_diagnosis
  document.getElementById('gen_subjective_dx')?.addEventListener('click', async () => {
    const inputs = collectInputs();
    try {
      const res = await fetch('/ai_suggestion/subjective_diagnosis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          age_sex: ageSex,
          present_history: present,
          past_history: past,
          inputs
        })
      });
      const { suggestion, error } = await res.json();
      if (error) throw new Error(error);
      alert('Provisional impressions:\n\n' + (suggestion || 'No output'));
    } catch (e) {
      alert('Error: ' + e.message);
      console.error(e);
    }
  });
}


  // ---- 2. Subjective/Patient Perspectives Screen ----
  if (document.getElementById('perspectives-form')) {
    const prevAdd   = JSON.parse(localStorage.getItem('add_patient_data')     || '{}');
    const prevSubj  = JSON.parse(localStorage.getItem('subjective_inputs')    || '{}');
    let   prevPersp = JSON.parse(localStorage.getItem('perspectives_inputs') || '{}');

    const allPrev = {
      age_sex:         prevAdd.age_sex || '',
      present_history: prevAdd.present_history || '',
      past_history:    prevAdd.past_history || '',
      subjective:      prevSubj,
      perspectives:    prevPersp
    };

    // Per-field brain buttons
    document.querySelectorAll('.ai-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const field = btn.dataset.field;
        const value = document.getElementById(field).value.trim();
        prevPersp[field] = value;
        localStorage.setItem('perspectives_inputs', JSON.stringify(prevPersp));

        try {
          const res = await fetch(`/ai_suggestion/perspectives/${field}`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ previous: allPrev, inputs: { [field]: value } })
          });
          const { suggestion, error } = await res.json();
          if (error) throw new Error(error);
          const pop = document.getElementById(field + '_popup');
          pop.innerText     = suggestion;
          pop.style.display = 'block';
        } catch (e) {
          alert('Error: ' + e.message);
        }
      });
    });

    // Provisional suggestion button
    const genPerspDx = document.getElementById('gen_perspectives_dx');
    if (genPerspDx) {
      genPerspDx.addEventListener('click', async () => {
        const inputs = {};
        ['knowledge','attribution','expectation','consequences_awareness','locus_of_control','affective_aspect']
          .forEach(name => {
            inputs[name] = document.getElementById(name).value.trim();
          });

        try {
          const res = await fetch('/ai_suggestion/perspectives_diagnosis', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ previous: allPrev, inputs })
          });
          const { suggestion, error } = await res.json();
          if (error) throw new Error(error);
          alert("Provisional Impressions:\n\n" + suggestion);
        } catch (e) {
          alert('Error: ' + e.message);
        }
      });
    }
  }

  // ---- 3. Initial Plan Screen ----
  if (document.getElementById('initial-plan-form')) {
    const prevAdd   = JSON.parse(localStorage.getItem('add_patient_data')    || '{}');
    const prevSubj  = JSON.parse(localStorage.getItem('subjective_inputs')   || '{}');
    const prevPersp = JSON.parse(localStorage.getItem('perspectives_inputs')|| '{}');
    let prevAssess  = JSON.parse(localStorage.getItem('initial_plan_assessments') || '{}');

    const allPrev = {
      age_sex:         prevAdd.age_sex        || '',
      present_history: prevAdd.present_history|| '',
      past_history:    prevAdd.past_history   || '',
      subjective:      prevSubj,
      perspectives:    prevPersp,
      assessments:     prevAssess
    };

    document.querySelectorAll('.ai-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const field     = btn.dataset.field;
        const selection = document.getElementById(field).value.trim();
        prevAssess[field] = { choice: selection };
        localStorage.setItem('initial_plan_assessments', JSON.stringify(prevAssess));
        try {
          const res = await fetch(`/ai_suggestion/initial_plan/${field}`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ previous: allPrev, selection })
          });
          const { suggestion, error } = await res.json();
          if (error) throw new Error(error);
          document.getElementById(field + '_suggestion').value = suggestion;
        } catch (err) {
          alert('Error: ' + err.message);
        }
      });
    });

    const genInitialSummary = document.getElementById('gen_initial_summary');
    if (genInitialSummary) {
      genInitialSummary.addEventListener('click', async () => {
        ['active_movements','passive_movements','passive_over_pressure',
         'resisted_movements','combined_movements','special_tests','neurodynamic']
          .forEach(f => {
            const details = (document.getElementById(f + '_details')?.value||'').trim();
            prevAssess[f] = { 
              choice:  prevAssess[f]?.choice || '',
              details
            };
          });
        localStorage.setItem('initial_plan_assessments', JSON.stringify(prevAssess));
        try {
          const res = await fetch('/ai_suggestion/initial_plan_summary', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ previous: allPrev, assessments: prevAssess })
          });
          const { summary, error } = await res.json();
          if (error) throw new Error(error);
          alert("Assessment Summary & Provisional Dx:\n\n" + summary);
        } catch (e) {
          alert('Error: ' + e.message);
        }
      });
    }
  }

  // ---- 4. Pathophysiological Mechanism Screen ----
  if (document.querySelector('select#possible_source')) {
    const prevAdd   = JSON.parse(localStorage.getItem('add_patient_data')    || '{}');
    const prevSubj  = JSON.parse(localStorage.getItem('subjective_inputs')   || '{}');
    const prevPersp = JSON.parse(localStorage.getItem('perspectives_inputs')|| '{}');
    const assessments = JSON.parse(localStorage.getItem('initial_plan_assessments')|| '{}');
    const allPrev = {
      age_sex:         prevAdd.age_sex||'',
      present_history: prevAdd.present_history||'',
      past_history:    prevAdd.past_history||'',
      subjective:      prevSubj,
      perspectives:    prevPersp,
      assessments
    };

    document.querySelectorAll('.ai-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const field     = btn.dataset.field;
        const selection = document.getElementById(field).value.trim();
        try {
          const res = await fetch('/ai_suggestion/patho/possible_source', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ previous: allPrev, selection })
          });
          const { suggestion, error } = await res.json();
          if (error) throw new Error(error);
          const pop = document.getElementById(field + '_popup');
          pop.innerText     = suggestion;
          pop.style.display = 'block';
        } catch (e) {
          alert('Error: ' + e.message);
        }
      });
    });
  }

  // ---- 5. Chronic Disease Factors Screen ----
  if (document.getElementById('specific_factors')) {
    const prevAdd   = JSON.parse(localStorage.getItem('add_patient_data')    || '{}');
    const prevSubj  = JSON.parse(localStorage.getItem('subjective_inputs')   || '{}');
    const prevPersp = JSON.parse(localStorage.getItem('perspectives_inputs')|| '{}');
    const assessments = JSON.parse(localStorage.getItem('initial_plan_assessments')|| '{}');
    const allPrev = {
      age_sex:         prevAdd.age_sex||'',
      present_history: prevAdd.present_history||'',
      past_history:    prevAdd.past_history||'',
      subjective:      prevSubj,
      perspectives:    prevPersp,
      assessments
    };

    const chronicBtn = document.querySelector('.ai-btn');
    if (chronicBtn) {
      chronicBtn.addEventListener('click', async e => {
        const field  = chronicBtn.dataset.field;
        const text   = document.getElementById(field).value.trim();
        const causes = Array.from(document.querySelectorAll('input[name="maintenance_causes"]:checked')).map(cb => cb.value);
        try {
          const res = await fetch('/ai_suggestion/chronic/specific_factors', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({
              previous: allPrev,
              input: text,
              causes
            })
          });
          const { suggestion, error } = await res.json();
          if (error) throw new Error(error);
          const pop = document.getElementById(field + '_popup');
          pop.innerText     = suggestion;
          pop.style.display = 'block';
        } catch (err) {
          alert('Error: ' + err.message);
        }
      });
    }
  }

  // ---- 6. Clinical Flags Screen ----
  if (document.getElementById('clinical-flags-form')) {
    const prevAdd   = JSON.parse(localStorage.getItem('add_patient_data')    || '{}');
    const prevSubj  = JSON.parse(localStorage.getItem('subjective_inputs')   || '{}');
    const prevPersp = JSON.parse(localStorage.getItem('perspectives_inputs')|| '{}');
    const prevAssess= JSON.parse(localStorage.getItem('initial_plan_assessments')|| '{}');

    const allPrev = {
      age_sex:         prevAdd.age_sex||'',
      present_history: prevAdd.present_history||'',
      past_history:    prevAdd.past_history||'',
      subjective:      prevSubj,
      perspectives:    prevPersp,
      assessments:     prevAssess
    };

    // highlight relevant flags
    const highlights = [];
    if (allPrev.subjective.pain_irritability === 'Present') {
      highlights.push('yellow_flags');
    }
    if (allPrev.assessments.special_tests?.choice === 'Absolutely Contraindicated') {
      highlights.push('black_flags');
    }
    highlights.forEach(id => {
      document.getElementById(id + '_block')?.classList.add('highlight');
    });

    document.querySelectorAll('.ai-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const field = btn.dataset.field;
        const text  = document.getElementById(field).value.trim();
        try {
          const res = await fetch(`/ai_suggestion/clinical_flags/${window.patientId}/suggest`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ previous: allPrev, field, text })
          });
          const { suggestions, error } = await res.json();
          if (error) throw new Error(error);
          const hint = document.getElementById(field + '_hint');
          hint.innerText     = suggestions;
          hint.style.display = 'block';
        } catch (e) {
          alert('Error: ' + e.message);
        }
      });
    });
  }

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

  // ---- 10. Global: Hide popups when clicking outside ----
  document.addEventListener('click', e => {
    if (!e.target.closest('.control-group') && !e.target.closest('.field-block')) {
      document.querySelectorAll('.ai-popup').forEach(p => p.style.display = 'none');
    }
  });
});
