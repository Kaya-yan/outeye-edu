/**
 * 任务G4 浮动层状态单测：clamp 边界值 / id 生成 / 转义 / 构建-解析百分比往返。
 * 运行：npm run test:floats（node ≥23.6 原生 TS 类型剥离，.mts 不进 tsc 收录）
 */
import {
  buildFloatHtml,
  clampW,
  clampX,
  clampY,
  escapeHtml,
  nextFloatId,
  parseFloatsFromHtml,
  unescapeHtml,
  type VeFloatItem,
} from "../src/components/v2editor/floats.ts";

let fails = 0;
let total = 0;
function check(name: string, cond: boolean) {
  total += 1;
  if (!cond) {
    fails += 1;
    console.error("FAIL", name);
  } else {
    console.log("OK  ", name);
  }
}

// ---- clamp 边界值 ----
check("clampX 负值归 0", clampX(-5, 32) === 0);
check("clampX 超上界归 100-w", clampX(120, 32) === 68);
check("clampX 界内不动", clampX(50, 32) === 50);
check("clampX 宽先钳制（w=120→100）则上界为 0", clampX(90, 120) === 0);
check("clampY 边界与界内", clampY(-1) === 0 && clampY(120) === 100 && clampY(42.5) === 42.5);
check("clampW 下限 4 上限 100", clampW(1) === 4 && clampW(300) === 100);

// ---- id 生成 ----
check("nextFloatId 跳过已用号", nextFloatId(["oe-fl1", "oe-fl3"]) === "oe-fl2");
check("nextFloatId 空表从 1 开始", nextFloatId([]) === "oe-fl1");

// ---- 转义 ----
check("escapeHtml 覆盖五类字符", escapeHtml(`<a href="x">&'`) === "&lt;a href=&quot;x&quot;&gt;&amp;&#39;");
check("unescape 往返", unescapeHtml(escapeHtml('1<2 & "3" > \'4\'')) === '1<2 & "3" > \'4\'');

// ---- 构建 → 解析 百分比往返（三种 kind + 注入防护） ----
const samples: VeFloatItem[] = [
  { id: "oe-fl1", kind: "textbox", section: 2, xPct: 12.5, yPct: 30, wPct: 32, content: '双击<b>编辑</b>"引号" & 符号' },
  { id: "oe-fl2", kind: "note", section: 1, xPct: 0, yPct: 100, wPct: 22, content: "便签内容 <img onerror=alert(1)>" },
  { id: "oe-fl3", kind: "image", section: 3, xPct: 60, yPct: 15.25, wPct: 34, content: "https://example.com/a.png?x=1&y=2" },
];
for (const s of samples) {
  const html = buildFloatHtml(s);
  const parsed = parseFloatsFromHtml(html).find((f) => f.id === s.id);
  check(
    `往返 ${s.kind}：kind/content/百分比一致`,
    !!parsed &&
      parsed.kind === s.kind &&
      parsed.content === s.content &&
      parsed.xPct === clampX(s.xPct, s.wPct) &&
      parsed.yPct === clampY(s.yPct) &&
      parsed.wPct === clampW(s.wPct)
  );
}
check("越界坐标构建即钳制（x=120 只产出合法 HTML）", parseFloatsFromHtml(buildFloatHtml({ ...samples[0], xPct: 120 }))[0].xPct === 68);
check("note 文本已转义（无裸 <img 注入）", !buildFloatHtml(samples[1]).includes("<img onerror"));
check("data-float 标记齐全", samples.every((s) => buildFloatHtml(s).includes('data-float="1"')));
check("HTML 不承载节号（解析 section 恒 0）", parseFloatsFromHtml(buildFloatHtml(samples[0]))[0].section === 0);

// ---- 二次构建稳定（解析结果再构建应逐字节一致） ----
const once = buildFloatHtml(samples[0]);
const twice = buildFloatHtml(parseFloatsFromHtml(once)[0]);
check("二次构建字节级稳定", once === twice);

console.log(fails ? `\nFAILED ${fails}/${total}` : `\nALL CLEAN (${total})`);
process.exit(fails ? 1 : 0);
