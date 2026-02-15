---
name: GetSchedule
description: Extracts the procurement schedule (key dates, deadlines, milestones) from RFP/RFI documents (PDF or DOCX). Identifies submission deadlines, demo dates, PoC periods, selection dates, and other timeline events.
argument-hint: [path-to-document]
allowed-tools: Read, Bash, Write, Glob, Grep
---

# GetSchedule Skill

Extract the procurement schedule from an RFP (Request for Proposal) or RFI (Request for Information) document. The skill parses the document, identifies schedule-related content (tables, lists, or narrative), and extracts structured timeline events including submission deadlines, demo dates, PoC periods, selection dates, and more.

Supports: **PDF** and **DOCX** files.

## Workflow

### Step 1: Check Dependencies

Verify that `pdfplumber` and `python-docx` are installed:

```bash
pip3 list 2>/dev/null | grep -i pdfplumber && pip3 list 2>/dev/null | grep -i python-docx || pip3 install -r .claude/skills/GetSchedule/scripts/requirements.txt
```

### Step 2: Parse the Document

The document path comes from `$ARGUMENTS`. If no path is provided, ask the user for it.

Run the parser script in `--parse-only` mode to extract text and tables from the document:

```bash
python3 .claude/skills/GetSchedule/scripts/extract_schedule.py \
  --input "$ARGUMENTS" \
  --parse-only
```

This outputs JSON to stdout with `document_text`, `tables_text`, `filename`, and `page_count`.

### Step 3: Analyse the Parsed Content

Read the JSON output from Step 2. Using the extracted text and tables, identify and extract ALL schedule-related events. Look for:

1. **RFP/RFI issuance or release date**
2. **Deadline to confirm intention to respond**
3. **Questions/clarifications submission deadline**
4. **Proposal/response submission deadline**
5. **Evaluation period or dates**
6. **Shortlist or initial selection notification**
7. **Vendor demos, presentations, or site visits**
8. **Proof of Concept (PoC) start and end dates**
9. **Final selection/award decision date**
10. **Contracting/negotiation period**
11. **Implementation or project start date**
12. **Any other milestone dates**

The schedule may appear in a **table**, a **bullet list**, or **narrative paragraphs**. Check ALL of these sources.

For each event, determine:
- **Event name**: As stated in the document
- **Event type**: One of: rfp_release, intention_to_respond, clarification_deadline, submission_deadline, evaluation, shortlist_notification, demo_presentation, poc_start, poc_end, selection_decision, contracting, implementation_start, other
- **Date**: In YYYY-MM-DD format for exact dates, or descriptive (e.g., "Week 49") for approximate dates
- **Date type**: exact, approximate, week_number, relative, or tbd
- **Is deadline**: Whether this is a deadline (must be done BY this date) vs a start date
- **Notes**: Any additional context

### Step 4: Display Results

Present the extracted schedule to the user as a **markdown table**:

```
## Procurement Schedule: [Document Name]

**Source:** [Section where schedule was found]

| # | Event | Date | Deadline? | Notes |
|---|-------|------|-----------|-------|
| 1 | ... | ... | ... | ... |

**Note:** [Any caveats about the schedule, e.g., "indicative", "subject to change"]
```

### Step 5: Generate Win Plan Document

After displaying the schedule, automatically generate an **RFP Win Plan** Word document:

1. Assemble a JSON data file with the extracted schedule events plus RFP metadata. The JSON must include:
   - `client_name`: The client/organisation name (extracted from the document or asked from the user)
   - `rfp_title`: The title of the RFP/RFI
   - `document`: Source filename
   - `page_count`: Number of pages
   - `source_section`: Where the schedule was found
   - `additional_notes`: Any caveats about the schedule
   - `events`: Array of schedule event objects (same structure as displayed in Step 4, with fields: event_type, event_name, date, date_type, is_deadline, notes)

2. Write the JSON to `./output/<document_name>_schedule_data.json`

3. Run the Win Plan generator:

```bash
python3 .claude/skills/GetSchedule/scripts/generate_win_plan.py \
  --input ./output/<document_name>_schedule_data.json \
  --output "./output/<Client_Name>_Win_Plan.docx"
```

4. Report the output file path and offer to open it.

The Win Plan DOCX contains these sections:
- **Cover Page**: RFP Win Plan title, client name, RFP title, date
- **RFP Overview**: Client, document, page count, schedule source
- **Procurement Schedule**: Full schedule table with all events (deadlines highlighted in yellow)
- **Key Deadlines Summary**: Filtered view with priority levels (CRITICAL/HIGH/MEDIUM) and colour coding
- **Response Team**: Placeholder table with common roles (Bid Manager, Solution Architect, SME, etc.)
- **Win Strategy**: Prompts for differentiators, competitive advantages, pain points, risks, win themes
- **Action Items**: Pre-filled action tracker (confirm intent, prepare demo, draft response, pricing, submit)
- **Notes**: Empty section for additional notes

### Step 6: Offer Additional Exports

After generating the Win Plan, also offer to save the raw schedule data:
- **JSON file**: `./output/<document_name>_schedule.json`
- **CSV file**: `./output/<document_name>_schedule.csv`

## Example Output

See `.claude/skills/GetSchedule/examples/sample_output.json` for a complete schedule extraction example.

## Notes

- Document parsing uses `pdfplumber` (PDF) and `python-docx` (DOCX) — runs locally, no API needed
- Schedule analysis is performed by Claude directly within the skill conversation
- Win Plan generation uses `python-docx` — no API needed
- For very large documents (>15,000 chars), the text is truncated but all tables are always included
- The script also supports a full standalone mode with `--format json|csv|markdown` when `ANTHROPIC_API_KEY` is set
