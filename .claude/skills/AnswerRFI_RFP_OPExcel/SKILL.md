---
name: AnswerRFI_RFP_OPExcel
description: Reads RFP/RFI Excel questionnaires and answers questions with IBM OpenPages solution details. Supports multi-sheet workbooks with varying column layouts.
argument-hint: [path-to-excel-file]
allowed-tools: Read, Bash, Write, Glob, Grep, Edit, WebFetch
---

# AnswerRFI_RFP_OPExcel Skill

Reads an RFP/RFI Excel questionnaire, analyses the questions, and writes professional IBM OpenPages answers into the vendor response column. Supports workbooks with multiple sheets and varying column layouts (question/response columns auto-detected).

## Workflow

### Step 1: Check Dependencies

Verify that `openpyxl` is installed:

```bash
pip3 list 2>/dev/null | grep -i openpyxl || pip3 install -r .claude/skills/AnswerRFI_RFP_OPExcel/scripts/requirements.txt
```

### Step 2: Parse Excel — Sheet Listing

The Excel file path comes from `$ARGUMENTS`. If no path is provided, ask the user for it.

Run the parser in `--parse-only` mode (without `--sheets`) to get the sheet listing:

```bash
python3 .claude/skills/AnswerRFI_RFP_OPExcel/scripts/parse_excel_rfp.py \
  --input "$ARGUMENTS" \
  --parse-only
```

This outputs JSON with all sheet names, question counts, detected column structures, and whether each sheet is answerable.

### Step 3: Present Sheets and Get User Selection

Display the available sheets to the user in a markdown table:

```
## Available Sheets in [filename]

| Sheet | Questions | Answerable | Structure |
|-------|-----------|------------|-----------|
| A. Company Profile | 26 | Yes | Q=Col C, Resp=Col D |
| D. Functional Requirements | 248 | Yes | Q=Col B, Score=Col C, Resp=Col D |
| ... | ... | ... | ... |

Which sheets would you like me to answer? (e.g., "all", "D,E", or "D. Functional Requirements, E. Non-Functional Requirements")
```

Wait for the user to specify which sheets to answer.

### Step 4: Extract Questions from Selected Sheets

Run the parser again with `--sheets` to extract full questions:

```bash
python3 .claude/skills/AnswerRFI_RFP_OPExcel/scripts/parse_excel_rfp.py \
  --input "$ARGUMENTS" \
  --parse-only \
  --sheets "Sheet1,Sheet2"
```

Read the JSON output containing all questions with their IDs, categories, question types, and current responses.

### Step 5: Process Questions in Batches

For each selected sheet, process questions in batches of **20-25 questions**. For each batch:

1. Read the batch of questions from the parsed JSON
2. Generate IBM OpenPages answers following the **Answer Generation Rules** below
3. For technical questions where you need specific feature details, use `WebFetch` to check:
   - Admin Guide: `https://www.ibm.com/docs/en/openpages/9.0.0?topic=administrators-guide`
   - User Guide: `https://www.ibm.com/docs/en/openpages/9.0.0?topic=user-guide`
4. Append answers to the accumulated answers list

**Batching process:**
- Group questions by category within each sheet
- Process one category at a time if the category has <= 25 questions
- If a category has > 25 questions, split into sub-batches of 20
- After each batch, report progress to the user (e.g., "Answered 45/248 questions in D. Functional Requirements")

### Step 6: Assemble Answers JSON

After processing all batches for all sheets, assemble the complete answers into a JSON file:

```json
{
  "file": "original_filename.xlsx",
  "answers": {
    "D. Functional Requirements": [
      {
        "row": 7,
        "response_col_letter": "D",
        "answer": "Yes. IBM OpenPages provides comprehensive...",
        "score": "Y",
        "score_col_letter": "C"
      }
    ]
  }
}
```

Write this to `./output/<filename>_answers.json`.

### Step 7: Write Answers to Excel

Run the write-back command:

```bash
python3 .claude/skills/AnswerRFI_RFP_OPExcel/scripts/parse_excel_rfp.py \
  --input "$ARGUMENTS" \
  --write-answers ./output/<filename>_answers.json
```

This creates a new file `<filename>_answered.xlsx` preserving all original formatting. The original file is NOT modified.

### Step 8: Report Results

Report to the user:
- Total questions answered per sheet
- Number of questions flagged for manual input (company info, references)
- Output file path
- Offer to review specific answers or make modifications

---

## Answer Generation Rules

When generating answers, follow these rules precisely:

### For Binary Questions (question_type = "binary")

These are questions like "The system supports...", "Does your system...?", "Can the solution...?"

