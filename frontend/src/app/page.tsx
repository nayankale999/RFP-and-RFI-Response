"use client";

import { useEffect, useState } from "react";
import { projects as projectsApi } from "@/lib/api";
import type { Project } from "@/types";
import Link from "next/link";
import { statusColor, formatDate } from "@/lib/utils";

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    projectsApi
      .list()
      .then((data: any) => setProjects(data.projects || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Manage your RFP/RFI response projects</p>
        </div>
        <Link
          href="/projects"
          className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 text-sm font-medium"
        >
          View All Projects
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <p className="text-sm text-gray-500">Total Projects</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{projects.length}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <p className="text-sm text-gray-500">In Progress</p>
          <p className="text-3xl font-bold text-blue-600 mt-1">
            {projects.filter((p) => p.status === "in_progress").length}
          </p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <p className="text-sm text-gray-500">In Review</p>
          <p className="text-3xl font-bold text-purple-600 mt-1">
            {projects.filter((p) => p.status === "review").length}
          </p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <p className="text-sm text-gray-500">Completed</p>
          <p className="text-3xl font-bold text-green-600 mt-1">
            {projects.filter((p) => p.status === "completed").length}
          </p>
        </div>
      </div>

      {/* Recent Projects */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">Recent Projects</h2>
        </div>
        {loading ? (
          <div className="p-6 text-center text-gray-500">Loading...</div>
        ) : projects.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-500 mb-4">No projects yet</p>
            <Link
              href="/projects"
              className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 text-sm"
            >
              Create Your First Project
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {projects.slice(0, 5).map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-gray-50"
              >
                <div>
                  <p className="font-medium text-gray-900">{project.name}</p>
                  <p className="text-sm text-gray-500">{project.client_name || "No client"}</p>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-500">
                    {project.requirement_count} requirements
                  </span>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor(project.status)}`}
                  >
                    {project.status.replace("_", " ")}
                  </span>
                  <span className="text-sm text-gray-400">{formatDate(project.created_at)}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
