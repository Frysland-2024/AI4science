import fs from "node:fs/promises";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const TMP = "E:/AI4science/.codex_tmp/scientific_evidence_deck_20260828";
const RENDER_DIR = `${TMP}/round5_rendered`;
const FINAL = "E:/AI4science/outputs/XRD_导师汇报_第五轮_方案A方法页_3页_2026-08-28.pptx";
const SPECTRUM_CSV = "E:/AI4science/xrd_robustness/data/real_xrd/rruff371/spectra_10_80_step_002/R040017_Cassiterite.csv";
const PANEL_BASE = "E:/AI4science/xrd_robustness/outputs/public_simulated_test/panel_cache/seed_20260721/level0.npy";
const PANEL_SHIFT = "E:/AI4science/xrd_robustness/outputs/public_simulated_test/panel_cache/seed_20260721/ood_shift_positive.npy";
const PANEL_NOISE = "E:/AI4science/xrd_robustness/outputs/public_simulated_test/panel_cache/seed_20260721/ood_noise.npy";
const PANEL_VIEW_A = "E:/AI4science/xrd_robustness/outputs/public_simulated_test/panel_cache/seed_20260721/in_range.npy";
const PANEL_VIEW_B = "E:/AI4science/xrd_robustness/outputs/public_simulated_test/panel_cache/seed_20260722/in_range.npy";
const PANEL_INDEX = "E:/AI4science/xrd_robustness/outputs/public_simulated_test/panel_cache/index.json";
const PANEL_ROW = 109;

const W = 1280;
const H = 720;
const FONT = "Microsoft YaHei";
const NAVY = "#143A63";
const INK = "#17222F";
const MUTED = "#657384";
const RULE = "#D9E0E8";
const BLUE = "#5F8FC4";
const BLUE_DARK = "#285F97";
const ORANGE = "#E77A25";
const GREEN = "#2A8F63";
const PALE_BLUE = "#EAF2F9";
const PALE_ORANGE = "#FFF1E6";
const LIGHT = "#F6F8FA";

const presentation = Presentation.create({ slideSize: { width: W, height: H } });

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()));
}

function addText(slide, text, left, top, width, height, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name: options.name,
    position: { left, top, width, height },
    fill: options.fill ?? "none",
    line: options.line ?? { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: options.typeface ?? FONT,
    fontSize: options.fontSize ?? 20,
    bold: options.bold ?? false,
    color: options.color ?? INK,
    alignment: options.align ?? "left",
    verticalAlignment: options.valign ?? "top",
    lineSpacing: options.lineSpacing ?? 1.06,
    wrap: "square",
    autoFit: "none",
    insets: options.insets ?? { top: 0, right: 0, bottom: 0, left: 0 },
  };
  return shape;
}

function addRect(slide, left, top, width, height, fill, options = {}) {
  return slide.shapes.add({
    geometry: options.geometry ?? "rect",
    name: options.name,
    position: { left, top, width, height },
    fill,
    line: options.line ?? { style: "solid", fill: options.lineFill ?? "none", width: options.lineWidth ?? 0 },
    borderRadius: options.borderRadius,
  });
}

function addLine(slide, left, top, width, height = 0, color = RULE, lineWidth = 1) {
  return slide.shapes.add({
    geometry: "line",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: color, width: lineWidth },
  });
}

function addArrow(slide, left, top, width, height = 14, fill = NAVY) {
  return addRect(slide, left, top, width, height, fill, { geometry: "rightArrow" });
}

function addHeader(slide, title, page, options = {}) {
  addText(slide, title, 58, 30, 1128, 58, {
    fontSize: options.fontSize ?? 40,
    bold: true,
    color: NAVY,
    name: `slide-${page}-title`,
  });
  addText(slide, `${String(page).padStart(2, "0")} / 03`, 1176, 40, 48, 24, {
    fontSize: 14,
    color: MUTED,
    align: "right",
  });
  addLine(slide, 58, 102, 1166, 0, NAVY, 1.5);
}

function addFooter(slide, text = "PXRD 测量等价性与鲁棒分类") {
  addText(slide, text, 58, 682, 600, 20, { fontSize: 13, color: MUTED });
}

