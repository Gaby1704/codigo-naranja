import type { Audit, AuthResponse, ColumnMapping, Dashboard, UploadPreview } from "../../../packages/shared/types"
import type { Filters } from "./lib/shared"

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set("X-Codigo-Naranja", "1")
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  const response = await fetch(path, { ...init, headers, credentials: "include" })
  if (response.status === 204) return undefined as T
  const payload = (await response.json().catch(() => ({}))) as { detail?: unknown }
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "No se pudo completar la solicitud."
    throw new ApiError(response.status, detail)
  }
  return payload as T
}

export function getMe() {
  return api<AuthResponse>("/api/auth/me")
}

export function login(email: string, password: string) {
  return api<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
}

export function logout() {
  return api<void>("/api/auth/logout", { method: "POST" })
}

export function getDashboard(filters: Filters, signal?: AbortSignal) {
  const params = new URLSearchParams(filters)
  return api<Dashboard>(`/api/dashboard?${params.toString()}`, { signal })
}

export function uploadDataset(file: File) {
  const body = new FormData()
  body.append("file", file)
  return api<UploadPreview>("/api/datasets/uploads", { method: "POST", body })
}

export function changeSheet(uploadId: string, sheet: string) {
  return api<UploadPreview>(`/api/datasets/uploads/${uploadId}/sheet`, {
    method: "POST",
    body: JSON.stringify({ sheet }),
  })
}

export function applyDataset(uploadId: string, sheet: string, mapping: ColumnMapping) {
  return api<{ audit: Audit; fileName: string }>(`/api/datasets/uploads/${uploadId}/apply`, {
    method: "POST",
    body: JSON.stringify({ sheet, mapping }),
  })
}

export async function downloadTemplate() {
  const response = await fetch("/api/datasets/template", {
    credentials: "include",
    headers: { "X-Codigo-Naranja": "1" },
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: unknown }
    const detail = typeof payload.detail === "string" ? payload.detail : "No se pudo descargar la plantilla."
    throw new ApiError(response.status, detail)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = "plantilla-smet.xlsx"
  link.click()
  URL.revokeObjectURL(url)
}
