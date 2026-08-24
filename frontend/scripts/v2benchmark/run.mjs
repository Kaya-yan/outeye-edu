/**
 * V2-lite 编辑器 M4 benchmark harness（无头 jsdom，零 LLM token）。
 *
 * 复用真实产物：src/components/v2editor 的 pickAgent（iframe 内代理）与 patches 引擎，
 * 在 jsdom 中按 postMessage 协议驱动，产出分项成功率：
 *   A 拾取选择器唯一率  B CSS 补丁应用  C 文本补丁  D 图片补丁
 *   E 导出往返保真     F 保存后加载回验（Target Resolver）+ 漂移负控
 *
 * 用法: node scripts/v2benchmark/run.mjs [--samples DIR]
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { JSDOM, VirtualConsole } from "jsdom";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FE_ROOT = path.resolve(__dirname, "..", "..");
const BUILD = path.join(__dirname, "build");
const CHANNEL = "bench-ch-1";

const args = process.argv.slice(2);
let samplesDir = path.join(__dirname, "samples");
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--samples" && args[i + 1]) samplesDir = path.resolve(args[i + 1]);
}

function compileEditorModules() {
  const marker = path.join(BUILD, "pickAgent.js");
  if (fs.existsSync(marker)) return;
  fs.mkdirSync(BUILD, { recursive: true });
  const r = spawnSync(
    "npx",
    [
      "tsc",
      "src/components/v2editor/pickAgent.ts",
      "src/components/v2editor/patches.ts",
      "src/components/v2editor/rpc.ts",
      "--outDir",
      BUILD,
      "--module",
      "commonjs",
      "--target",
      "es2018",
      "--moduleResolution",
      "node",
      "--skipLibCheck",
    ],
    { cwd: FE_ROOT, stdio: "inherit", shell: true }
  );
  if (r.status !== 0) throw new Error("tsc 编译 v2editor 模块失败");
}

compileEditorModules();
const { buildPickAgentScript, injectAgent } = await import(
  pathToFileURL(path.join(BUILD, "pickAgent.js")).href
);
const P = await import(pathToFileURL(path.join(BUILD, "patches.js")).href);

/** 与 pickAgent 内 cssPath 完全同构的宿主实现，用于度量选择器唯一性 */
function cssPathHost(document, el) {
  if (!el || el.nodeType !== 1) return "";
  if (el === document.documentElement) return "html";
  if (el === document.body) return "body";
  const parts = [];
  let e = el;
  let depth = 0;
  while (e && e.nodeType === 1 && depth < 9) {
    let s = e.tagName.toLowerCase();
    let n = 1;
    let p = e.previousElementSibling;
    while (p) {
      if (p.tagName === e.tagName) n++;
      p = p.previousElementSibling;
    }
    let hasSame = false;
    let q = e.nextElementSibling;
    while (q) {
      if (q.tagName === e.tagName) {
        hasSame = true;
        break;
      }
      q = q.nextElementSibling;
    }
    if (n > 1 || hasSame) s += `:nth-of-type(${n})`;
    parts.unshift(s);
    if (e === document.body) break;
    e = e.parentElement;
    depth++;
  }
  return parts.join(" > ");
}

const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

async function createDoc(sourceHtml) {
  const messages = [];
  const injected = injectAgent(sourceHtml, CHANNEL);
  const vc = new VirtualConsole();
  const dom = new JSDOM(injected, {
    runScripts: "dangerously",
    pretendToBeVisual: true,
    url: "http://bench.local/",
    virtualConsole: vc,
    beforeParse(window) {
      window.addEventListener("message", (ev) => {
        const d = ev.data;
        if (d && d.ve === 1 && d.ch === CHANNEL) messages.push(d);
      });
    },
  });
  const send = (type, payload) =>
    dom.window.postMessage({ ve: 1, ch: CHANNEL, type, payload: payload || {} }, "*");
  // 只等待「调用之后」新到达的消息，避免捞到上一轮同名消息导致抢跑
  const waitMsg = async (type, timeout = 3000) => {
    const baseline = messages.length;
    const t0 = Date.now();
    while (Date.now() - t0 < timeout) {
      for (let i = baseline; i < messages.length; i++) {
        if (messages[i].type === type) return messages[i].payload;
      }
      await sleep(5);
    }
    return null;
  };
  return { dom, messages, send, waitMsg };
}