function addNotes(slide, sources, note = "") {
  const lines = [];
  if (note) lines.push(note, "");
  lines.push("[Sources]", ...sources.map((s) => `- ${s}`));
  slide.speakerNotes.textFrame.setText(lines.join("\n"));
}

function clamp(v, lo = 0, hi = 1) {
  return Math.max(lo, Math.min(hi, v));
}

async function loadSpectrum(path) {
  const raw = await fs.readFile(path, "utf8");
  const rows = raw.trim().split(/\r?\n/).slice(1);
  const x = [];
  const y = [];
  for (const row of rows) {
    const [xs, ys] = row.split(",");
    const xv = Number(xs);
    const yv = Number(ys);
    if (Number.isFinite(xv) && Number.isFinite(yv)) {
      x.push(xv);
      y.push(yv);
    }
  }
  const maxY = Math.max(...y);
  return { x, y: y.map((v) => v / maxY) };
}

async function loadNpyRow(path, row, cols = 3501) {
  const buffer = await fs.readFile(path);
  if (buffer.toString("latin1", 1, 6) !== "NUMPY") throw new Error(`Invalid NPY file: ${path}`);
  const major = buffer[6];
  let dataOffset;
  if (major === 1) dataOffset = 10 + buffer.readUInt16LE(8);
  else if (major === 2 || major === 3) dataOffset = 12 + buffer.readUInt32LE(8);
  else throw new Error(`Unsupported NPY version ${major}: ${path}`);
  const rowOffset = dataOffset + row * cols * 4;
  const values = Array.from({ length: cols }, (_, i) => buffer.readFloatLE(rowOffset + i * 4));
  const max = Math.max(...values);
  return values.map((v) => v / max);
}

function xGrid(cols = 3501) {
  return Array.from({ length: cols }, (_, i) => 10 + 0.02 * i);
}

function interpolate(x, y, target) {
  if (target <= x[0] || target >= x[x.length - 1]) return 0;
  let lo = 0;
  let hi = x.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (x[mid] <= target) lo = mid;
    else hi = mid;
  }
  const t = (target - x[lo]) / (x[hi] - x[lo]);
  return y[lo] * (1 - t) + y[hi] * t;
}

function shiftedSeries(x, y, shiftDeg) {
  return x.map((v) => interpolate(x, y, v - shiftDeg));
}

function noisySeries(y, seed = 20260828, amplitude = 0.035) {
  let state = seed >>> 0;
  const rand = () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 4294967296;
  };
  return y.map((v) => clamp(v + amplitude * ((rand() + rand() + rand()) / 3 - 0.5) * 2, 0, 1.05));
}

function smoothSeries(y, radius = 2) {
  return y.map((_, i) => {
    let s = 0;
    let w = 0;
    for (let j = -radius; j <= radius; j++) {
      const idx = i + j;
      if (idx >= 0 && idx < y.length) {
        const weight = radius + 1 - Math.abs(j);
        s += y[idx] * weight;
        w += weight;
      }
    }
    return s / w;
  });
}

function downsampleMax(x, y, bucketSize = 12) {
  const xo = [];
  const yo = [];
  for (let start = 0; start < x.length; start += bucketSize) {
    const end = Math.min(x.length, start + bucketSize);
    let best = start;
    for (let i = start + 1; i < end; i++) if (y[i] > y[best]) best = i;
    xo.push(x[best]);
    yo.push(y[best]);
  }
  return { x: xo, y: yo };
}

function cropSeries(x, y, minX, maxX) {
  const xo = [];
  const yo = [];
  for (let i = 0; i < x.length; i++) {
    if (x[i] >= minX && x[i] <= maxX) {
      xo.push(x[i]);
      yo.push(y[i]);
    }
  }
  return { x: xo, y: yo };
}

