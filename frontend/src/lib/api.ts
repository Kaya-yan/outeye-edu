"use client";

const API_BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

// 按状态码把错误归为三类，给老师可理解的提示
function makeApiError(res: Response, body: unknown, path?: string): ApiError {
  const rawDetail = (body as { detail?: unknown; message?: unknown })?.detail
    ?? (body as { message?: unknown })?.message;
  const detail = typeof rawDetail === "string" ? rawDetail : undefined;

  if (res.status === 401 || res.status === 403) {
    // 登录接口的 401 是"邮箱或密码错误"，不是登录态过期
    if (path === "/users/login") {
      return new ApiError("邮箱或密码错误", res.status);
    }
    return new ApiError("登录已过期，请重新登录", res.status);
  }
  if (res.status >= 500) {
    // 透出服务端明确给出的原因（如 503 图片识别未配置）；无意义兜底文案则用通用提示
    const generic = !detail || /^(internal server error)$/i.test(detail);
    return new ApiError(generic ? "服务暂时不可用，请稍后重试" : detail, res.status);
  }
  return new ApiError(detail || `请求失败（${res.status}）`, res.status);
}

function newRequestId(): string {
  const c = typeof crypto !== "undefined" ? crypto : undefined;
  if (c && "randomUUID" in c) return c.randomUUID().slice(0, 12);
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

async function failRequest(res: Response, path: string): Promise<never> {
  const body = await res.json().catch(() => ({}));
  const rid = res.headers.get("X-Request-ID");
  console.error(
    `[api] ${res.status} ${path}${rid ? ` rid=${rid}` : ""}`,
    (body as { detail?: unknown })?.detail ?? body ?? ""
  );
  throw makeApiError(res, body, path);
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

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: { ...headers, "X-Request-ID": newRequestId() },
      body: data ? JSON.stringify(data) : undefined,
      ...options,
    });
  } catch {
    throw new ApiError("网络连接失败，请检查网络后重试", 0);
  }

  if (!res.ok) {
    throw await failRequest(res, path);
  }

  return res;
}

export async function apiGet<T = unknown>(path: string): Promise<T> {
  const res = await apiRequest("GET", path);
  return res.json();
}

export async function apiPost<T = unknown>(path: string, data?: unknown): Promise<T> {
  const res = await apiRequest("POST", path, data);
  return res.json();
}

export async function apiPut<T = unknown>(path: string, data?: unknown): Promise<T> {
  const res = await apiRequest("PUT", path, data);
  return res.json();
}

export async function apiDelete<T = unknown>(path: string): Promise<T> {
  const res = await apiRequest("DELETE", path);
  return res.json();
}

export async function apiUpload<T = unknown>(path: string, formData: FormData): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { ...headers, "X-Request-ID": newRequestId() },
      body: formData,
    });
  } catch {
    throw new ApiError("网络连接失败，请检查网络后重试", 0);
  }

  if (!res.ok) {
    throw await failRequest(res, path);
  }

  return res.json();
}
