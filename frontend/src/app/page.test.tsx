/**
 * 工作台首屏 smoke：DeepL 式大标题 + 输入区 + 开始分析按钮可达（SIM-2 契约）
 * 空态契约：输入为空（<20 词）时开始分析按钮禁用
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/",
}));

import Page from "./page";

describe("工作台首屏", () => {
  it("渲染大标题与输入区；空输入时开始分析按钮禁用", async () => {
    render(<Page />);
    expect(screen.getByText("把课文变成一堂好课")).toBeInTheDocument();
    const btn = await screen.findByRole("button", { name: /开始分析/ });
    expect(btn).toBeInTheDocument();
    expect(btn).toBeDisabled(); // wordCount < 20
  });
});