function spectrumChart(slide, position, seriesDefs, options = {}) {
  const series = seriesDefs.map((s) => {
    const cropped = cropSeries(s.x, s.y, options.xMin ?? 10, options.xMax ?? 80);
    const d = downsampleMax(cropped.x, cropped.y, options.bucketSize ?? 12);
    return {
      name: s.name,
      xValues: d.x,
      values: d.y,
      line: { style: s.dashed ? "dashed" : "solid", fill: s.color, width: s.width ?? 2.4 },
      marker: { symbol: "none", size: 2 },
    };
  });
  return slide.charts.add("scatter", {
    position,
    series,
    scatterOptions: { style: "line", varyColors: false },
    hasLegend: options.hasLegend ?? false,
    legend: options.hasLegend ? {
      position: options.legendPosition ?? "bottom",
      overlay: false,
      textStyle: { fontSize: options.legendFontSize ?? 16, fill: INK },
    } : undefined,
    chartFill: "#FFFFFF",
    chartLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    xAxis: {
      visible: options.axes ?? true,
      min: options.xMin ?? 10,
      max: options.xMax ?? 80,
      majorUnit: options.xMajorUnit ?? 10,
      title: options.axes === false ? undefined : { text: "2θ (°)", textStyle: { fontSize: 16, fill: MUTED } },
      textStyle: { fontSize: 14, fill: MUTED },
      line: { style: "solid", fill: RULE, width: 1 },
      majorGridlines: null,
      tickLabelPosition: options.axes === false ? "none" : "nextTo",
    },
    yAxis: {
      visible: options.axes ?? true,
      min: 0,
      max: 1.08,
      majorUnit: 0.25,
      title: options.axes === false ? undefined : { text: "归一化强度", textStyle: { fontSize: 16, fill: MUTED } },
      textStyle: { fontSize: 14, fill: MUTED },
      line: { style: "solid", fill: "#FFFFFF", width: 0 },
      majorGridlines: options.axes === false ? null : { style: "solid", fill: "#E7EBF0", width: 1 },
      tickLabelPosition: options.axes === false ? "none" : "nextTo",
    },
  });
}

function spectrumStrip(slide, position, x, y, color, showXAxis = false) {
  const cropped = cropSeries(x, y, 18, 43);
  const d = downsampleMax(cropped.x, cropped.y, 7);
  return slide.charts.add("scatter", {
    position,
    series: [{
      name: "spectrum",
      xValues: d.x,
      values: d.y,
      line: { style: "solid", fill: color, width: 2.6 },
      marker: { symbol: "none", size: 2 },
    }],
    scatterOptions: { style: "line", varyColors: false },
    hasLegend: false,
    chartFill: "#FFFFFF",
    chartLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    xAxis: {
      visible: showXAxis,
      min: 18,
      max: 43,
      majorUnit: 5,
      title: showXAxis ? { text: "2θ (°)", textStyle: { fontSize: 15, fill: MUTED } } : undefined,
      textStyle: { fontSize: 13, fill: MUTED },
      line: { style: "solid", fill: showXAxis ? RULE : "#FFFFFF", width: showXAxis ? 1 : 0 },
      majorGridlines: null,
      tickLabelPosition: showXAxis ? "nextTo" : "none",
    },
    yAxis: {
      visible: false,
      min: 0,
      max: 1.05,
      majorGridlines: null,
      line: { style: "solid", fill: "#FFFFFF", width: 0 },
      tickLabelPosition: "none",
    },
  });
}

function pairedSeedChart(slide, position, pairs, meanPair, options = {}) {
  const seedColors = ["#B4C5D7", "#9FB7CF", "#CBD6E2", "#A9BED3", "#D4DDE7"];
  const series = pairs.map((pair, i) => ({
    name: `seed ${i + 1}`,
    values: pair,
    line: { style: "solid", fill: seedColors[i], width: 2.3 },
    marker: { symbol: "circle", size: 7 },
    valuesFormatCode: "0.000",
  }));
  series.push({
    name: "均值",
    values: meanPair,
    line: { style: "solid", fill: NAVY, width: 4.5 },
    marker: { symbol: "diamond", size: 10 },
    valuesFormatCode: "0.000",
  });
  return slide.charts.add("line", {
    position,
    categories: ["Dynamic ERM", "JS Consistency"],
    series,
    lineOptions: { grouping: "standard", smooth: false, varyColors: false },
    hasLegend: false,
    chartFill: "#FFFFFF",
    chartLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    xAxis: {
      visible: true,
      textStyle: { fontSize: 18, fill: INK, bold: true },
      line: { style: "solid", fill: RULE, width: 1 },
      majorGridlines: null,
    },
    yAxis: {
      visible: true,
      min: options.min,
      max: options.max,
      majorUnit: options.majorUnit,
      numberFormatCode: "0.00",
      title: { text: "Macro-F1", textStyle: { fontSize: 17, fill: MUTED } },
      textStyle: { fontSize: 15, fill: MUTED },
      line: { style: "solid", fill: "#FFFFFF", width: 0 },
      majorGridlines: { style: "solid", fill: "#E4E9EF", width: 1 },
    },
  });
}

