"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  projects as projectsApi,
  documents as documentsApi,
  requirements as requirementsApi,
  responses as responsesApi,
  schedule as scheduleApi,
  pricing as pricingApi,
  exportApi,
  plan as planApi,
} from "@/lib/api";
import type {
  Project,
  Document,
  Requirement,
  Response,
  ScheduleEvent,
  PricingItem,
  ComplianceScores,
} from "@/types";
import { useDropzone } from "react-dropzone";
import {
  formatDate,
  formatFileSize,
  statusColor,
  complianceStatusColor,
  complianceStatusLabel,
  priorityColor,
} from "@/lib/utils";

type Tab = "documents" | "requirements" | "responses" | "schedule" | "pricing" | "export";

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [responses, setResponses] = useState<Response[]>([]);
  const [scheduleEvents, setScheduleEvents] = useState<ScheduleEvent[]>([]);
  const [pricingItems, setPricingItems] = useState<PricingItem[]>([]);
  const [complianceScores, setComplianceScores] = useState<ComplianceScores | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("documents");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    loadProject();
  }, [projectId]);

  useEffect(() => {
    if (activeTab === "documents") loadDocuments();
    else if (activeTab === "requirements") loadRequirements();
    else if (activeTab === "responses") loadResponses();
    else if (activeTab === "schedule") loadSchedule();
    else if (activeTab === "pricing") loadPricing();
  }, [activeTab, projectId]);

  async function loadProject() {
    try {
      const data: any = await projectsApi.get(projectId);
      setProject(data);
    } catch {
    } finally {
      setLoading(false);
    }
  }

  async function loadDocuments() {
    try {
      const data: any = await documentsApi.list(projectId);
      setDocuments(data.documents || []);
    } catch {}
  }

  async function loadRequirements() {
    try {
      const data: any = await requirementsApi.list(projectId);
      setRequirements(data.requirements || []);
    } catch {}
  }

  async function loadResponses() {
    try {
      const data: any = await responsesApi.list(projectId);
      setResponses(data.responses || []);
      setComplianceScores(data.compliance_scores || null);
    } catch {}
  }

  async function loadSchedule() {
    try {
      const data: any = await scheduleApi.list(projectId);
      setScheduleEvents(Array.isArray(data) ? data : []);
    } catch {}
  }

  async function loadPricing() {
    try {
      const data: any = await pricingApi.list(projectId);
      setPricingItems(Array.isArray(data) ? data : []);
    } catch {}
  }

  // File upload handler
  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setActionLoading("upload");
      try {
        await documentsApi.upload(projectId, acceptedFiles);
        loadDocuments();
        loadProject();
      } catch (err: any) {
        alert(err.message);
      } finally {
        setActionLoading(null);
      }
    },
    [projectId]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
    },
  });

  async function handleParseAll() {
    setActionLoading("parse");
    try {
      for (const doc of documents.filter((d) => d.status === "uploaded")) {
        await documentsApi.parse(doc.id);
      }
      loadDocuments();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleExtract() {
    setActionLoading("extract");
    try {
      const result: any = await requirementsApi.extract(projectId);
      alert(result.message);
      setActiveTab("requirements");
      loadRequirements();
      loadProject();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleGenerate() {
    setActionLoading("generate");
    try {
      const result: any = await responsesApi.generate(projectId);
      alert(result.message);
      setActiveTab("responses");
      loadResponses();
      loadProject();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleExtractSchedule() {
    setActionLoading("schedule");
    try {
      const result: any = await scheduleApi.extract(projectId);
      alert(result.message);
      loadSchedule();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleExportWord() {
    setActionLoading("export");
    try {
      const blob = await exportApi.word(projectId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `RFP_Response_${project?.name?.replace(/\s+/g, "_") || "export"}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleGeneratePlan() {
    setActionLoading("plan");
    try {
      await planApi.generate(projectId);
      alert("Response plan generated successfully");
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) return <div className="text-center py-12 text-gray-500">Loading project...</div>;
  if (!project) return <div className="text-center py-12 text-red-500">Project not found</div>;

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "documents", label: "Documents", count: project.document_count },
    { key: "requirements", label: "Requirements", count: project.requirement_count },
    { key: "responses", label: "Responses", count: project.response_count },
    { key: "schedule", label: "Schedule" },
    { key: "pricing", label: "Pricing" },
    { key: "export", label: "Export" },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <a href="/projects" className="text-primary-600 hover:underline text-sm">
            Projects
          </a>
          <span className="text-gray-400">/</span>
          <span className="text-gray-600 text-sm">{project.name}</span>
        </div>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
            <p className="text-gray-500 mt-1">
              {project.client_name || "No client"} {project.industry && `| ${project.industry}`}
            </p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColor(project.status)}`}>
            {project.status.replace("_", " ")}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                activeTab === tab.key
                  ? "border-primary-600 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span className="ml-1.5 bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full text-xs">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === "documents" && (
        <div>
          {/* Upload Zone */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer mb-6 transition ${
              isDragActive ? "border-primary-400 bg-primary-50" : "border-gray-300 hover:border-primary-300"
            }`}
          >
            <input {...getInputProps()} />
            {actionLoading === "upload" ? (
              <p className="text-gray-500">Uploading...</p>
            ) : isDragActive ? (
              <p className="text-primary-600 font-medium">Drop files here...</p>
            ) : (
              <div>
                <p className="text-gray-600 font-medium">Drag & drop files here, or click to browse</p>
                <p className="text-sm text-gray-400 mt-1">PDF, DOCX, XLSX, CSV, PPTX</p>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 mb-6">
            <button
              onClick={handleParseAll}
              disabled={!!actionLoading || documents.filter((d) => d.status === "uploaded").length === 0}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
            >
              {actionLoading === "parse" ? "Parsing..." : "Parse All Documents"}
            </button>
            <button
              onClick={handleExtract}
              disabled={!!actionLoading || documents.filter((d) => d.status === "parsed").length === 0}
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 text-sm font-medium disabled:opacity-50"
            >
              {actionLoading === "extract" ? "Extracting..." : "Extract Requirements"}
            </button>
          </div>

          {/* Document List */}
          <div className="bg-white rounded-lg border border-gray-200">
            {documents.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No documents uploaded yet</div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Filename</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Category</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Size</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Pages</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{doc.filename}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 uppercase">{doc.file_type}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {doc.doc_category?.replace("_", " ") || "-"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">{formatFileSize(doc.file_size_bytes)}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{doc.page_count || "-"}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor(doc.status)}`}>
                          {doc.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {activeTab === "requirements" && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <p className="text-sm text-gray-500">{requirements.length} requirements extracted</p>
            <button
              onClick={handleGenerate}
              disabled={!!actionLoading || requirements.length === 0}
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 text-sm font-medium disabled:opacity-50"
            >
              {actionLoading === "generate" ? "Generating..." : "Generate AI Responses"}
            </button>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
            {requirements.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No requirements extracted yet. Upload and parse documents first.
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">ID</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Title</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Category</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Mandatory</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Priority</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {requirements.map((req) => (
                    <tr key={req.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-mono text-gray-600">{req.req_number}</td>
                      <td className="px-4 py-3 text-sm text-gray-900 max-w-md">
                        <p className="font-medium">{req.title}</p>
                        <p className="text-gray-500 text-xs mt-1 line-clamp-2">{req.description}</p>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">{req.type.replace("_", " ")}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{req.category || "-"}</td>
                      <td className="px-4 py-3 text-sm">
                        {req.is_mandatory ? (
                          <span className="text-red-600 font-medium">Yes</span>
                        ) : (
                          <span className="text-gray-400">No</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${priorityColor(req.priority)}`}>
                          {req.priority}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {activeTab === "responses" && (
        <div>
          {/* Compliance Scores */}
          {complianceScores && (
            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <p className="text-sm text-gray-500">Overall Compliance</p>
                <p className="text-2xl font-bold text-primary-600">{complianceScores.overall_score}%</p>
              </div>
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <p className="text-sm text-gray-500">Functional</p>
                <p className="text-2xl font-bold text-green-600">{complianceScores.functional_score}%</p>
              </div>
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <p className="text-sm text-gray-500">Non-Functional</p>
                <p className="text-2xl font-bold text-blue-600">{complianceScores.non_functional_score}%</p>
              </div>
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <p className="text-sm text-gray-500">Responses</p>
                <p className="text-2xl font-bold text-gray-900">
                  {complianceScores.total_responses} / {complianceScores.total_requirements}
                </p>
              </div>
            </div>
          )}

          <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
            {responses.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No responses generated yet. Extract requirements and generate responses.
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Req ID</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Compliance</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Response</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Confidence</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {responses.map((resp) => {
                    const req = requirements.find((r) => r.id === resp.requirement_id);
                    return (
                      <tr key={resp.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-mono text-gray-600">
                          {req?.req_number || "-"}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-1 rounded-full text-xs font-medium ${complianceStatusColor(resp.compliance_status)}`}
                          >
                            {complianceStatusLabel(resp.compliance_status)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700 max-w-lg">
                          <p className="line-clamp-3">{resp.response_text}</p>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {resp.confidence_score !== null ? (
                            <span
                              className={
                                resp.confidence_score >= 0.7 ? "text-green-600" : "text-orange-600 font-medium"
                              }
                            >
                              {(resp.confidence_score * 100).toFixed(0)}%
                            </span>
                          ) : (
                            "-"
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {resp.is_reviewed ? (
                            <span className="text-green-600 font-medium">Reviewed</span>
                          ) : resp.is_ai_generated ? (
                            <span className="text-blue-600">AI Draft</span>
                          ) : (
                            <span className="text-gray-400">Manual</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {activeTab === "schedule" && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <p className="text-sm text-gray-500">{scheduleEvents.length} events</p>
            <button
              onClick={handleExtractSchedule}
              disabled={!!actionLoading}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
            >
              {actionLoading === "schedule" ? "Extracting..." : "Extract Schedule from Documents"}
            </button>
          </div>

          <div className="bg-white rounded-lg border border-gray-200">
            {scheduleEvents.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No schedule events. Extract from parsed documents.
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Event</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Date</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {scheduleEvents.map((event) => (
                    <tr key={event.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{event.event_name}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{event.event_type.replace("_", " ")}</td>
                      <td className="px-4 py-3 text-sm text-gray-700">{event.event_date || "TBD"}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{event.notes || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {activeTab === "pricing" && (
        <div>
          <div className="bg-white rounded-lg border border-gray-200">
            {pricingItems.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No pricing items yet.</div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Category</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Line Item</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Unit Cost</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Qty</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {pricingItems.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-700">{item.category.replace("_", " ")}</td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{item.line_item}</td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {item.unit_cost != null ? `$${item.unit_cost.toLocaleString()}` : "-"}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">{item.quantity || "-"}</td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {item.total != null ? `$${item.total.toLocaleString()}` : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {activeTab === "export" && (
        <div className="max-w-2xl">
          <h2 className="text-lg font-semibold mb-4">Export RFP Response</h2>

          <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-6">
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Document Sections</h3>
              <p className="text-sm text-gray-500">The exported Word document will include all 13 mandatory sections:</p>
              <ol className="text-sm text-gray-600 mt-2 space-y-1 list-decimal list-inside">
                <li>Executive Summary</li>
                <li>About the Company</li>
                <li>Understanding of Requirements</li>
                <li>Proposed Solution Overview</li>
                <li>Functional Compliance Matrix</li>
                <li>Non-Functional Compliance Matrix</li>
                <li>Architecture Overview</li>
                <li>Implementation Approach</li>
                <li>Project Plan</li>
                <li>Pricing</li>
                <li>Assumptions</li>
                <li>Risks & Mitigation</li>
                <li>Legal & Compliance Statements</li>
              </ol>
            </div>

            <div>
              <h3 className="font-medium text-gray-900 mb-2">Project Summary</h3>
              <div className="text-sm text-gray-600 space-y-1">
                <p>Requirements: {project.requirement_count}</p>
                <p>Responses: {project.response_count}</p>
                <p>Schedule Events: {scheduleEvents.length}</p>
                <p>Pricing Items: {pricingItems.length}</p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleExportWord}
                disabled={!!actionLoading}
                className="bg-primary-600 text-white px-6 py-2.5 rounded-lg hover:bg-primary-700 text-sm font-medium disabled:opacity-50"
              >
                {actionLoading === "export" ? "Generating..." : "Download Word Document"}
              </button>
              <button
                onClick={handleGeneratePlan}
                disabled={!!actionLoading}
                className="bg-gray-600 text-white px-6 py-2.5 rounded-lg hover:bg-gray-700 text-sm font-medium disabled:opacity-50"
              >
                {actionLoading === "plan" ? "Generating..." : "Generate Response Plan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
