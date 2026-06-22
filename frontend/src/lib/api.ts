"use client";

const API_BASE = "/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export async function apiRequest(
  method: string,
  path: string,
  data?: unknown,
  options?: RequestInit
): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: data ? JSON.stringify(data) : undefined,
    ...options,
  });

  if (res.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "/login";
    throw new Error("未授权，请重新登录");
  }

  return res;
}

export async function apiGet<T = unknown>(path: string): Promise<T> {
  const res = await apiRequest("GET", path);
  if (!res.ok) throw new Error(`请求失败: ${res.status}`);
  return res.json();
}

export async function apiPost<T = unknown>(path: string, data?: unknown): Promise<T> {
  const res = await apiRequest("POST", path, data);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `请求失败: ${res.status}`);
  }
  return res.json();
}

export async function apiPut<T = unknown>(path: string, data?: unknown): Promise<T> {
  const res = await apiRequest("PUT", path, data);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `请求失败: ${res.status}`);
  }
  return res.json();
}

export async function apiDelete<T = unknown>(path: string): Promise<T> {
  const res = await apiRequest("DELETE", path);
  if (!res.ok) throw new Error(`请求失败: ${res.status}`);
  return res.json();
}

export async function apiUpload<T = unknown>(path: string, formData: FormData): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  // 不设置 Content-Type，让浏览器自动设置 multipart/form-data boundary

  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (res.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "/login";
    throw new Error("未授权，请重新登录");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `请求失败: ${res.status}`);
  }

  return res.json();
}