function addProbabilityBars(slide, left, top, label, values, accent) {
  addText(slide, label, left, top, 54, 30, { fontSize: 25, bold: true, color: accent });
  const barLeft = left + 62;
  for (let i = 0; i < values.length; i++) {
    addRect(slide, barLeft, top + i * 20 + 4, 166, 7, "#E3E8EE");
    addRect(slide, barLeft, top + i * 20 + 4, 166 * values[i], 7, accent);
  }
}

const panelX = xGrid();
const base = { x: panelX, y: await loadNpyRow(PANEL_BASE, PANEL_ROW) };
const shifted = await loadNpyRow(PANEL_SHIFT, PANEL_ROW);
const noisy = await loadNpyRow(PANEL_NOISE, PANEL_ROW);
const viewA = await loadNpyRow(PANEL_VIEW_A, PANEL_ROW);
const viewB = await loadNpyRow(PANEL_VIEW_B, PANEL_ROW);
const broadened = smoothSeries(base.y, 4);
const recon = shiftedSeries(smoothSeries(base.y, 1), 0.035).map((v, i) => clamp(v * 0.99 + 0.005 * noisy[i], 0, 1.05));

// Slide 1 — opening hook: state the problem before presenting evidence.
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";

  addText(slide, "让 PXRD 晶系判断不再依赖“怎么测”", 76, 62, 1128, 74, {
    fontSize: 54,
    bold: true,
    color: NAVY,
    align: "center",
  });
  addText(slide, "模拟谱训练出的模型，遇到真实实验条件变化后还能稳定判断晶系吗？", 116, 158, 1048, 42, {
    fontSize: 25,
    color: MUTED,
    align: "center",
  });
  addLine(slide, 178, 222, 924, 0, RULE, 1.2);

  addText(slide, "较理想的谱", 104, 270, 416, 30, {
    fontSize: 22,
    bold: true,
    color: BLUE_DARK,
    align: "center",
  });
  addText(slide, "受测量扰动的谱", 760, 270, 416, 30, {
    fontSize: 22,
    bold: true,
    color: ORANGE,
    align: "center",
  });
  spectrumStrip(slide, { left: 86, top: 312, width: 452, height: 184 }, base.x, base.y, BLUE_DARK, false);
  spectrumStrip(slide, { left: 742, top: 312, width: 452, height: 184 }, base.x, noisy, ORANGE, false);

  addText(slide, "同一晶体", 548, 326, 184, 32, {
    fontSize: 22,
    color: MUTED,
    align: "center",
  });
  addText(slide, "晶系不变", 536, 376, 208, 48, {
    fontSize: 34,
    bold: true,
    color: NAVY,
    align: "center",
  });
  addLine(slide, 548, 446, 184, 0, NAVY, 1.5);

  addText(slide, "阶段性研究汇报 · 2026.08.28", 76, 654, 1128, 24, {
    fontSize: 16,
    color: MUTED,
    align: "center",
  });
  addNotes(slide, [
    PANEL_BASE,
    PANEL_NOISE,
    PANEL_INDEX,
    "E:\\AI4science\\xrd_robustness\\data\\formal_14060\\manifests\\v9_method_transfer_test_seed_20260721.csv",
  ], "左右曲线取自同一 mp-10448 母结构的基准谱与项目已缓存噪声扰动谱，仅作为开篇认知钩子。" );
}

