"""
Generation Pipeline Orchestrator

Downloads project documents from S3, runs skill scripts
(extract_schedule, generate_win_plan, parse_excel_rfp, generate_pdf),
generates AI answers for Excel RFPs, and uploads outputs back to S3.
"""

import json
import logging
import re
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.document import Document
from app.models.project import Project
from app.shared.ai_client import get_ai_client
from app.shared.storage import get_storage_client

logger = logging.getLogger(__name__)

# Skill script paths
SKILLS_DIR = Path(__file__).parent.parent.parent.parent / ".claude" / "skills"
EXTRACT_SCHEDULE_SCRIPT = SKILLS_DIR / "GetSchedule" / "scripts" / "extract_schedule.py"
GENERATE_WIN_PLAN_SCRIPT = SKILLS_DIR / "GetSchedule" / "scripts" / "generate_win_plan.py"
PARSE_EXCEL_SCRIPT = SKILLS_DIR / "AnswerRFI_RFP_OPExcel" / "scripts" / "parse_excel_rfp.py"
GENERATE_PDF_SCRIPT = SKILLS_DIR / "CreateRFIResponse" / "scripts" / "generate_pdf.py"

# IBM OpenPages system prompt for RFP answer generation
ANSWER_SYSTEM_PROMPT = """You are an expert RFP/RFI response writer for IBM OpenPages, a leading integrated GRC (Governance, Risk and Compliance) platform.

When answering RFP/RFI questions:
- For binary questions (Yes/No): Start with "Yes." followed by a brief elaboration (1-2 sentences) explaining how IBM OpenPages addresses this capability.
- For narrative questions: Provide 2-5 clear, professional sentences describing how IBM OpenPages meets the requirement.
- For company_info questions: Respond with "[REQUIRES MANUAL INPUT]" as these need specific company details.
- For reference questions: Provide standard IBM OpenPages reference information.

Key IBM OpenPages capabilities to reference:
- Unified GRC platform with modules for Operational Risk Management (ORM), Regulatory Compliance Management (RCM), IT Governance, Policy Management, Internal Audit, Financial Controls, Model Risk Governance, Third-Party Risk Management
- Built on IBM Cloud Pak for Data / watsonx platform
- AI-powered insights with Watson / watsonx.ai integration
- Highly configurable workflows, forms, and dashboards
- SOC 2 Type II, ISO 27001, FedRAMP certified
- REST APIs for integration, supports SSO/SAML, LDAP
- Role-based access control (RBAC)
- Available as SaaS, on-premises, or hybrid deployment
- Supports regulatory frameworks: Basel III/IV, SOX, GDPR, DORA, CCPA, etc.

Be confident, professional, and specific. Never be vague or generic."""

ANSWER_BATCH_SIZE = 20


class UploadContextParser:
    """Extracts structured info from free-text upload context."""

    @staticmethod
    def parse(context: str | None) -> dict:
        result = {
            "sheet_names": [],
            "client_name": None,
            "focus_files": [],
            "raw": context or "",
        }
        if not context:
            return result

        # Extract sheet/tab names
        sheet_patterns = [
            r"(?:sheet|tab|worksheet)\s*[:\-]?\s*[\"']?([^\"'\n,]+)[\"']?",
            r"[\"']([^\"']+)[\"']\s*(?:sheet|tab)",
            r"(?:focus on|answer)\s+(?:sheet|tab)?\s*[\"']?([^\"'\n,]+)[\"']?",
        ]
        for pattern in sheet_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            result["sheet_names"].extend([m.strip() for m in matches if m.strip()])

        # Extract client name
        client_match = re.search(r"(?:client|company|vendor|for)\s*[:\-]?\s*[\"']?([A-Z][a-zA-Z\s&]+)", context)
        if client_match:
            result["client_name"] = client_match.group(1).strip()

        # Remove duplicates
        result["sheet_names"] = list(dict.fromkeys(result["sheet_names"]))

        return result


