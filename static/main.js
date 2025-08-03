document.addEventListener('DOMContentLoaded', () => {
  const ageSexInput      = document.querySelector('input[name="age_sex"]');
  const presentTextarea  = document.querySelector('textarea[name="present_history"]');
  const pastTextarea     = document.getElementById('past_history');
  const aiResponseDiv    = document.getElementById('ai_response');

  // 1) Suggest past-history questions
  document.getElementById('suggest_questions')?.addEventListener('click', async () => {
    const payload = {
      age_sex:         ageSexInput.value.trim(),
      present_history: presentTextarea.value.trim()
    };
    try {
      const res  = await fetch('/ai_suggestion/past_questions', {
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

  // 2) Generate provisional diagnoses
  document.getElementById('gen_diagnosis')?.addEventListener('click', async () => {
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
});
document.addEventListener('DOMContentLoaded', () => {
  const ageSexInput     = document.querySelector('input[name="age_sex"]');
  const presentInput    = document.querySelector('textarea[name="present_history"]');
  const pastInput       = document.querySelector('textarea[name="past_history"]');
  const fieldBtns       = document.querySelectorAll('.ai-btn');
  const genDxBtn        = document.getElementById('gen_subjective_dx');

  fieldBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      const field = btn.dataset.field;
      const inputs = {};
      document.querySelectorAll('.input-field')
              .forEach(el => inputs[el.name] = el.value.trim());

      const payload = {
        age_sex:         ageSexInput.value.trim(),
        present_history: presentInput.value.trim(),
        past_history:    pastInput?.value.trim() || '',
        inputs
      };

      try {
        const res = await fetch(`/ai_suggestion/subjective/${field}`, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify(payload)
        });
        const { suggestion, error } = await res.json();
        if (error) throw new Error(error);
        const popup = document.getElementById(field + '_popup');
        popup.innerText   = suggestion;
        popup.style.display = 'block';
      } catch (e) {
        alert('Error: ' + e.message);
      }
    });
  });

  genDxBtn?.addEventListener('click', async () => {
    const inputs = {};
    document.querySelectorAll('.input-field')
            .forEach(el => inputs[el.name] = el.value.trim());

    const payload = {
      age_sex:         ageSexInput.value.trim(),
      present_history: presentInput.value.trim(),
      past_history:    pastInput?.value.trim() || '',
      inputs
    };

    try {
      const res = await fetch('/ai_suggestion/subjective_diagnosis', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      });
      const { suggestion, error } = await res.json();
      if (error) throw new Error(error);
      alert("Subjective Diagnosis:\n\n" + suggestion);
    } catch (e) {
      alert('Error: ' + e.message);
    }
  });
});
// ——— AI on Patient Perspectives screen ———
// Only run this block if we’re on the Perspectives page
if (document.getElementById('perspectives-form')) {
  // Load prior data
  const prevAdd   = JSON.parse(localStorage.getItem('add_patient_data')     || '{}');
  const prevSubj  = JSON.parse(localStorage.getItem('subjective_inputs')    || '{}');
  let   prevPersp = JSON.parse(localStorage.getItem('perspectives_inputs') || '{}');

  // Build a single “previous” object for the server
  const allPrev = {
    age_sex:         prevAdd.age_sex || '',
    present_history: prevAdd.present_history || '',
    past_history:    prevAdd.past_history || '',
    subjective:      prevSubj,
    perspectives:    prevPersp
  };

  // Attach click listeners to each 🧠 button
  document.querySelectorAll('.ai-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const field = btn.dataset.field;
      const value = document.getElementById(field).value.trim();
      // update local cache
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
        // show popup
        const pop = document.getElementById(field + '_popup');
        pop.innerText     = suggestion;
        pop.style.display = 'block';
      } catch (e) {
        alert('Error: ' + e.message);
      }
    });
  });

  // Provisional diagnosis button 🩺
  document.getElementById('gen_perspectives_dx')?.addEventListener('click', async () => {
    // gather all perspective values
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
  // ——— AI on Initial Plan screen ———
  if (document.getElementById('initial-plan-form')) {
    // load up prior stages
    const prevAdd   = JSON.parse(localStorage.getItem('add_patient_data')    || '{}');
    const prevSubj  = JSON.parse(localStorage.getItem('subjective_inputs')   || '{}');
    const prevPersp = JSON.parse(localStorage.getItem('perspectives_inputs')|| '{}');

    // **Here’s the key** for Initial Plan data:
    let prevAssess = JSON.parse(localStorage.getItem('initial_plan_assessments') || '{}');

    // Build the “previous” object we send to every AI call
    const allPrev = {
      age_sex:         prevAdd.age_sex        || '',
      present_history: prevAdd.present_history|| '',
      past_history:    prevAdd.past_history   || '',
      subjective:      prevSubj,
      perspectives:    prevPersp,
      assessments:     prevAssess
    };

    // Per-field test suggestions
    document.querySelectorAll('.ai-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const field     = btn.dataset.field;                   // e.g. 'active_movements'
        const selection = document.getElementById(field).value.trim();
        // **Save** the choice into our local cache
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

    // Full summary + provisional dx
    document.getElementById('gen_initial_summary')?.addEventListener('click', async () => {
      // ensure details from each field are also saved
      ['active_movements','passive_movements','passive_over_pressure',
       'resisted_movements','combined_movements','special_tests','neurodynamic']
        .forEach(f => {
          const details = (document.getElementById(f + '_details')?.value||'').trim();
          prevAssess[f] = { 
            choice:  prevAssess[f]?.choice || '',
            details
          };
        });
      // persist again
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
// ——— AI on Pathophysiological Mechanism screen ———
if (document.querySelector('select#possible_source')) {
  // load up all prior data
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
    assessments     // your key under which you stored the initial plan choices
  };

  document.querySelectorAll('.ai-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const field     = btn.dataset.field;               // "possible_source"
      const selection = document.getElementById(field).value.trim();
      try {
        const res = await fetch('/ai_suggestion/patho/possible_source', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ previous: allPrev, selection })
        });
        const { suggestion, error } = await res.json();
        if (error) throw new Error(error);
        // show popup
        const pop = document.getElementById(field + '_popup');
        pop.innerText     = suggestion;
        pop.style.display = 'block';
      } catch (e) {
        alert('Error: ' + e.message);
      }
    });
  });
}
// ——— AI on Chronic Disease Factors screen ———
if (document.getElementById('specific_factors')) {
  // load all prior data
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

  // Chronic factors follow-ups
  document.querySelector('.ai-btn').addEventListener('click', async e => {
    const btn    = e.currentTarget;
    const field  = btn.dataset.field;               // "specific_factors"
    const text   = document.getElementById(field).value.trim();
    // gather checked causes
    const causes = Array.from(document.querySelectorAll('input[name="maintenance_causes"]:checked'))
                        .map(cb => cb.value);

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
      // show popup
      const pop = document.getElementById(field + '_popup');
      pop.innerText     = suggestion;
      pop.style.display = 'block';
    } catch (err) {
      alert('Error: ' + err.message);
    }
  });
}
// ——— AI on Clinical Flags screen ———
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

  // On page load: highlight relevant flags
  const highlights = [];
  if (allPrev.subjective.pain_irritability === 'Present') {
    highlights.push('yellow_flags');
  }
  if (allPrev.assessments.special_tests?.choice === 'Absolutely Contraindicated') {
    highlights.push('black_flags');
  }
  highlights.forEach(id => {
    document.getElementById(id + '_block').classList.add('highlight');
  });

  // Wire up AI buttons
  document.querySelectorAll('.ai-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const field = btn.dataset.field;
      const text  = document.getElementById(field).value.trim();
      try {
        const res = await fetch(
          `/ai_suggestion/clinical_flags/{{ patient_id }}/suggest`,
          {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ previous: allPrev, field, text })
          }
        );
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
// ——— AI on Objective Assessment screen ———
if (document.getElementById('objective-assessment-form')) {
  // load prior stages
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

  // per-field AI helpers
  document.querySelectorAll('#objective-assessment-form .ai-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const field = btn.dataset.field;          // "plan"
      // show loading
      const popup = document.getElementById(field + '_popup');
      popup.textContent = 'Thinking…';
      popup.style.display = 'block';

      try {
        // update local prevAssess so later provisional DX has this choice
        allPrev.assessments[field] = { 
          choice: document.getElementById(field).value 
        };
        localStorage.setItem('initial_plan_assessments', 
                             JSON.stringify(allPrev.assessments));

        const res = await fetch(
          `/ai_suggestion/objective_assessment/${field}`,
          {
            method: 'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ previous: allPrev, value: allPrev.assessments[field].choice })
          }
        );
        const { suggestion, error } = await res.json();
        if (error) throw new Error(error);
        popup.textContent = suggestion.trim();
      } catch (err) {
        popup.textContent = 'Error: ' + err.message;
        console.error(err);
      }
    });
  });

  // global click hides popups
  document.addEventListener('click', e => {
    if (!e.target.closest('.field-block')) {
      document.querySelectorAll('.ai-popup').forEach(p=>p.style.display='none');
    }
  });

  // provisional DX button
  document.getElementById('gen_provisional_dx').addEventListener('click', async () => {
    try {
      // also grab details text
      allPrev.assessments.plan.details = 
        document.getElementById('plan_details').value.trim();
      localStorage.setItem('initial_plan_assessments',
                           JSON.stringify(allPrev.assessments));

      const res = await fetch(
        `/ai_suggestion/provisional_diagnosis`,
        {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ previous: allPrev })
        }
      );
      const { diagnosis, error } = await res.json();
      if (error) throw new Error(error);
      alert("Provisional Diagnosis:\n\n" + diagnosis.trim());
    } catch (err) {
      alert("Error: " + err.message);
      console.error(err);
    }
  });
}
// ——— Provisional Diagnosis AI Suggestions ———
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.ai-btn[data-field]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const field = btn.dataset.field;
      const popup = document.getElementById(field + '_popup');
      // show loading state
      popup.textContent = '🤔 Thinking…';
      popup.style.display = 'block';

      try {
        const res = await fetch(
          `/provisional_diagnosis_suggest/${window.patientId}?field=${encodeURIComponent(field)}`
        );
        const { suggestion } = await res.json();
        popup.textContent = suggestion || 'No suggestion available.';
      } catch (err) {
        console.error(err);
        popup.textContent = '⚠️ Error fetching suggestion.';
      }
    });
  });

  // hide any open popup on outside click
  document.body.addEventListener('click', e => {
    if (!e.target.matches('.ai-btn')) {
      document.querySelectorAll('.ai-popup')
              .forEach(p => p.style.display = 'none');
    }
  });
});

