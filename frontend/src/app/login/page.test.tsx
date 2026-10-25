/**
 * 登录页 smoke：表单字段与提交按钮可达
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/login",
}));

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ user: null, login: vi.fn(), logout: vi.fn(), register: vi.fn() }),
}));

import LoginPage from "./page";

describe("登录页", () => {
  it("渲染邮箱/密码输入与登录按钮", () => {
    render(<LoginPage />);
    expect(screen.getByText("登录账户")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("your@email.com")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("请输入密码")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^登录$/ })).toBeInTheDocument();
  });
});
