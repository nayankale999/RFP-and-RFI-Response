---
name: CreateRFIResponse
description: Creates a professional RFI response PDF document with corporate branding, section heading bars, tables, footers, and table of contents. Use when the user wants to generate an RFI or RFP response document.
argument-hint: [client-name] [solution-name]
allowed-tools: Read, Bash, Write, Glob, Grep, Edit
---

# CreateRFIResponse Skill

Generate a professional RFI (Request for Information) response PDF document with corporate branding and formatting. The output PDF follows a standard corporate RFI response structure with a branded cover page, contact information, table of contents, executive summary, company profile, solution profile, technical information, appendices, and copyright notice.

## Workflow

### Step 1: Check Dependencies

Verify that `reportlab` and `Pillow` are installed. If not, install them:

```bash
pip3 list 2>/dev/null | grep -i reportlab || pip3 install -r .claude/skills/CreateRFIResponse/scripts/requirements.txt
```

### Step 2: Collect Information

Parse the arguments provided: `$ARGUMENTS` should contain the client name and solution name.

If arguments are missing or incomplete, interactively collect the following information from the user. For each section, offer to generate placeholder content if the user wants to skip it.

#### Required Information:

1. **Basic Details**
   - Client name (who the RFI response is for)
   - Solution name (what product/service is being proposed)
   - RFI description (e.g., "RFI for Risk Management Solution")
   - Prepared for (organization name)
   - Date prepared

2. **Company Information**
   - Company name
   - Address (line 1, line 2)
   - Contact person name and title
   - Phone number
   - Email address
   - Website URL

3. **Cover Page** (optional customization)
   - Background color (default: #1B3A5C dark navy)
   - Or path to a background image file

4. **Revision History**
   - Version, date, author(s), approver(s), description

5. **Executive Summary**
   - 2-4 paragraphs describing the context and proposed solution
   - Bullet points highlighting key capabilities

6. **Company Profile & Credentials**
   - Company description paragraph
   - Awards/credentials list
   - Analyst recognition/certifications list
   - Key experience highlights

7. **Solution Profile**
   - Solution overview paragraph
   - Features list (each with name and description)

8. **Technical Information**
   - Technical content/description
   - List of attached document references

9. **Appendices**
   - List of appendix documents (label, filename, description)

10. **Copyright**
    - Year (default: current year)
    - Company name
    - Copyright notice text (optional, defaults to standard notice)

### Step 3: Assemble JSON Data

Assemble all collected information into a JSON file following this structure. Refer to the example at `.claude/skills/CreateRFIResponse/examples/sample_input.json` for the complete data format.

Write the JSON data file to: `./output/<client_name_slug>_rfi_data.json`

### Step 4: Generate PDF

Run the PDF generation script:

```bash
python3 .claude/skills/CreateRFIResponse/scripts/generate_pdf.py \
  --input ./output/<client_name_slug>_rfi_data.json \
  --output "./output/<Client_Name>_<Solution_Name>_RFI_Response.pdf" \
  --verbose
```

### Step 5: Report Results

After generation, report to the user:
- The output PDF file path
- Total page count
- Any font substitutions that were made (the script will report these)
- Offer to open the file or make modifications

## Document Format Reference

The generated PDF follows this corporate format:
- **Page size:** A4 Portrait
- **Cover page:** Dark solid background (#1B3A5C) with white centered title text (Calibri-Light 36pt/20pt)
- **Section headings:** Dark blue bars (#314662) with white text (Calibri-Light 18pt)
- **Body text:** Times New Roman 12pt, black, justified
- **Tables:** Gray header rows (#D9D9D9), thin grid borders
- **Bullet points:** Dash-style (-) for features, round bullets for credentials
- **Footer:** "(c) Company Year Solution for Client Page X of Y" in Calibri-Light 10pt, navy (#1f3863)
- **Table of Contents:** Dot leaders with page numbers

## Notes

- The script runs on the local system Python, not inside Docker
- Fonts are discovered automatically across macOS, Linux, and Windows
- If Calibri-Light is not available, Arial or Helvetica will be used as fallback
- If Times New Roman is not available, Georgia or Times-Roman (builtin) will be used
- All font substitutions are reported in the output
