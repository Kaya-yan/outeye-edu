import "@testing-library/jest-dom/vitest";

// 三件套 smoke 测试统一在这里 mock 网络层：挂载期的 ocr-status / projects 等请求不打真实后端
import { vi } from "vitest";

vi.stubGlobal(
  "fetch",
  vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body: unknown = url.includes("ocr-status")
      ? { available: false }
      : url.includes("/projects")
        ? []
        : { ok: true };
    return {
      ok: true,
      status: 200,
      json: async () => body,
      blob: async () => new Blob(),
      text: async () => "",
    } as Response;
  })
);