// SMART Goals suggestions
document.querySelectorAll('.ai-btn[data-screen="smart_goals"]').forEach(btn => {
  btn.addEventListener('click', async () => {
    const field = btn.dataset.field;                   // e.g. "patient_goal"
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
          previous_assessments: JSON.parse(localStorage.getItem('initial_plan_inputs')  || '{}'),
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
// ----------------------------------------------------------------
// Treatment Plan screen:
// ----------------------------------------------------------------
document.querySelectorAll('.ai-btn').forEach(btn => {
  // each button on treatment_plan.html has data-field="treatment_plan", "goal_targeted", etc.
  btn.addEventListener('click', async () => {
    const field = btn.dataset.field;
    const popup = document.getElementById(field + '_popup');
    popup.textContent = 'Loading…';
    popup.style.display = 'block';

    try {
      const resp = await fetch(
        `/ai_suggestion/treatment_plan/${field}`,
        {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({
            patient_id: window.patientId,
            input: document.getElementById(field).value
          })
        }
      );
      const data = await resp.json();
      popup.textContent = data.suggestion || data.error || 'No suggestion';
    } catch (err) {
      popup.textContent = 'Error fetching suggestion';
      console.error(err);
    }
  });
});

// Hide popups when you click anywhere else:
document.addEventListener('click', e => {
  if (!e.target.closest('.control-group')) {
    document.querySelectorAll('.ai-popup').forEach(p => p.style.display = 'none');
  }
});

// Generate full treatment summary:
const genBtn = document.getElementById('gen_summary');
if (genBtn) {
  genBtn.addEventListener('click', async () => {
    try {
      const resp = await fetch(
        `/ai_suggestion/treatment_plan_summary/${window.patientId}`
      );
      const data = await resp.json();
      alert("Treatment Summary:\n\n" + (data.summary || data.error));
    } catch (err) {
      console.error(err);
      alert('Error generating summary');
    }
  });
}
document.querySelectorAll('.ai-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const textarea = btn.previousElementSibling;
    const field    = textarea.id;
    const popup    = document.getElementById(field + '_popup');
    popup.textContent = 'Thinking…';
    popup.style.display = 'block';

    try {
      const resp = await fetch(`/ai/followup_suggestion/${window.patientId}`, {
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
});

// hide popups on outside click
document.addEventListener('click', e => {
  if (!e.target.closest('.control-group')) {
    document.querySelectorAll('.ai-popup').forEach(p => p.style.display = 'none');
  }
});