function candidatesOf(document) {
  const out = [];
  const all = document.querySelectorAll("*");
  for (const el of all) {
    if (el.hasAttribute && el.hasAttribute("data-ve-agent")) continue;
    if (el.id === "ve-hover-box" || el.id === "ve-live-patches" || el.id === "ve-freeze") continue;
    const isLeafText = el.childElementCount === 0 && (el.textContent || "").trim().length > 0;
    const isImg = el.tagName === "IMG";
    if (isLeafText || isImg) out.push(el);
  }
  return out;
}

function normText(s) {
  return (s || "").replace(/\s+/g, " ").trim().slice(0, 40);
}

async function benchmarkSample(file, sourceHtml) {
  const result = { file, bytes: Buffer.byteLength(sourceHtml), categories: {} };
  let ctx = null;
  try {
    ctx = await createDoc(sourceHtml);
    const ready = await ctx.waitMsg("ve:ready", 5000);
    if (!ready) throw new Error("agent ve:ready 超时");
    const document = ctx.dom.window.document;

    const spread = (arr, n) => {
      if (arr.length <= n) return arr;
      const step = arr.length / n;
      return Array.from({ length: n }, (_, i) => arr[Math.floor(i * step)]);
    };

    // ---- A. 拾取选择器唯一率 ----
    const leaves = candidatesOf(document);
    let unique = 0;
    for (const el of leaves) {
      const sel = cssPathHost(document, el);
      if (!sel) continue;
      let hits = [];
      try {
        hits = document.querySelectorAll(sel);
      } catch {
        continue;
      }
      if (hits.length === 1 && hits[0] === el) unique++;
    }
    result.categories.pick_unique = {
      ok: unique,
      total: leaves.length,
      rate: leaves.length ? unique / leaves.length : 1,
    };

    // 指纹快照必须在打补丁之前取自底稿（真实流程在拾取时取原始指纹）
    const verifyItems = spread(leaves, 12).map((el, i) => ({
      id: `v${i}`,
      selector: cssPathHost(document, el),
      tag: el.tagName.toLowerCase(),
      childCount: el.childElementCount,
      text: normText(el.textContent),
    }));

    // 先选中一个目标，使后续 applyAll 有 ve:rect 回执
    const first = leaves[0];
    if (first) {
      ctx.send("ve:pick:goto", { selector: cssPathHost(document, first) });
      const picked = await ctx.waitMsg("ve:pick");
      if (!picked) throw new Error("ve:pick:goto 无回执");
    }

    // ---- B. CSS 补丁 ----
    const cssTargets = spread(leaves.filter((e) => e.tagName !== "IMG"), 10);
    const cssPatches = cssTargets.map((el, i) => ({
      id: P.patchId(cssPathHost(document, el), "css", "font-size"),
      kind: "css",
      selector: cssPathHost(document, el),
      label: "bench",
      prop: "font-size",
      value: `${13 + i}px`,
      fingerprint: null,
    }));
    const css = P.buildPatchCss(cssPatches);
    ctx.send("ve:patches:applyAll", { css, patches: [] });
    await ctx.waitMsg("ve:rect");
    const liveStyle = document.getElementById("ve-live-patches");
    const cssOk =
      !!liveStyle &&
      cssPatches.every((p) => liveStyle.textContent.includes(p.selector) && liveStyle.textContent.includes(p.value));
    result.categories.patch_css = { ok: cssOk ? 1 : 0, total: 1, rate: cssOk ? 1 : 0 };

    // ---- C. 文本补丁 ----
    const textTargets = spread(leaves.filter((e) => e.tagName !== "IMG" && (e.textContent || "").trim()), 8);
    const textPatches = textTargets.map((el, i) => ({
      id: P.patchId(cssPathHost(document, el), "text"),
      kind: "text",
      selector: cssPathHost(document, el),
      label: "bench",
      newText: `BENCH-TEXT-${i}`,
      fingerprint: null,
    }));
    ctx.send("ve:patches:applyAll", { css, patches: textPatches });
    await ctx.waitMsg("ve:rect");
    let textOk = 0;
    for (const p of textPatches) {
      let el = null;
      try {
        el = document.querySelector(p.selector);
      } catch {}
      if (el && el.childElementCount === 0 && el.textContent === p.newText) textOk++;
    }
    result.categories.patch_text = {
      ok: textOk,
      total: textPatches.length,
      rate: textPatches.length ? textOk / textPatches.length : 1,
    };

    // ---- D. 图片补丁 ----
    const imgs = [...document.querySelectorAll("img")];
    const imgPatches = imgs.map((el, i) => ({
      id: P.patchId(cssPathHost(document, el), "image"),
      kind: "image",
      selector: cssPathHost(document, el),
      label: "bench",
      newSrc: `https://bench.local/img-${i}.png`,
      fingerprint: null,
    }));
    if (imgPatches.length) {
      ctx.send("ve:patches:applyAll", { css, patches: [...textPatches, ...imgPatches] });
      await ctx.waitMsg("ve:rect");
    }
    let imgOk = 0;
    for (const p of imgPatches) {
      let el = null;
      try {
        el = document.querySelector(p.selector);
      } catch {}
      if (el && el.tagName === "IMG" && el.getAttribute("src") === p.newSrc) imgOk++;
    }
    result.categories.patch_image = {
      ok: imgOk,
      total: imgPatches.length,
      rate: imgPatches.length ? imgOk / imgPatches.length : null,
      na: imgPatches.length === 0,
    };

    // ---- G. 插入组件补丁（幂等重放 + 撤销清除） ----
    const insertTarget = leaves[0];
    const insertPatch = {
      id: "bench-insert-1",
      kind: "insert",
      selector: cssPathHost(document, insertTarget),
      label: "bench insert",
      position: "after",
      html: '<div style="padding:8px;background:#eef">BENCH COMPONENT</div>',
      fingerprint: null,
    };
    const baseDom = [...textPatches, ...imgPatches];
    ctx.send("ve:patches:applyAll", { css, patches: [...baseDom, insertPatch] });
    await ctx.waitMsg("ve:rect");
    ctx.send("ve:patches:applyAll", { css, patches: [...baseDom, insertPatch] });
    await ctx.waitMsg("ve:rect");
    const wrappers = document.querySelectorAll('[data-ve-insert="bench-insert-1"]');
    const insertOnce = wrappers.length === 1;
    const insertPosOk =
      insertOnce && wrappers[0].previousElementSibling === insertTarget && wrappers[0].textContent.includes("BENCH COMPONENT");
    // 撤销（补丁列表去掉 insert）应清除已插入节点
    ctx.send("ve:patches:applyAll", { css, patches: baseDom });
    await ctx.waitMsg("ve:rect");
    const insertGone = document.querySelectorAll('[data-ve-insert="bench-insert-1"]').length === 0;
    const insertOk = insertOnce && insertPosOk && insertGone;
    result.categories.patch_insert = { ok: insertOk ? 1 : 0, total: 1, rate: insertOk ? 1 : 0 };

    // ---- E. 导出往返保真（含 insert 补丁重新应用） ----
    ctx.send("ve:patches:applyAll", { css, patches: [...baseDom, insertPatch] });
    await ctx.waitMsg("ve:rect");
    const beforeExportCount = document.querySelectorAll("*").length;
    ctx.send("ve:export", { css });
    const exportResult = await ctx.waitMsg("ve:export:result");
    let exportOk = true;
    const exportNotes = [];
    if (!exportResult || !exportResult.html) {
      exportOk = false;
      exportNotes.push("ve:export:result 缺失");
    } else {
      const vdom = new JSDOM(exportResult.html);
      const vdoc = vdom.window.document;
      if (!vdoc.getElementById("ve-export-patches")) {
        exportOk = false;
        exportNotes.push("缺少 #ve-export-patches");
      } else if (!vdoc.getElementById("ve-export-patches").textContent.includes("font-size")) {
        exportOk = false;
        exportNotes.push("补丁样式内容缺失");
      }
      // insert 的 wrapper 会位移兄弟 DIV 的 nth-of-type，故用唯一标记串断言导出内容而非陈旧选择器
      for (const p of textPatches) {
        if (!exportResult.html.includes(p.newText)) {
          exportOk = false;
          exportNotes.push(`文本补丁未导出: ${p.newText}`);
        }
      }
      for (const p of imgPatches) {
        if (!exportResult.html.includes(p.newSrc)) {
          exportOk = false;
          exportNotes.push(`图片补丁未导出: ${p.newSrc}`);
        }
      }
      if (vdoc.querySelector("[data-ve-agent],[contenteditable],#ve-hover-box,#ve-live-patches")) {
        exportOk = false;
        exportNotes.push("导出残留编辑器痕迹");
      }
      if (vdoc.querySelectorAll('[data-ve-insert="bench-insert-1"]').length !== 1) {
        exportOk = false;
        exportNotes.push("插入组件未随导出保留");
      }
      const afterCount = vdoc.querySelectorAll("*").length;
      if (Math.abs(afterCount - beforeExportCount) > 2) {
        exportOk = false;
        exportNotes.push(`元素数漂移 ${beforeExportCount}->${afterCount}`);
      }
      // css-only 纯字符串往返（保存为版本后重进剥离底稿）
      const injectedRound = P.injectExportStyle(sourceHtml, css);
      if (P.stripExportStyle(injectedRound) !== sourceHtml) {
        exportOk = false;
        exportNotes.push("inject/strip 字符串往返不等");
      }
    }
    result.categories.export_roundtrip = { ok: exportOk ? 1 : 0, total: 1, rate: exportOk ? 1 : 0, notes: exportNotes };

    ctx.dom.window.close();
    ctx = null;

    // ---- F. 加载回验（Target Resolver）+ 漂移负控 ----
    const fresh1 = await createDoc(sourceHtml);
    fresh1.send("ve:verify", { items: verifyItems });
    const vr1 = await fresh1.waitMsg("ve:verify:result");
    fresh1.dom.window.close();
    let verifyOk = 0;
    if (vr1 && Array.isArray(vr1.results)) {
      for (const r of vr1.results) if (r.ok) verifyOk++;
    }
    result.categories.reload_verify = {
      ok: verifyOk,
      total: verifyItems.length,
      rate: verifyItems.length ? verifyOk / verifyItems.length : 1,
    };

    const driftIdx = verifyItems.reduce((acc, it, i) => (it.tag !== "img" ? i : acc), -1);
    let driftDetected = false;
    if (driftIdx >= 0) {
      const fresh2 = await createDoc(sourceHtml);
      const driftEl = fresh2.dom.window.document.querySelector(verifyItems[driftIdx].selector);
      if (driftEl) driftEl.textContent = "DRIFTED CONTENT BY BENCHMARK";
      fresh2.send("ve:verify", { items: verifyItems });
      const vr2 = await fresh2.waitMsg("ve:verify:result");
      if (vr2 && Array.isArray(vr2.results)) {
        const hit = vr2.results.find((r) => r.id === verifyItems[driftIdx].id);
        driftDetected = !!hit && !hit.ok && !!hit.reason;
      }
      fresh2.dom.window.close();
    }
    result.categories.drift_detect = { ok: driftDetected ? 1 : 0, total: 1, rate: driftDetected ? 1 : 0 };

    // 保存后重进：底稿=导出 html 剥离补丁样式（wrapper 已底稿化），insert 重放须幂等
    if (exportResult && exportResult.html) {
      const reloadHtml = P.stripExportStyle(exportResult.html);
      const freshIns = await createDoc(reloadHtml);
      freshIns.send("ve:patches:applyAll", { css, patches: [insertPatch] });
      await freshIns.waitMsg("ve:rect");
      const insCount = freshIns.dom.window.document.querySelectorAll(
        '[data-ve-insert="bench-insert-1"]'
      ).length;
      freshIns.dom.window.close();
      result.categories.reload_replay_insert = { ok: insCount === 1 ? 1 : 0, total: 1, rate: insCount === 1 ? 1 : 0 };
    }
  } catch (err) {
    result.error = String((err && err.message) || err);
  } finally {
    if (ctx) {
      try {
        ctx.dom.window.close();
      } catch {}
    }
  }
  return result;
}

