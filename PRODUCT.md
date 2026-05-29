# PhysiologicPRISM

AI-powered clinical reasoning platform for physiotherapy professionals.

## What it is

PhysiologicPRISM is a web application that helps physiotherapists structure their clinical reasoning, capture biopsychosocial factors, and generate defensible documentation using the proprietary PRISM Clinical Reasoning Framework. The platform combines evidence-based assessment workflows with AI-assisted documentation to improve patient care quality and efficiency.

## Who uses it

- **Individual physiotherapists** conducting patient assessments and treatment planning
- **Clinical institutes** managing multiple physiotherapists and patient caseloads
- **University programs** teaching clinical reasoning to physiotherapy students

## Register

product

The platform serves clinical workflows (app UI, dashboards, assessment forms, patient management). Design should enhance usability and reduce cognitive load during high-stakes clinical decision-making, not draw attention to itself.

## Core surfaces

1. **Public marketing pages** (homepage, pricing, for-clinics, for-universities, blog)
   - Landing pages to convert visitors to trial signups
   - Educational content about the PRISM Framework

2. **Authentication & onboarding** (login, register, 2FA, trial signup)
   - Individual and institute-based user flows
   - 14-day free trial (5 patients, 25 AI assists, all features)

3. **Patient management** (patient list, add patient, patient dashboard)
   - Core clinical workflow: managing caseload
   - Quick access to patient history and assessments

4. **PRISM Assessment workflow** (multi-step guided assessment)
   - Subjective examination
   - Pathophysiological mechanisms
   - Chronic disease factors
   - Clinical flags
   - Objective assessment
   - Functioning assessment
   - Patient perspectives
   - Initial plan of assessment
   - Provisional diagnosis
   - SMART goals
   - Treatment plan
   - Follow-up tracking

5. **AI-assisted documentation** (Quick Mode, AI responses, speech-to-text)
   - AI generates clinical documentation based on prompts
   - Voice input for hands-free documentation
   - Hallucination prevention & evidence-based guardrails

6. **Subscription & billing** (pricing page, subscription manager, Razorpay integration)
   - Tiered plans: Starter ($9), Professional ($29), Institute (custom)
   - Trial → paid conversion flows

## Tech stack

- **Backend:** Python/Flask, Azure Cosmos DB (migrating from SQLite)
- **Frontend:** Jinja2 templates, vanilla CSS (no framework), vanilla JS
- **Auth:** Firebase Authentication with custom JWT
- **AI:** Azure OpenAI (GPT-4, GPT-3.5 Turbo), Claude (Anthropic)
- **Payments:** Razorpay (INR & USD)
- **Infrastructure:** Azure Container Apps, Azure App Service
- **Analytics:** Google Analytics 4, PostHog

## Current state

- **99 HTML templates** with inline styles and separate CSS files
- **8 CSS files** in `/static/`: style.css (main), assessmentProgress.css, logout.css, print.css, keyboardShortcuts.css, textExpansion.css, autocomplete.css, progressBar.css
- **Brand colors:** Primary teal (`#1a5f5a`), gradients for CTAs, neutral grays
- **Design system:** CSS custom properties in `:root`, but implementation is inconsistent
- **Recent work:** Mobile responsiveness improvements, public page cleanup, blog feature expansion

## Known design debt

- Inline styles scattered across templates (hard to maintain)
- Gradient text on CTA buttons (line 60 of index.html: `background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)` applied to button, not brand colors)
- Inconsistent spacing and typography hierarchy across pages
- No documented design system (tokens exist but not formalized)
- Accessibility gaps (contrast, focus states, ARIA labels not audited)
- Mobile-first responsive design added reactively, not built-in

## Goals for design work

1. **Audit & document** the existing visual system (colors, typography, spacing, components)
2. **Extract reusable components** from the 99 templates to reduce duplication
3. **Improve conversion** on public marketing pages (homepage, pricing, trial signup)
4. **Enhance clinical UX** in the PRISM assessment workflow (reduce steps, improve clarity)
5. **Accessibility audit** (WCAG 2.1 AA compliance for healthcare software)
6. **Motion & delight** where appropriate (assessment progress, success states, AI feedback)

## Brand voice

Professional, evidence-based, empowering. The PRISM Framework is proprietary and clinically validated. We help physiotherapists think better, not replace their judgment. Tone is confident but not prescriptive, educational but not patronizing.

## Constraints

- **No CSS framework:** Must work with vanilla CSS (tailwind/bootstrap/etc. not in use)
- **No JS framework:** Vanilla JavaScript only (no React/Vue/Svelte)
- **Backend-rendered:** Jinja2 templates, not SPA
- **Performance:** Target <2s page load on 3G (healthcare settings have poor connectivity)
- **Compliance:** GDPR, HIPAA-ready (data privacy is critical)

---

*Generated: 2026-05-29 for Impeccable design skill initialization*
