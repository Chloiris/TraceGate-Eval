import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

test("loads authenticated real service and benchmark state", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "部分能力尚未配置" })).toBeVisible();
  await expect(page.getByText("GitHub 尚未连接", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("模型尚未配置", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("工作区活动")).toBeVisible();
  await expect(page.getByText("1", { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: /设置.*本地偏好与宿主/ }).click();
  await page.getByRole("link", { name: /诊断.*版本、指标与队列/ }).click();
  await expect(page.getByRole("heading", { name: "诊断", level: 2 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "最近持久化指标" })).toBeVisible();
  await expect(page.getByText("not configured", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: /评测中心.*真实基准与声明评测/ }).click();
  await expect(page.getByRole("heading", { name: "TraceGate v0.2-alpha hard real-data mini benchmark" })).toBeVisible();
  await expect(page.getByText("160 ClaimBench runs")).toBeVisible();
  await expect(page.getByText("dataset version / sha256", { exact: false })).toBeVisible();
  await page.screenshot({ path: "docs/screenshots/p1-eval-center-macos.png", fullPage: true });
});

test("indexes an explicitly enrolled repository through the UI", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /仓库.*同步与增量索引/ }).click();
  await expect(page.getByRole("heading", { name: "受控仓库" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "tracegate-e2e/fixture" })).toBeVisible();

  await page.getByLabel("GitHub 仓库（owner/name）").fill("tracegate-e2e/second");
  // The browser cannot discover a host path. Read the already enrolled path
  // from the rendered metadata and use that explicit user-visible value.
  const workspace = await page.locator(".repository-card .metadata-grid dd").first().getAttribute("title");
  expect(workspace).toBeTruthy();
  await page.getByLabel("本地工作区绝对路径（可选）").fill(workspace ?? "");
  await page.getByRole("button", { name: "添加仓库" }).click();
  await expect(page.getByRole("heading", { name: "tracegate-e2e/second" })).toBeVisible();
  const secondCard = page.locator(".repository-card", { hasText: "tracegate-e2e/second" });
  await secondCard.getByRole("button", { name: "重新索引" }).click();
  await expect(secondCard.getByText("尚未索引")).toHaveCount(0);
  await secondCard.getByRole("button", { name: "Repository Map" }).click();
  await expect(page.getByRole("heading", { name: "Repository Map" })).toBeVisible();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "导出 PNG" }).click(),
  ]);
  expect(download.suggestedFilename()).toBe("tracegate-repository-map.png");
  const downloadPath = await download.path();
  expect(downloadPath).toBeTruthy();
  const bytes = await readFile(downloadPath ?? "");
  expect([...bytes.subarray(0, 8)]).toEqual([137, 80, 78, 71, 13, 10, 26, 10]);
});

test("navigates PR diff, Review Map, Finding and Agent Trace", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.goto("/");
  await page.getByRole("button", { name: /审查队列.*拉取请求审查与分析/ }).click();
  await expect(page.getByText("#17 · Double the calculated total")).toBeVisible();
  await page.getByText("#17 · Double the calculated total").click();
  await page.waitForTimeout(250);
  expect(pageErrors).toEqual([]);
  await expect(page.getByRole("heading", { name: "Double the calculated total" })).toBeVisible();

  await page.getByRole("tab", { name: "Files & Diff" }).click();
  await expect(page.getByRole("button", { name: /^M service\.py$/ })).toBeVisible();
  await expect(page.locator(".monaco-diff-editor")).toBeVisible();
  await page.screenshot({ path: "docs/screenshots/p1-pr-diff-macos.png", fullPage: true });

  await page.getByRole("tab", { name: "Review Map" }).click();
  await expect(page.getByText("Impact depth uses exact Head-side changed lines", { exact: false })).toBeVisible();
  await expect(page.locator(".review-flow .react-flow")).toBeVisible();
  await page.screenshot({ path: "docs/screenshots/p1-review-map-macos.png", fullPage: true });

  await page.getByRole("tab", { name: "Change Tour" }).click();
  await expect(page.getByText("Single changed indexed code file", { exact: false })).toBeVisible();
  await expect(page.getByText("相关符号", { exact: true })).toBeVisible();
  await expect(page.getByText("建议检查点", { exact: true })).toBeVisible();

  await page.getByRole("tab", { name: "Findings" }).click();
  await expect(page.getByRole("heading", { name: "Return value semantics changed" })).toBeVisible();
  await page.getByRole("button", { name: "service.py:2" }).click();
  await expect(page.getByRole("tab", { name: "Files & Diff", selected: true })).toBeVisible();

  await page.getByRole("tab", { name: "Agent Trace" }).click();
  await expect(page.getByText("Repository Retriever", { exact: true })).toBeVisible();
  await expect(page.getByText("read_file", { exact: false })).toBeVisible();
});

test("shows explicit retry failure and actual registry permissions", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /运行记录.*节点与工具轨迹/ }).click();
  await expect(page.getByText("verification_failed", { exact: false })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Agent Evidence Graph" })).toBeVisible();
  await expect(page.locator(".evidence-flow .react-flow")).toBeVisible();
  await page.getByRole("button", { name: "重试" }).click();
  await expect(page.getByText("操作失败: Model provider and model name are not configured", { exact: false })).toBeVisible();

  await page.getByRole("button", { name: /组件注册.*智能体与工具/ }).click();
  await expect(page.getByRole("heading", { name: "Planner" })).toBeVisible();
  const plannerCard = page.locator(".registry-card", { hasText: "Planner" });
  await plannerCard.getByRole("button", { name: "停用 Agent" }).click();
  await expect(plannerCard.getByRole("button", { name: "启用 Agent" })).toBeVisible();
  await plannerCard.getByRole("button", { name: "启用 Agent" }).click();
  await expect(plannerCard.getByRole("button", { name: "停用 Agent" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "apply_patch" })).toBeVisible();
  const patchCard = page.locator(".registry-card", { hasText: "apply_patch" });
  await expect(patchCard.getByText("confirmation only", { exact: true })).toBeVisible();
  await expect(patchCard.getByRole("button", { name: "必须逐次确认" })).toBeDisabled();
  await expect(page.getByText("WRITE_CONFIRMATION", { exact: true })).toBeVisible();
  await page.screenshot({ path: "docs/screenshots/p1-registry-macos.png", fullPage: true });
});
