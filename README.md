# Vireo Audio Support Intelligence

A small, local support-analytics tool for Vireo Audio. It turns the supplied 18-month helpdesk export into validated weekly metrics, reviewed repeat-contact findings, a configurable AI-classification layer, and a decision-focused dashboard for the Head of Customer Experience.

The proposed 13-week pilot targets Vireo's strongest actionable opportunity: reduce the verified missing-delivery/tracking repeat-contact rate from **14.34% to 10.76%** (a 25% relative reduction). At the current volume and historical channel mix, reaching that target would represent approximately **37 fewer repeat contacts** and **₹9,350 of support capacity released per quarter**. This is a pilot target and capacity value, not a forecast or guaranteed cash saving.

## Key findings

- After deduplication, the export contains **11,875 distinct tickets**.
- **3,304** contacts were candidates for a return within 30 days; **1,039** were classified as high-confidence same-issue repeats. Those contacts represent **₹263,740** of historical support capacity.
- The mature operational cohort contains **10,485** completed tickets with a full 30-day observation window. **1,008** had a confirmed same-issue return, giving an overall repeat-contact baseline of **9.61%**.
- Missing-delivery/tracking is the largest actionable repeat issue: **186 / 1,297 = 14.34%** among mature tickets.
- In the fixed validation sample, **67/67 reviewed high-confidence cases agreed**. Ambiguous cases were excluded from the headline estimate. This supports precision; it does not establish recall.

## What was built

```text
Five source CSVs
    ↓
Deterministic validation, cleaning and weekly metrics
    ↓
AI-assisted ticket and same-issue pair classification
    ↓
Cached classifications + reviewed investigation outputs
    ↓
Static local dashboard (no API or network calls)
```

### Deterministic pipeline

`vireo_support/pipeline.py` validates all five schemas, deduplicates ticket IDs, normalizes timestamps to IST, links orders conservatively, applies the mature 30-day observation rule, joins the resolving-agent roster assignment, and calculates weekly ticket and agent metrics. Data-quality discrepancies remain visible in `outputs/pipeline/data_quality_report.json`.

### AI-assisted analysis

`vireo_support/ai_analysis/` classifies opening messages into a controlled complaint taxonomy and evaluates candidate ticket pairs for the same underlying issue. Responses use validated structured JSON, permit uncertainty, enforce deterministic customer/product/order gates, apply a documented confidence threshold, redact common identifiers, and cache results to prevent duplicate requests. Human-label templates support evaluation without treating model agreement as ground truth.

The saved `offline-rules-v1` run is retained as a rejected development baseline: it reproduced only **50.53%** of the reviewed positive set and is not used for the headline business rates. An OpenAI-compatible provider is included for bounded external-model evaluation, but no successful Gemini result is used in this submission's findings.

### Dashboard

The dashboard is a static site under `dashboard/` and reads only saved local data. It includes:

- a selectable Weekly Digest with week-specific KPIs, the complete ranked issue breakdown, an eight-week complaint trend, and concise week-over-week observations;
- a weekly agent leaderboard covering all support teams, explicitly presented as ticket volume rather than agent quality; and
- Support Opportunities showing the 14.34% delivery baseline, 10.76% pilot target, expected capacity impact, top repeat issues, recommended intervention, and concise validation limits.

## Dashboard View

<img width="949" height="504" alt="image" src="https://github.com/user-attachments/assets/fc906cb2-fd6f-4132-ba2e-f13236d6adc0" />

## Analytical decisions and limits

- Duplicate ticket IDs prefer the helpdesk record over the migrated legacy record. Conflicts remain in the quality report.
- Legacy resolution timestamps receive the established **+5 hours 30 minutes** UTC-to-IST correction, supported by all 618 comparable duplicate pairs.
- A ticket enters the repeat-rate denominator only when it is completed and `resolution time + 30 days` falls within the export's observation boundary.
- Order matching never chooses arbitrarily between multiple possible orders. High-confidence repeats require the same complaint plus explicit or uniquely inferable same-order evidence.
- Support-capacity values use the policy rates: chat ₹210, email ₹260, voice ₹520, and social ₹240.
- The repeat rates are conservative lower bounds. Vague messages, issue progression, ambiguous order links, changed customer identities, and June tickets without a complete observation window can hide real repeats.
- The validation sample was designed to check precision, not recall. The pilot target is managerial and must be tested prospectively.

Full calculation trails are preserved in:

- `outputs/repeat-contact-investigation.md`
- `outputs/baseline-and-pilot.md`
- `outputs/classifier-evaluation.md`

## Clean-machine setup

Requirements: **Python 3.11 or newer**. The project has no third-party runtime dependencies. PowerShell commands below assume the five supplied CSVs have been copied into an ignored `data/` directory using their standard filenames.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Run the deterministic pipeline:

```powershell
python -m vireo_support `
  --tickets "data\tickets.csv" `
  --agents "data\agents.csv" `
  --customers "data\customers.csv" `
  --orders "data\orders.csv" `
  --products "data\products.csv" `
  --output-dir "outputs\pipeline"
```

Run the test suite:

```powershell
python -m unittest discover -s tests -v
```

Build and serve the dashboard from the saved outputs:

```powershell
python dashboard\build_data.py
python -m http.server 8000 --directory dashboard
```

Open [http://localhost:8000](http://localhost:8000). The included `dashboard/data.js` also allows the dashboard to be served immediately; rebuilding it refreshes the bundle from the saved outputs.

Run a bounded offline classifier sample without a key or paid call:

```powershell
$env:VIREO_AI_PROVIDER="offline"
$env:VIREO_AI_MODEL="offline-rules-v1"
python -m vireo_support.ai_analysis `
  --clean-tickets "outputs\pipeline\clean_tickets.csv" `
  --output-dir "outputs\ai-sample" `
  --ticket-limit 12 `
  --pair-limit 8
```

## operating cost

The delivered dashboard makes no live LLM calls, requires no API key, and works without a network connection. All dashboard results are generated from saved analysis artifacts. No external model calls are required to reproduce or run the dashboard.

## AI/Development

During development, an external Gemini-compatible provider was prepared for bounded evaluation, but no external model call was successfully made. No API cost was incurred.
