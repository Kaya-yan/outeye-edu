/**
 * 历史记录页 smoke：空数据时呈现空态引导（fetch 已在 setup.ts 全局 mock）
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/history",
}));

import HistoryPage from "./page";

describe("历史记录页", () => {
  it("无记录时渲染空态", async () => {
    render(<HistoryPage />);
    expect(await screen.findByText("还没有记录")).toBeInTheDocument();
  });
});
