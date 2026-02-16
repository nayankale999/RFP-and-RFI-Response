"use client";

import { useEffect, useState, useCallback, useRef } from "react";
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
  generation as generationApi,
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
  const [uploadContext, setUploadContext] = useState("");
  const [generationPolling, setGenerationPolling] = useState(false);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Polling for generation status — uses raw fetch to avoid auto-redirect on 401
  useEffect(() => {
    if (generationPolling) {
      pollingRef.current = setInterval(async () => {
        try {
          const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
          const headers: Record<string, string> = { "Content-Type": "application/json" };
          if (token) headers["Authorization"] = `Bearer ${token}`;
          const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          const res = await fetch(`${API_BASE}/api/projects/${projectId}`, { headers });
          if (!res.ok) return; // Silently skip — don't redirect on polling errors
          const data = await res.json();
          setProject(data);
          if (data.processing_status !== "processing") {
            setGenerationPolling(false);
            // Refresh document list to show generated files
            loadDocuments();
          }
        } catch {
          // Silently ignore polling errors
        }
      }, 5000);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [generationPolling, projectId]);

  // Start polling if project is already processing on load
  useEffect(() => {
    if (project?.processing_status === "processing") {
      setGenerationPolling(true);
    }
  }, [project?.processing_status]);

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
      setUploadContext(data.upload_context || "");
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

  // Save upload context on blur
  async function saveUploadContext() {
    try {
      await projectsApi.update(projectId, { upload_context: uploadContext });
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

  async function handleDownloadDocument(docId: string, filename: string) {
    try {
      const blob = await documentsApi.download(docId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Download failed: ${err.message}`);
    }
  }

  async function handleDeleteDocument(docId: string, filename: string) {
    if (!confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    try {
      await documentsApi.delete(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  }

  async function handleGenerateWinPlanAndAnswer() {
    // Save context first
    try {
      await projectsApi.update(projectId, { upload_context: uploadContext });
    } catch {}

    setActionLoading("generate-full");
    try {
      await generationApi.trigger(projectId);
      // Optimistically show the processing banner immediately
      setProject((prev) =>
        prev ? { ...prev, processing_status: "processing", processing_message: "Initializing pipeline..." } : prev
      );
      setGenerationPolling(true);
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

          {/* Context Text Box */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              File Context & Instructions
            </label>
            <textarea
              value={uploadContext}
              onChange={(e) => setUploadContext(e.target.value)}
              onBlur={saveUploadContext}
              placeholder="Provide context about uploaded files — e.g., which Excel tabs/sheets contain the questions to answer, which documents describe the RFP scope, etc."
              rows={3}
              className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-y"
            />
            <p className="text-xs text-gray-400 mt-1">
              This context helps guide AI processing of your documents. Auto-saved when you click away.
            </p>
          </div>

          {/* Generation Status Banner */}
          {project.processing_status === "processing" && (
            <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <svg className="animate-spin h-5 w-5 text-blue-600 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <div className="flex-1">
                  <p className="text-sm font-medium text-blue-800">Generation in progress...</p>
                  <p className="text-xs text-blue-600 mt-0.5">{project.processing_message || "Processing your documents"}</p>
                </div>
                {project.processing_started_at && (
                  <span className="text-xs text-blue-500 flex-shrink-0">
                    Started {new Date(project.processing_started_at).toLocaleTimeString()}
                  </span>
                )}
              </div>
              <div className="mt-3">
                <div className="w-full bg-blue-200 rounded-full h-1.5">
                  <div className="bg-blue-600 h-1.5 rounded-full animate-pulse" style={{ width: "60%" }}></div>
                </div>
                <p className="text-xs text-blue-500 mt-1.5">This may take 5-10 minutes depending on the number of questions.</p>
              </div>
            </div>
          )}

          {project.processing_status === "completed" && (
            <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
              <svg className="h-5 w-5 text-green-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-sm font-medium text-green-800">Generation complete!</p>
                <p className="text-xs text-green-600 mt-0.5">{project.processing_message || "Documents generated successfully"}</p>
              </div>
              <button
                onClick={() => projectsApi.update(projectId, { processing_status: null, processing_message: null }).then(loadProject)}
                className="ml-auto text-green-600 hover:text-green-800 text-xs underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {project.processing_status === "failed" && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
              <svg className="h-5 w-5 text-red-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-sm font-medium text-red-800">Generation failed</p>
                <p className="text-xs text-red-600 mt-0.5">{project.processing_message || "An error occurred"}</p>
              </div>
              <button
                onClick={() => projectsApi.update(projectId, { processing_status: null, processing_message: null }).then(loadProject)}
                className="ml-auto text-red-600 hover:text-red-800 text-xs underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Action Button */}
          <div className="flex gap-3 mb-6">
            <button
              onClick={handleGenerateWinPlanAndAnswer}
              disabled={
                !!actionLoading ||
                documents.length === 0 ||
                project.processing_status === "processing"
              }
              className="bg-indigo-600 text-white px-5 py-2.5 rounded-lg hover:bg-indigo-700 text-sm font-medium disabled:opacity-50 flex items-center gap-2 transition"
            >
              {actionLoading === "generate-full" || project.processing_status === "processing" ? (
                <>
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing...
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Generate Win Plan & Answer RFP/RFI
                </>
              )}
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
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase"></th>
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
                      <td className="px-4 py-3 flex items-center space-x-2">
                        <button
                          onClick={() => handleDownloadDocument(doc.id, doc.filename)}
                          className="text-primary-600 hover:text-primary-800 text-sm font-medium"
                          title="Download file"
                        >
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                          className="text-red-500 hover:text-red-700 text-sm font-medium"
                          title="Delete document"
                        >
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
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