// Slide 2 — physical problem shown with spectra.
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addHeader(slide, "真实问题：同一晶体的谱会随测量条件变化", 2, { fontSize: 40 });

  addText(slide, "理想 / 基准谱", 64, 162, 154, 32, { fontSize: 21, bold: true, color: NAVY });
  addText(slide, "峰移或展宽后的谱", 64, 316, 164, 58, { fontSize: 21, bold: true, color: ORANGE });
  addText(slide, "加背景 / 噪声后的谱", 64, 472, 166, 58, { fontSize: 21, bold: true, color: GREEN });

  spectrumStrip(slide, { left: 230, top: 126, width: 982, height: 128 }, base.x, base.y, NAVY, false);
  spectrumStrip(slide, { left: 230, top: 280, width: 982, height: 128 }, base.x, shifted, ORANGE, false);
  spectrumStrip(slide, { left: 230, top: 434, width: 982, height: 154 }, base.x, noisy, GREEN, true);

  addLine(slide, 230, 264, 982, 0, RULE, 1);
  addLine(slide, 230, 418, 982, 0, RULE, 1);
  addText(slide, "问题：模型能否不把测量条件误认为结构特征？", 218, 632, 844, 38, {
    fontSize: 27,
    bold: true,
    color: NAVY,
    align: "center",
  });
  addNotes(slide, [
    PANEL_BASE,
    PANEL_SHIFT,
    PANEL_NOISE,
    PANEL_INDEX,
    "E:\\AI4science\\xrd_robustness\\data\\formal_14060\\manifests\\v9_method_transfer_test_seed_20260721.csv",
  ], "三条曲线均取 panel_cache 的 row 109，对应同一 mp-10448 母结构；峰移与噪声是项目中已缓存、可复现的测量扰动输出。" );
}

// Slide 3 — exact two-view training mechanism, expressed in plain language.
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addHeader(slide, "同一结构即使测出来不同，模型判断也应一致", 3, { fontSize: 36 });

  // Connectors first, so every line stays behind the scientific content.
  addLine(slide, 640, 151, 0, 22, NAVY, 1.5);
  addLine(slide, 330, 173, 620, 0, NAVY, 1.5);
  addLine(slide, 330, 173, 0, 12, NAVY, 1.5);
  addLine(slide, 950, 173, 0, 12, NAVY, 1.5);
  addRect(slide, 320, 181, 20, 24, NAVY, { geometry: "downArrow" });
  addRect(slide, 940, 181, 20, 24, NAVY, { geometry: "downArrow" });
  addRect(slide, 320, 296, 20, 35, NAVY, { geometry: "downArrow" });
  addRect(slide, 940, 296, 20, 35, NAVY, { geometry: "downArrow" });
  addRect(slide, 490, 374, 22, 42, NAVY, { geometry: "downArrow" });
  addRect(slide, 768, 374, 22, 42, NAVY, { geometry: "downArrow" });

  addText(slide, "同一母结构", 518, 115, 244, 34, { fontSize: 24, bold: true, color: NAVY, align: "center" });

  addText(slide, "扰动谱 A", 165, 178, 330, 28, { fontSize: 20, bold: true, color: BLUE_DARK, align: "center" });
  addText(slide, "扰动谱 B", 785, 178, 330, 28, { fontSize: 20, bold: true, color: ORANGE, align: "center" });
  spectrumChart(slide, { left: 160, top: 202, width: 340, height: 100 }, [
    { name: "view A", x: panelX, y: viewA, color: BLUE_DARK, width: 2.4 },
  ], { axes: false, bucketSize: 7, xMin: 18, xMax: 43, xMajorUnit: 5 });
  spectrumChart(slide, { left: 780, top: 202, width: 340, height: 100 }, [
    { name: "view B", x: panelX, y: viewB, color: ORANGE, width: 2.4 },
  ], { axes: false, bucketSize: 7, xMin: 18, xMax: 43, xMajorUnit: 5 });

  addRect(slide, 260, 331, 760, 43, PALE_BLUE, { geometry: "roundRect", borderRadius: 7, lineFill: NAVY, lineWidth: 1.2 });
  addText(slide, "同一个模型", 410, 340, 460, 26, { fontSize: 22, bold: true, color: NAVY, align: "center" });

  addText(slide, "预测 A   ≈   预测 B", 220, 414, 840, 124, {
    fontSize: 72,
    bold: true,
    color: NAVY,
    align: "center",
    valign: "middle",
  });
  addNotes(slide, [
    "E:\\AI4science\\xrd_robustness\\src\\xrd_robustness\\training\\objectives.py",
    "E:\\AI4science\\xrd_robustness\\src\\xrd_robustness\\online_views.py",
    PANEL_VIEW_A,
    PANEL_VIEW_B,
    PANEL_INDEX,
    "E:\\AI4science\\xrd_robustness\\data\\formal_14060\\manifests\\v9_method_transfer_test_seed_20260721.csv",
    "E:\\AI4science\\xrd_robustness\\data\\formal_14060\\manifests\\v9_method_transfer_test_seed_20260722.csv",
  ]);
}

