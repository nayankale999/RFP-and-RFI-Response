import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | null): string {
  if (!date) return "N/A";
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatFileSize(bytes: number | null): string {
  if (!bytes) return "N/A";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function complianceStatusColor(status: string): string {
  const colors: Record<string, string> = {
    fully_compliant: "bg-green-100 text-green-800",
    partially_compliant: "bg-yellow-100 text-yellow-800",
    configurable: "bg-blue-100 text-blue-800",
    custom_dev: "bg-orange-100 text-orange-800",
    not_applicable: "bg-gray-100 text-gray-600",
  };
  return colors[status] || "bg-gray-100 text-gray-600";
}

export function complianceStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    fully_compliant: "Fully Compliant",
    partially_compliant: "Partially Compliant",
    configurable: "Configurable",
    custom_dev: "Custom Development",
    not_applicable: "N/A",
  };
  return labels[status] || status;
}

export function priorityColor(priority: string): string {
  const colors: Record<string, string> = {
    high: "bg-red-100 text-red-800",
    medium: "bg-yellow-100 text-yellow-800",
    low: "bg-green-100 text-green-800",
  };
  return colors[priority] || "bg-gray-100 text-gray-600";
}

export function statusColor(status: string): string {
  const colors: Record<string, string> = {
    draft: "bg-gray-100 text-gray-700",
    in_progress: "bg-blue-100 text-blue-700",
    review: "bg-purple-100 text-purple-700",
    completed: "bg-green-100 text-green-700",
    archived: "bg-gray-200 text-gray-500",
    uploaded: "bg-gray-100 text-gray-700",
    parsing: "bg-yellow-100 text-yellow-700",
    parsed: "bg-blue-100 text-blue-700",
    extracted: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };
  return colors[status] || "bg-gray-100 text-gray-600";
}