- **First word**: Start with **"Yes."**, **"No."**, or **"Partially."** on the first line
- **Elaboration**: Follow with 1-3 sentences explaining HOW IBM OpenPages supports this capability
- **Score**: Set the `score` field to `"Y"` (Yes), `"N"` (No), or `"N/A"` (Not Applicable)
- If partially supported: say "Partially." and explain what is supported and what requires configuration or customisation
- If supported via configuration/extension: say "Yes." and note it requires configuration

Example:
> Yes. IBM OpenPages provides comprehensive role-based access control (RBAC) through its Security Model, allowing administrators to define granular permissions at the object type, field, and record level. Access can be managed through security domains, user groups, and application permissions.

### For Narrative Questions (question_type = "narrative")

These are questions starting with "Describe...", "Explain...", "Provide details...", "How does...?"

- Provide **2-5 sentences** of professional, positive response
- Reference specific IBM OpenPages features, modules, and capabilities
- Use concrete terms: module names, feature names, technology components
- Be thorough but concise

### For Company Info Questions (question_type = "company_info")

- Output: `"[REQUIRES MANUAL INPUT: Company-specific information needed — e.g., company name, address, financials, employee count]"`
- Do NOT fabricate company details

### For Reference Questions (question_type = "reference")

- Output: `"[REQUIRES MANUAL INPUT: Client reference details needed — provide client name, contact, project scope, outcomes]"`
- Do NOT fabricate reference details

### General Rules

- **Tone**: ALWAYS be professional, confident, and positive
- **Product name**: Use "IBM OpenPages" on first mention per answer, then "OpenPages" subsequently
- **Never fabricate**: If unsure about a capability, say "IBM OpenPages can be configured to support..." or check the IBM docs via WebFetch
- **Modules**: Reference relevant modules by their full names:
  - Operational Risk Management (ORM)
  - IT Governance (ITG)
  - Regulatory Compliance Management (RCM)
  - Model Risk Governance (MRG)
  - Third Party Risk Management (TPRM)
  - Policy Management
  - Financial Controls Management (FCM)
  - Internal Audit Management (IAM)
  - Data Privacy Management (DPM)
  - Business Continuity Management (BCM)
  - ESG (Environmental, Social and Governance)
- **Technical features** to reference when relevant:
  - REST APIs and integration capabilities
  - FastMap for bulk import/export
  - IBM Cognos Analytics integration for reporting (200+ out-of-box reports)
  - Visual workflow designer with automated triggers and rules
  - Role-based access control with field-level security
  - Configurable object types, field groups, profiles, and views
  - SAML 2.0 SSO, LDAP/AD integration
  - Encryption at rest and in transit
  - SOC 2 Type II certified, ISO 27001 compliant
  - IBM Cloud Pak for Data compatible
  - Watson AI for risk insights

---

## IBM OpenPages Quick Reference

Use this reference for consistent, accurate answers:

**Platform**: Cloud-native SaaS or on-premise, IBM Cloud Pak for Data compatible
**Architecture**: Multi-tenant SaaS, SOC 2 Type II certified, ISO 27001, SOC 1 Type II
**UI**: Task-focused "Zero Training UI", Classic UI, Administrative UI
**Reporting**: IBM Cognos Analytics integration, 200+ out-of-box reports, custom report builder
**AI/ML**: Watson AI for risk insights, 50+ language translation, natural language search
**Integration**: REST APIs, FastMap bulk import/export, SOX Express, pre-built connectors
**Workflow**: Visual drag-and-drop workflow designer, automated triggers, rules engine, notifications
**Security**: RBAC, SAML 2.0 SSO, LDAP/AD, field-level security, encryption at rest and in transit, MFA
**Data Model**: Configurable object types, field groups, profiles, views, computed fields
**Audit Trail**: Complete history tracking, change logs, electronic signatures, version control
**Calculations**: Automated risk scoring, KRI thresholds, loss event aggregation, heat maps
**Import/Export**: FastMap (Excel-based bulk ops), REST API, scheduled data feeds, CSV
**Localisation**: 50+ languages, multi-currency, jurisdiction-specific configurations
**Mobile**: Responsive web UI accessible from any device
**Scalability**: Enterprise-grade, handles 100,000+ objects, concurrent user support

## Notes

- Excel parsing uses `openpyxl` — runs locally, no API needed
- Question analysis and answer generation is performed by Claude directly within the skill conversation
- The original Excel file is NEVER modified — answers are written to a new `_answered.xlsx` file
- Company-specific and reference questions are flagged for manual input
- Formula cells in score columns are preserved (never overwritten)
- WebFetch for IBM docs is pre-approved in settings