// Round 5 deliberately stops after the approved three-slide opening sequence.
{
  await fs.mkdir(RENDER_DIR, { recursive: true });
  await fs.mkdir("E:/AI4science/outputs", { recursive: true });
  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const png = await presentation.export({ slide, format: "png", scale: 1 });
    await writeBlob(`${RENDER_DIR}/${stem}.png`, png);
    await writeBlob(`E:/AI4science/outputs/XRD_导师汇报_第五轮_${stem}.png`, png);
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(`${RENDER_DIR}/${stem}.layout.json`, await layout.text());
  }
  await writeBlob(`${RENDER_DIR}/montage.webp`, await presentation.export({ format: "webp", montage: true, scale: 1 }));
  const inspection = await presentation.inspect({ kind: "slide,textbox,shape,chart,notes", maxChars: 20000 });
  await fs.writeFile(`${RENDER_DIR}/inspect.ndjson`, inspection.ndjson);
  const round1Pptx = await PresentationFile.exportPptx(presentation);
  await round1Pptx.save(FINAL);
  console.log(`Wrote ${FINAL}`);
  process.exit(0);
}

// Slide 3 — five paired simulated OOD seeds.
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addHeader(slide, "模拟 OOD：5/5 个 seed 全部提升，平均 +5.46 pp", 3, { fontSize: 40 });
  const pairs = [
    [0.639028974, 0.693876991],
    [0.655334469, 0.716735051],
    [0.657677572, 0.707536534],
    [0.651666815, 0.696743932],
    [0.649975054, 0.711787892],
  ];
  pairedSeedChart(slide, { left: 72, top: 146, width: 860, height: 454 }, pairs, [0.650736577, 0.705336080], {
    min: 0.62,
    max: 0.73,
    majorUnit: 0.02,
  });
  addText(slide, "5 / 5  ↑", 948, 222, 250, 70, { fontSize: 54, bold: true, color: GREEN, align: "center" });
  addText(slide, "每条细线代表一个独立训练 seed", 964, 304, 218, 54, { fontSize: 17, color: MUTED, align: "center", lineSpacing: 1.18 });
  addLine(slide, 972, 384, 206, 0, RULE, 1);
  addText(slide, "均值", 978, 410, 194, 24, { fontSize: 17, color: MUTED, align: "center" });
  addText(slide, "0.6507  →  0.7053", 948, 444, 250, 38, { fontSize: 27, bold: true, color: NAVY, align: "center" });
  addText(slide, "+5.46 pp", 948, 498, 250, 48, { fontSize: 38, bold: true, color: ORANGE, align: "center" });
  addText(slide, "冻结 Test · 单因素 OOD Macro-F1", 72, 624, 860, 28, { fontSize: 17, color: MUTED, align: "center" });
  addFooter(slide);
  addNotes(slide, [
    "E:\\AI4science\\xrd_robustness\\reports\\simulated_test_results.json",
    "E:\\AI4science\\xrd_robustness\\figures\\figure_3_simulated_test_paired_ood.svg",
  ]);
}

