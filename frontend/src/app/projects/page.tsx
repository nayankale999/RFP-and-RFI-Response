"use client";

import { useEffect, useState } from "react";
import { projects as projectsApi } from "@/lib/api";
import type { Project } from "@/types";
import Link from "next/link";
import { statusColor, formatDate } from "@/lib/utils";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({ name: "", description: "", client_name: "", industry: "" });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  async function loadProjects() {
    try {
      const data: any = await projectsApi.list();
      setProjects(data.projects || []);
    } catch {
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await projectsApi.create(formData);
      setShowCreate(false);
      setFormData({ name: "", description: "", client_name: "", industry: "" });
      loadProjects();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 text-sm font-medium"
        >
          + New Project
        </button>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-bold mb-4">Create New Project</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Project Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  placeholder="e.g., Enterprise CRM RFP 2026"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Client Name</label>
                <input
                  type="text"
                  value={formData.client_name}
                  onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Acme Corp"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
                <input
                  type="text"
                  value={formData.industry}
                  onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Financial Services"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500"
                  rows={3}
                  placeholder="Brief description of the RFP..."
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 text-sm font-medium disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Projects List */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading projects...</div>
      ) : projects.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <p className="text-gray-500 mb-4">No projects yet. Create your first project to get started.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="bg-white rounded-lg border border-gray-200 p-6 hover:border-primary-300 hover:shadow-sm transition"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{project.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{project.client_name || "No client"}</p>
                  {project.description && (
                    <p className="text-sm text-gray-600 mt-2 line-clamp-2">{project.description}</p>
                  )}
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColor(project.status)}`}>
                  {project.status.replace("_", " ")}
                </span>
              </div>
              <div className="flex items-center gap-6 mt-4 text-sm text-gray-500">
                <span>{project.document_count} documents</span>
                <span>{project.requirement_count} requirements</span>
                <span>{project.response_count} responses</span>
                {project.deadline && <span>Due: {formatDate(project.deadline)}</span>}
                <span className="ml-auto">{formatDate(project.created_at)}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