class GenerationPipeline:
    """Orchestrates the full generation pipeline for a project."""

    def __init__(self, project_id: uuid.UUID):
        self.project_id = project_id
        self.storage = get_storage_client()
        self.ai_client = get_ai_client()
        self.temp_dir: Path | None = None
        self.output_files: list[dict] = []

    async def run(self):
        """Main pipeline entry point. Runs all generation steps."""
        logger.info(f"Starting generation pipeline for project {self.project_id}")

        try:
            await self._update_status("processing", "Initializing pipeline...")

            # Get project and documents
            async with async_session() as db:
                project = await db.get(Project, self.project_id)
                if not project:
                    raise ValueError(f"Project {self.project_id} not found")

                result = await db.execute(
                    select(Document).where(Document.project_id == self.project_id)
                )
                documents = result.scalars().all()

            if not documents:
                await self._update_status("failed", "No documents found in project")
                return

            upload_context = project.upload_context or ""
            context_info = UploadContextParser.parse(upload_context)

            # Create temp directory for processing
            with tempfile.TemporaryDirectory(prefix="rfp_gen_") as tmp:
                self.temp_dir = Path(tmp)
                output_dir = self.temp_dir / "output"
                output_dir.mkdir()

                # Step 1: Download documents from S3
                await self._update_status("processing", "Downloading documents...")
                local_files = await self._download_documents(documents)

                if not local_files:
                    await self._update_status("failed", "No documents could be downloaded")
                    return

                # Classify files by type
                pdf_docx_files = [f for f in local_files if f["type"] in ("pdf", "docx")]
                xlsx_files = [f for f in local_files if f["type"] == "xlsx"]

                # Step 2: Extract schedule from PDF/DOCX files
                schedule_json = None
                if pdf_docx_files:
                    await self._update_status("processing", "Extracting schedule from documents...")
                    schedule_json = self._run_schedule_extraction(pdf_docx_files[0]["path"])

                # Step 3: Generate Win Plan DOCX
                if schedule_json:
                    await self._update_status("processing", "Generating Win Plan document...")
                    win_plan_path = output_dir / "Win_Plan.docx"
                    self._run_win_plan_generation(schedule_json, win_plan_path, context_info)

                # Step 4: Answer Excel RFP questions
                for xlsx_file in xlsx_files:
                    await self._update_status(
                        "processing",
                        f"Answering questions in {xlsx_file['filename']}..."
                    )
                    answered_path = output_dir / f"Answered_{xlsx_file['filename']}"
                    await self._run_excel_answering(
                        xlsx_file["path"], answered_path, context_info, upload_context
                    )

                # Step 5: Generate RFI Response PDF
                if pdf_docx_files or schedule_json:
                    await self._update_status("processing", "Generating RFI Response PDF...")
                    pdf_path = output_dir / "RFI_Response.pdf"
                    self._run_pdf_generation(pdf_path, context_info, schedule_json)

                # Step 6: Upload outputs to S3
                await self._update_status("processing", "Uploading generated documents...")
                await self._upload_outputs()

            await self._update_status(
                "completed",
                f"Generation complete! {len(self.output_files)} document(s) generated."
            )
            logger.info(f"Pipeline completed for project {self.project_id}")

        except Exception as e:
            logger.exception(f"Pipeline failed for project {self.project_id}: {e}")
            await self._update_status("failed", f"Pipeline failed: {str(e)[:500]}")

    async def _download_documents(self, documents: list[Document]) -> list[dict]:
        """Download documents from S3 to temp directory."""
        local_files = []
        for doc in documents:
            try:
                file_data = self.storage.download_file(doc.file_path)
                local_path = self.temp_dir / doc.filename
                local_path.write_bytes(file_data)
                local_files.append({
                    "path": str(local_path),
                    "filename": doc.filename,
                    "type": doc.file_type,
                    "doc_id": str(doc.id),
                })
                logger.info(f"Downloaded {doc.filename} ({len(file_data)} bytes)")
            except Exception as e:
                logger.warning(f"Failed to download {doc.filename}: {e}")
        return local_files

    def _run_schedule_extraction(self, file_path: str) -> dict | None:
        """Extract schedule from a PDF/DOCX file using extract_schedule.py."""
        if not EXTRACT_SCHEDULE_SCRIPT.exists():
            logger.warning(f"Schedule extraction script not found: {EXTRACT_SCHEDULE_SCRIPT}")
            return None

        try:
            result = subprocess.run(
                ["python3", str(EXTRACT_SCHEDULE_SCRIPT), "--input", file_path, "--parse-only"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(SKILLS_DIR / "GetSchedule" / "scripts"),
            )
            if result.returncode == 0 and result.stdout.strip():
                parsed = json.loads(result.stdout)
                logger.info(f"Schedule extraction: parsed document text ({len(parsed.get('text', ''))} chars)")
                return parsed
            else:
                logger.warning(f"Schedule extraction returned code {result.returncode}: {result.stderr[:500]}")
                return None
        except subprocess.TimeoutExpired:
            logger.warning("Schedule extraction timed out")
            return None
        except Exception as e:
            logger.warning(f"Schedule extraction failed: {e}")
            return None

    def _run_win_plan_generation(self, schedule_json: dict, output_path: Path, context_info: dict):
        """Generate a Win Plan DOCX from schedule data."""
        if not GENERATE_WIN_PLAN_SCRIPT.exists():
            logger.warning(f"Win Plan script not found: {GENERATE_WIN_PLAN_SCRIPT}")
            return

        # Write schedule data to temp file
        schedule_file = self.temp_dir / "schedule_data.json"

        # Structure data as the script expects
        plan_data = {
            "events": schedule_json.get("events", schedule_json.get("schedule_events", [])),
            "client_name": context_info.get("client_name", ""),
            "document_name": schedule_json.get("filename", "RFP Document"),
        }
        schedule_file.write_text(json.dumps(plan_data, indent=2))

        try:
            result = subprocess.run(
                [
                    "python3", str(GENERATE_WIN_PLAN_SCRIPT),
                    "--input", str(schedule_file),
                    "--output", str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(SKILLS_DIR / "GetSchedule" / "scripts"),
            )
            if result.returncode == 0 and output_path.exists():
                self.output_files.append({
                    "path": str(output_path),
                    "filename": output_path.name,
                    "type": "docx",
                    "category": "generated_output",
                })
                logger.info(f"Win Plan generated: {output_path}")
            else:
                logger.warning(f"Win Plan generation failed: {result.stderr[:500]}")
        except subprocess.TimeoutExpired:
            logger.warning("Win Plan generation timed out")
        except Exception as e:
            logger.warning(f"Win Plan generation failed: {e}")

    async def _run_excel_answering(
        self,
        xlsx_path: str,
        output_path: Path,
        context_info: dict,
        upload_context: str,
    ):
        """Parse Excel RFP, generate AI answers, write back."""
        if not PARSE_EXCEL_SCRIPT.exists():
            logger.warning(f"Excel parser script not found: {PARSE_EXCEL_SCRIPT}")
            return

        # Step 1: Parse questions from Excel
        parse_cmd = [
            "python3", str(PARSE_EXCEL_SCRIPT),
            "--input", xlsx_path,
            "--parse-only",
        ]
        if context_info.get("sheet_names"):
            parse_cmd.extend(["--sheets", ",".join(context_info["sheet_names"])])

        try:
            result = subprocess.run(
                parse_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(SKILLS_DIR / "AnswerRFI_RFP_OPExcel" / "scripts"),
            )
            if result.returncode != 0:
                logger.warning(f"Excel parsing failed: {result.stderr[:500]}")
                return

            parsed_data = json.loads(result.stdout)
        except Exception as e:
            logger.warning(f"Excel parsing failed: {e}")
            return

        # Check if we got sheets with questions
        sheets = parsed_data.get("sheets", [])
        if not sheets:
            logger.info("No sheets with questions found")
            return

        # Step 2: Generate AI answers for each sheet
        all_answers = []
        for sheet in sheets:
            questions = sheet.get("questions", [])
            if not questions:
                continue

            sheet_name = sheet.get("sheet_name", "Unknown")
            structure = sheet.get("structure", {})
            response_col = structure.get("response_col")

            if not response_col:
                logger.warning(f"No response column detected for sheet '{sheet_name}'")
                continue

            logger.info(f"Generating answers for {len(questions)} questions in '{sheet_name}'")

            # Batch questions
            for i in range(0, len(questions), ANSWER_BATCH_SIZE):
                batch = questions[i:i + ANSWER_BATCH_SIZE]
                batch_answers = await self._generate_answers_batch(
                    batch, sheet_name, response_col, upload_context
                )
                all_answers.extend(batch_answers)

        if not all_answers:
            logger.info("No answers generated for Excel file")
            return

        # Step 3: Write answers back to Excel
        answers_file = self.temp_dir / "answers.json"
        answers_data = {"answers": all_answers}
        answers_file.write_text(json.dumps(answers_data, indent=2))

        try:
            write_cmd = [
                "python3", str(PARSE_EXCEL_SCRIPT),
                "--input", xlsx_path,
                "--write-answers", str(answers_file),
                "--output-file", str(output_path),
            ]
            result = subprocess.run(
                write_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(SKILLS_DIR / "AnswerRFI_RFP_OPExcel" / "scripts"),
            )
            if result.returncode == 0 and output_path.exists():
                self.output_files.append({
                    "path": str(output_path),
                    "filename": output_path.name,
                    "type": "xlsx",
                    "category": "generated_output",
                })
                logger.info(f"Answered Excel written: {output_path} ({len(all_answers)} answers)")
            else:
                logger.warning(f"Excel write-back failed: {result.stderr[:500]}")
        except Exception as e:
            logger.warning(f"Excel write-back failed: {e}")

    async def _generate_answers_batch(
        self,
        questions: list[dict],
        sheet_name: str,
        response_col: str,
        upload_context: str,
    ) -> list[dict]:
        """Generate AI answers for a batch of questions."""
        answers = []

        # Build the prompt
        questions_text = ""
        for q in questions:
            row = q.get("row")
            q_text = q.get("question", "")
            q_type = q.get("type", "narrative")
            category = q.get("category", "")
            questions_text += f"Row {row} | Type: {q_type} | Category: {category}\nQ: {q_text}\n\n"

        user_prompt = f"""Answer the following RFP/RFI questions for sheet "{sheet_name}".

{f'Additional context from the user: {upload_context}' if upload_context else ''}

Return your answers as a JSON array where each item has:
- "row": the row number (integer)
- "sheet_name": "{sheet_name}"
- "response_col_letter": "{response_col}"
- "answer": your response text

Questions:
{questions_text}

Respond with ONLY the JSON array, no markdown formatting or code blocks."""

        try:
            response_text = self.ai_client.generate(
                system_prompt=ANSWER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=8192,
                temperature=0.1,
            )

            # Parse the JSON response
            # Strip markdown code fences if present
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
                cleaned = re.sub(r"\n?```\s*$", "", cleaned)

            batch_answers = json.loads(cleaned)
            if isinstance(batch_answers, list):
                answers.extend(batch_answers)
                logger.info(f"Generated {len(batch_answers)} answers for batch")
            else:
                logger.warning(f"Unexpected AI response format: {type(batch_answers)}")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
        except Exception as e:
            logger.warning(f"AI answer generation failed: {e}")

        return answers

    def _run_pdf_generation(self, output_path: Path, context_info: dict, schedule_json: dict | None):
        """Generate an RFI Response PDF."""
        if not GENERATE_PDF_SCRIPT.exists():
            logger.warning(f"PDF generation script not found: {GENERATE_PDF_SCRIPT}")
            return

        # Build the data structure expected by generate_pdf.py
        client_name = context_info.get("client_name", "Client")
        pdf_data = {
            "client_name": client_name,
            "solution_name": "IBM OpenPages",
            "rfi_description": f"RFP/RFI Response for {client_name}",
            "company": {
                "name": "IBM",
                "address_line1": "1 New Orchard Road",
                "address_line2": "Armonk, NY 10504",
                "contact_name": "[Contact Name]",
                "contact_title": "Account Executive",
                "contact_email": "[contact@ibm.com]",
                "contact_phone": "[Phone Number]",
            },
            "sections": {
                "executive_summary": {
                    "paragraphs": [
                        f"IBM is pleased to submit this response to {client_name}'s Request for Information/Proposal for a Governance, Risk, and Compliance (GRC) solution.",
                        "IBM OpenPages is a market-leading, AI-powered integrated GRC platform that enables organizations to manage risk and compliance with greater efficiency, insight, and confidence.",
                        "Built on IBM Cloud Pak for Data / watsonx, OpenPages provides a unified platform for Operational Risk Management, Regulatory Compliance, IT Governance, Policy Management, Internal Audit, Financial Controls, and Third-Party Risk Management.",
                    ],
                    "bullet_points": [
                        "Unified GRC platform with 8+ integrated modules",
                        "AI-powered insights via Watson / watsonx.ai",
                        "SOC 2 Type II, ISO 27001, FedRAMP certified",
                        "Flexible deployment: SaaS, on-premises, or hybrid",
                    ],
                },
                "company_profile": {
                    "description": "IBM is a global technology and consulting company headquartered in Armonk, New York. IBM OpenPages has been a Gartner Magic Quadrant Leader for Integrated Risk Management solutions.",
                    "credentials": [
                        "Fortune 500 company with 100+ years of innovation",
                        "Serving 170+ countries worldwide",
                        "12,000+ GRC implementations globally",
                    ],
                    "certifications": [
                        "SOC 2 Type II",
                        "ISO 27001",
                        "FedRAMP Authorized",
                        "ISO 22301 Business Continuity",
                    ],
                },
                "solution_profile": {
                    "overview": "IBM OpenPages is an AI-powered, integrated GRC platform that provides a single environment to identify, manage, monitor, and report on risk and regulatory compliance.",
                    "features": [
                        {"name": "Operational Risk Management", "description": "Identify, assess, mitigate, and monitor operational risks with configurable risk taxonomies, RCSA, loss event management, and KRI tracking."},
                        {"name": "Regulatory Compliance Management", "description": "Map regulations to controls, automate compliance assessments, and track regulatory changes across jurisdictions."},
                        {"name": "Policy & Document Management", "description": "Centralized policy lifecycle management with version control, attestation workflows, and automated distribution."},
                        {"name": "Internal Audit Management", "description": "Plan, execute, and report on audits with risk-based planning, workpaper management, and issue tracking."},
                        {"name": "Third-Party Risk Management", "description": "Assess and monitor third-party risks with vendor assessments, due diligence workflows, and continuous monitoring."},
                    ],
                },
                "technical_information": {
                    "content": "IBM OpenPages supports modern deployment architectures including cloud-native SaaS, containerized on-premises (Red Hat OpenShift), and hybrid models. The platform provides REST APIs, SSO/SAML integration, LDAP/AD support, and role-based access control.",
                    "attached_documents": [],
                },
            },
            "revision_history": [
                {"version": "1.0", "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "author": "IBM", "description": "Initial response"},
            ],
            "appendices": [],
            "copyright": {
                "year": str(datetime.now(timezone.utc).year),
                "company_name": "IBM Corporation",
                "notice_text": "This document contains proprietary and confidential information.",
            },
        }

        data_file = self.temp_dir / "pdf_data.json"
        data_file.write_text(json.dumps(pdf_data, indent=2))

        try:
            result = subprocess.run(
                [
                    "python3", str(GENERATE_PDF_SCRIPT),
                    "--input", str(data_file),
                    "--output", str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(SKILLS_DIR / "CreateRFIResponse" / "scripts"),
            )
            if result.returncode == 0 and output_path.exists():
                self.output_files.append({
                    "path": str(output_path),
                    "filename": output_path.name,
                    "type": "pdf",
                    "category": "generated_output",
                })
                logger.info(f"RFI Response PDF generated: {output_path}")
            else:
                logger.warning(f"PDF generation failed: {result.stderr[:500]}")
        except subprocess.TimeoutExpired:
            logger.warning("PDF generation timed out")
        except Exception as e:
            logger.warning(f"PDF generation failed: {e}")

    async def _upload_outputs(self):
        """Upload generated output files to S3 and create Document records."""
        async with async_session() as db:
            try:
                for output in self.output_files:
                    file_path = Path(output["path"])
                    if not file_path.exists():
                        continue

                    file_data = file_path.read_bytes()
                    object_name = f"projects/{self.project_id}/generated/{uuid.uuid4()}/{output['filename']}"

                    # Determine content type
                    content_types = {
                        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "pdf": "application/pdf",
                    }
                    content_type = content_types.get(output["type"], "application/octet-stream")

                    # Upload to S3
                    self.storage.upload_file(object_name, file_data, content_type)

                    # Create Document record
                    doc = Document(
                        project_id=self.project_id,
                        filename=output["filename"],
                        file_path=object_name,
                        file_type=output["type"],
                        file_size_bytes=len(file_data),
                        doc_category=output.get("category", "generated_output"),
                        status="completed",
                    )
                    db.add(doc)
                    logger.info(f"Uploaded output: {output['filename']} ({len(file_data)} bytes)")

                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to upload outputs: {e}")
                raise

    async def _update_status(self, status: str, message: str):
        """Update project processing status in the database."""
        async with async_session() as db:
            try:
                project = await db.get(Project, self.project_id)
                if project:
                    project.processing_status = status
                    project.processing_message = message
                    if status == "processing" and not project.processing_started_at:
                        project.processing_started_at = datetime.now(timezone.utc)
                    await db.commit()
                    logger.info(f"Status update: {status} - {message}")
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to update status: {e}")