// Slide 4 — RRUFF learning curve across label budgets.
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addHeader(slide, "RRUFF：K=1/2/5 三种标注预算下，一致性预训练始终更好", 4, { fontSize: 38 });
  slide.charts.add("line", {
    position: { left: 82, top: 150, width: 1110, height: 450 },
    categories: ["K = 1", "K = 2", "K = 5"],
    series: [
      {
        name: "Dynamic ERM",
        values: [0.284718980, 0.302615082, 0.355464307],
        line: { style: "solid", fill: BLUE_DARK, width: 4 },
        marker: { symbol: "circle", size: 10 },
        valuesFormatCode: "0.000",
      },
      {
        name: "JS Consistency",
        values: [0.328039642, 0.348641109, 0.409931132],
        line: { style: "solid", fill: ORANGE, width: 4 },
        marker: { symbol: "diamond", size: 11 },
        valuesFormatCode: "0.000",
      },
    ],
    lineOptions: { grouping: "standard", smooth: false, varyColors: false },
    hasLegend: true,
    legend: { position: "top", overlay: false, textStyle: { fontSize: 17, fill: INK } },
    chartFill: "#FFFFFF",
    chartLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    xAxis: {
      visible: true,
      title: { text: "每类使用的真实谱数量 K", textStyle: { fontSize: 17, fill: MUTED } },
      textStyle: { fontSize: 18, fill: INK, bold: true },
      line: { style: "solid", fill: RULE, width: 1 },
      majorGridlines: null,
    },
    yAxis: {
      visible: true,
      min: 0.25,
      max: 0.43,
      majorUnit: 0.03,
      numberFormatCode: "0.00",
      title: { text: "Macro-F1", textStyle: { fontSize: 17, fill: MUTED } },
      textStyle: { fontSize: 15, fill: MUTED },
      line: { style: "solid", fill: "#FFFFFF", width: 0 },
      majorGridlines: { style: "solid", fill: "#E4E9EF", width: 1 },
    },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { fontSize: 16, fill: INK, bold: true } },
  });
  addText(slide, "Δ Macro-F1：   +4.33 pp              +4.60 pp              +5.45 pp", 214, 612, 860, 32, {
    fontSize: 21,
    bold: true,
    color: ORANGE,
    align: "center",
  });
  addFooter(slide, "RRUFF-301 · few-shot adaptation · locked test");
  addNotes(slide, [
    "E:\\AI4science\\xrd_robustness\\reports\\rruff301_fewshot_results.json",
  ]);
}

// Slide 5 — CNRS five-seed independent-source zero-shot evidence.
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addHeader(slide, "CNRS：独立真实谱 zero-shot，5/5 个 seed 同向提升", 5, { fontSize: 40 });
  addText(slide, "不使用任何 CNRS 标签进行校准或域适配", 74, 122, 620, 28, { fontSize: 17, color: MUTED });
  const pairs = [
    [0.206723404, 0.221244249],
    [0.146931446, 0.175563753],
    [0.184176072, 0.197119253],
    [0.214866157, 0.229526078],
    [0.189160446, 0.211969559],
  ];
  pairedSeedChart(slide, { left: 72, top: 150, width: 860, height: 438 }, pairs, [0.188372, 0.207085], {
    min: 0.14,
    max: 0.24,
    majorUnit: 0.02,
  });
  addText(slide, "5 / 5  ↑", 948, 214, 250, 72, { fontSize: 54, bold: true, color: GREEN, align: "center" });
  addText(slide, "独立真实谱源", 972, 300, 202, 28, { fontSize: 20, bold: true, color: NAVY, align: "center" });
  addText(slide, "zero-shot", 972, 338, 202, 28, { fontSize: 20, bold: true, color: NAVY, align: "center" });
  addLine(slide, 972, 390, 206, 0, RULE, 1);
  addText(slide, "均值提升", 972, 414, 202, 24, { fontSize: 17, color: MUTED, align: "center" });
  addText(slide, "+1.87 pp", 948, 448, 250, 48, { fontSize: 38, bold: true, color: ORANGE, align: "center" });
  addText(slide, "0.1884  →  0.2071", 948, 510, 250, 34, { fontSize: 24, bold: true, color: NAVY, align: "center" });
  addText(slide, "绝对 Macro-F1 仍低，说明广义真实域迁移仍有空间。", 214, 612, 850, 32, {
    fontSize: 21,
    color: MUTED,
    align: "center",
  });
  addFooter(slide, "CNRS-318 · independent source · frozen zero-shot");
  addNotes(slide, [
    "E:\\AI4science\\xrd_robustness\\outputs\\cnrs318_zero_shot\\audit\\paired_seed_macro_f1.csv",
    "E:\\AI4science\\xrd_robustness\\reports\\CNRS_318_RESULTS.md",
  ]);
}