const SYNTHETIC_SAMPLE = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Synthetic Bench</title></head>
<body>
<section data-page="1" data-title="Cover" data-component="cover">
  <div><h1>Unit Benchmark</h1><p>Known-answer sample</p></div>
  <div><img src="cover.png" alt="cover"><span>subtitle text</span></div>
</section>
<section data-page="2" data-title="Lead-in" data-component="import">
  <div><p>First paragraph of lead-in activity.</p><p>Second paragraph of lead-in activity.</p></div>
  <ul><li>item one</li><li>item two</li><li>item three</li></ul>
  <img src="leadin.png" alt="photo">
</section>
<section data-page="3" data-title="Reading" data-component="content">
  <div class="col"><p>Column A text.</p></div>
  <div class="col"><p>Column B text.</p></div>
  <table><tr><td>r1c1</td><td>r1c2</td></tr><tr><td>r2c1</td><td>r2c2</td></tr></table>
</section>
</body></html>`;

async function main() {
  if (!fs.existsSync(samplesDir)) {
    console.error(`样本目录不存在: ${samplesDir}`);
    console.error("先生成样本: backend venv python scripts/generate_benchmark_samples.py");
    process.exit(1);
  }
  const files = fs
    .readdirSync(samplesDir)
    .filter((f) => f.endsWith(".html"))
    .sort();
  if (files.length === 0) {
    console.error("样本目录为空");
    process.exit(1);
  }
  console.log(`V2 benchmark：${files.length} 个样本（jsdom 无头）\n`);

  const agg = {};
  const rows = [];
  const sampleList = [...files.map((f) => ({ name: f, html: () => fs.readFileSync(path.join(samplesDir, f), "utf-8") })), { name: "synthetic-known-answer", html: () => SYNTHETIC_SAMPLE }];
  for (const item of sampleList) {
    const f = item.name;
    const html = item.html();
    const r = await benchmarkSample(f, html);
    rows.push(r);
    const parts = Object.entries(r.categories).map(([k, v]) => `${k}=${v.ok}/${v.total}`);
    console.log(`  ${f.padEnd(40)} ${r.error ? "ERROR: " + r.error : parts.join("  ")}`);
    if (!r.error) {
      for (const [k, v] of Object.entries(r.categories)) {
        if (!agg[k]) agg[k] = { ok: 0, total: 0, naCount: 0 };
        if (v.total === 0 && v.na) {
          agg[k].naCount++;
          continue;
        }
        agg[k].ok += v.ok;
        agg[k].total += v.total;
      }
    }
  }

  console.log("\n==== 分项汇总 ====");
  const summary = {};
  for (const [k, v] of Object.entries(agg)) {
    if (v.total === 0) {
      summary[k] = { rate: null, note: `全部样本 N/A (${v.naCount})` };
      console.log(`  ${k.padEnd(18)} N/A（样本均无此元素）`);
      continue;
    }
    const rate = v.ok / v.total;
    summary[k] = { ok: v.ok, total: v.total, rate: Number(rate.toFixed(4)), naSamples: v.naCount };
    console.log(`  ${k.padEnd(18)} ${v.ok}/${v.total} = ${(rate * 100).toFixed(1)}%${v.naCount ? `（${v.naCount} 样本 N/A）` : ""}`);
  }

  const report = {
    generated_at: new Date().toISOString(),
    samples_dir: samplesDir,
    sample_count: files.length,
    summary,
    rows,
  };
  const reportPath = path.join(__dirname, "report.json");
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`\n报告已写入 ${reportPath}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