// Slide 6 — forward-verifiable inversion next step.
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addHeader(slide, "下一步：从晶系分类走向可前向验证的定量参数反演", 6, { fontSize: 42 });
  addText(slide, "V0：已知相 · 单相 · 四方晶系", 60, 122, 520, 28, { fontSize: 18, color: MUTED });

  // Directional arrows precede the content blocks.
  addArrow(slide, 386, 330, 86, 16, NAVY);
  addArrow(slide, 808, 330, 86, 16, NAVY);

  addText(slide, "输入 PXRD", 72, 172, 320, 34, { fontSize: 25, bold: true, color: NAVY, align: "center" });
  spectrumChart(slide, { left: 66, top: 212, width: 334, height: 270 }, [
    { name: "input", x: base.x, y: base.y, color: NAVY, width: 2.6 },
  ], { axes: true, hasLegend: false, bucketSize: 12 });

  addText(slide, "反演参数", 488, 190, 304, 34, { fontSize: 25, bold: true, color: NAVY, align: "center" });
  addRect(slide, 486, 236, 308, 226, LIGHT, { geometry: "roundRect", borderRadius: 12, lineFill: RULE, lineWidth: 1.2 });
  addText(slide, "a        c", 522, 270, 236, 50, { fontSize: 36, bold: true, color: NAVY, align: "center" });
  addText(slide, "zero shift", 522, 338, 236, 36, { fontSize: 25, bold: true, color: ORANGE, align: "center" });
  addText(slide, "FWHM", 522, 394, 236, 36, { fontSize: 25, bold: true, color: ORANGE, align: "center" });
  addText(slide, "inverse model", 522, 474, 236, 24, { fontSize: 16, color: MUTED, align: "center" });

  addText(slide, "前向重建 ≈ 输入", 898, 172, 320, 34, { fontSize: 25, bold: true, color: NAVY, align: "center" });
  spectrumChart(slide, { left: 890, top: 212, width: 334, height: 270 }, [
    { name: "输入", x: base.x, y: base.y, color: NAVY, width: 2.3 },
    { name: "forward XRD", x: base.x, y: recon, color: ORANGE, width: 2.1, dashed: true },
  ], { axes: true, hasLegend: true, legendPosition: "bottom", legendFontSize: 14, bucketSize: 12 });

  addText(slide, "预测参数生成的 XRD 必须能够复现输入谱。", 290, 554, 700, 42, {
    fontSize: 29,
    bold: true,
    color: NAVY,
    align: "center",
  });
  addText(slide, "可验证标准：forward XRD 与 input XRD 的谱形、峰位和展宽保持一致", 248, 610, 784, 28, {
    fontSize: 18,
    color: MUTED,
    align: "center",
  });
  addFooter(slide);
  addNotes(slide, [
    "User-provided research-planning screenshot in this conversation",
    "E:\\AI4science\\docs\\CURRENT_STATE.md",
    SPECTRUM_CSV,
  ], "本页描述下一阶段的计划性闭环，不表示参数反演结果已经完成。" );
}

await fs.mkdir(RENDER_DIR, { recursive: true });
for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(`${RENDER_DIR}/${stem}.png`, await presentation.export({ slide, format: "png", scale: 1 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${RENDER_DIR}/${stem}.layout.json`, await layout.text());
}
await writeBlob(`${RENDER_DIR}/montage.webp`, await presentation.export({ format: "webp", montage: true, scale: 1 }));
const inspection = await presentation.inspect({ kind: "slide,textbox,shape,chart,notes", maxChars: 30000 });
await fs.writeFile(`${RENDER_DIR}/inspect.ndjson`, inspection.ndjson);
const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(FINAL);

console.log(`Wrote ${FINAL}`);
