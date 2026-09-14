import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const WORKSPACE = "E:/AI4science/.codex_tmp/scientific_evidence_deck_20260828/round7_add_p4_setup";
const SOURCE = `${WORKSPACE}/template-starter.pptx`;
const OUTPUT = "E:/AI4science/outputs/XRD_导师汇报_第七轮_新增实验配置P4_4页_2026-08-28.pptx";
const RENDER_DIR = `${WORKSPACE}/final-render`;
const OUTPUT_PNG_PREFIX = "E:/AI4science/outputs/XRD_导师汇报_第七轮";

const PANEL_DIR = "E:/AI4science/xrd_robustness/outputs/public_simulated_test/panel_cache/seed_20260721";
const PANEL_ROW = 1972;
const PANEL_BASE = `${PANEL_DIR}/level0.npy`;
const PERTURBATIONS = [
  { label: "峰位偏移", path: `${PANEL_DIR}/ood_shift_positive.npy` },
  { label: "峰展宽", path: `${PANEL_DIR}/ood_broadening.npy` },
  { label: "背景变化", path: `${PANEL_DIR}/ood_background.npy` },
  { label: "计数噪声", path: `${PANEL_DIR}/ood_noise.npy` },
  { label: "择优取向", path: `${PANEL_DIR}/ood_texture.npy` },
];

const W = 1280;
const FONT = "Microsoft YaHei";
const NAVY = "#143A63";
const INK = "#17222F";
const MUTED = "#657384";
const RULE = "#D9E0E8";
const BLUE = "#285F97";
const BASELINE = "#AEB8C4";

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

function addLine(slide, left, top, width, height = 0, color = RULE, lineWidth = 1) {
  return slide.shapes.add({
    geometry: "line",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: color, width: lineWidth },
  });
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
  const maxValue = Math.max(...values);
  return values.map((value) => value / maxValue);
}

function xGrid(cols = 3501) {
  return Array.from({ length: cols }, (_, i) => 10 + 0.02 * i);
}

function cropSeries(x, y, minX, maxX) {
  const xo = [];
  const yo = [];
  for (let i = 0; i < x.length; i += 1) {
    if (x[i] >= minX && x[i] <= maxX) {
      xo.push(x[i]);
      yo.push(y[i]);
    }
  }
  return { x: xo, y: yo };
}

function downsampleMax(x, y, bucketSize = 7) {
  const xo = [];
  const yo = [];
  for (let start = 0; start < x.length; start += bucketSize) {
    const end = Math.min(x.length, start + bucketSize);
    let best = start;
    for (let i = start + 1; i < end; i += 1) {
      if (y[i] > y[best]) best = i;
    }
    xo.push(x[best]);
    yo.push(y[best]);
  }
  return { x: xo, y: yo };
}

function addMiniSpectrum(slide, position, x, baselineY, changedY) {
  const croppedBaseline = cropSeries(x, baselineY, 12, 45);
  const croppedChanged = cropSeries(x, changedY, 12, 45);
  const base = downsampleMax(croppedBaseline.x, croppedBaseline.y, 7);
  const changed = downsampleMax(croppedChanged.x, croppedChanged.y, 7);
  return slide.charts.add("scatter", {
    position,
    series: [
      {
        name: "基准谱",
        xValues: base.x,
        values: base.y,
        line: { style: "solid", fill: BASELINE, width: 1.6 },
        marker: { symbol: "none", size: 2 },
      },
      {
        name: "扰动谱",
        xValues: changed.x,
        values: changed.y,
        line: { style: "solid", fill: BLUE, width: 2.4 },
        marker: { symbol: "none", size: 2 },
      },
    ],
    scatterOptions: { style: "line", varyColors: false },
    hasLegend: false,
    chartFill: "#FFFFFF",
    chartLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    xAxis: {
      visible: false,
      min: 12,
      max: 45,
      majorUnit: 5,
      line: { style: "solid", fill: "#FFFFFF", width: 0 },
      majorGridlines: null,
      tickLabelPosition: "none",
    },
    yAxis: {
      visible: false,
      min: 0,
      max: 1.05,
      line: { style: "solid", fill: "#FFFFFF", width: 0 },
      majorGridlines: null,
      tickLabelPosition: "none",
    },
  });
}

function setHeaderText(shape, text, fontSize) {
  shape.text = text;
  shape.text.style = {
    typeface: FONT,
    fontSize,
    bold: true,
    color: NAVY,
    alignment: "left",
    verticalAlignment: "top",
    lineSpacing: 1.06,
    wrap: "square",
    autoFit: "none",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(SOURCE));
if (presentation.slides.items.length !== 3) {
  throw new Error(`Expected 3 source slides, found ${presentation.slides.items.length}`);
}

presentation.resolve("sh/9072xkry").text = "02 / 04";
presentation.resolve("sh/cza94vmx").text = "03 / 04";
presentation.resolve("sh/mtwrmxg7").text = "变化来自测量条件，而非晶体结构本身。";
presentation.resolve("sh/v6l4jq94").text = "同一晶体结构";

const sourceP2 = presentation.resolve("sl/hwbqtkby");
const p4 = sourceP2.duplicate();
p4.moveTo(3);

const duplicatedShapes = [...p4.shapes.items];
if (duplicatedShapes.length < 3) throw new Error("Duplicated slide does not contain the expected header frame.");
for (const chart of [...p4.charts.items]) p4.charts.deleteById(chart.id);
for (const shape of duplicatedShapes.slice(3)) shape.delete();

const [titleShape, pageShape] = duplicatedShapes;
setHeaderText(titleShape, "14,060 个晶体结构，覆盖 5 类常见测量扰动", 38);
pageShape.text = "04 / 04";

addText(p4, "14,060", 68, 154, 390, 82, {
  fontSize: 60,
  bold: true,
  color: NAVY,
  valign: "middle",
});
addText(p4, "Materials Project 晶体结构", 72, 242, 390, 34, {
  fontSize: 22,
  color: INK,
});
addText(p4, "训练 / 验证 / 测试", 72, 337, 375, 28, {
  fontSize: 17,
  color: MUTED,
});
addText(p4, "9,842 / 2,109 / 2,109", 72, 374, 405, 48, {
  fontSize: 29,
  bold: true,
  color: NAVY,
});
addText(p4, "按晶体结构划分，\n同一结构的所有扰动谱不会跨集合。", 72, 500, 392, 72, {
  fontSize: 16,
  color: MUTED,
  lineSpacing: 1.2,
});

addLine(p4, 500, 134, 0, 502, RULE, 1.2);
addText(p4, "同一晶体：灰色基准谱 + 蓝色扰动谱", 750, 118, 448, 22, {
  fontSize: 14,
  color: MUTED,
  align: "right",
});

const x = xGrid();
const baseline = await loadNpyRow(PANEL_BASE, PANEL_ROW);
const changedRows = await Promise.all(PERTURBATIONS.map((item) => loadNpyRow(item.path, PANEL_ROW)));
const rowTops = [143, 240, 337, 434, 531];
for (let i = 0; i < PERTURBATIONS.length; i += 1) {
  const top = rowTops[i];
  addText(p4, PERTURBATIONS[i].label, 545, top + 21, 130, 32, {
    fontSize: 20,
    bold: true,
    color: INK,
    valign: "middle",
  });
  addMiniSpectrum(p4, { left: 680, top, width: 520, height: 70 }, x, baseline, changedRows[i]);
  if (i < PERTURBATIONS.length - 1) addLine(p4, 545, top + 86, 655, 0, "#E7EBF0", 0.8);
}

p4.speakerNotes.textFrame.setText([
  "本页只回答两个问题：使用多少独立晶体结构，以及模拟了哪些常见测量扰动。",
  "五条微型谱来自同一个测试结构 mp-556434（panel cache row 1972）；灰色为 level0 基准，蓝色为对应扰动缓存。",
  "",
  "[Sources]",
  "- E:/AI4science/xrd_robustness/configs/experiment.public.json",
  "- E:/AI4science/xrd_robustness/configs/data.method_transfer.structure_split.json",
  "- E:/AI4science/xrd_robustness/data/formal_14060/manifests/split_manifest.json",
  "- E:/AI4science/xrd_robustness/configs/simulation.method_transfer.frozen.json",
  "- E:/AI4science/xrd_robustness/outputs/public_simulated_test/panel_cache/index.json",
  "- E:/AI4science/xrd_robustness/data/formal_14060/manifests/v9_method_transfer_test_seed_20260721.csv",
].join("\n"));

if (presentation.slides.items.length !== 4) {
  throw new Error(`Expected 4 output slides, found ${presentation.slides.items.length}`);
}

await fs.mkdir(RENDER_DIR, { recursive: true });
await fs.mkdir("E:/AI4science/outputs", { recursive: true });
for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  const png = await presentation.export({ slide, format: "png", scale: 1 });
  await writeBlob(`${RENDER_DIR}/${stem}.png`, png);
  await writeBlob(`${OUTPUT_PNG_PREFIX}_${stem}.png`, png);
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${RENDER_DIR}/${stem}.layout.json`, await layout.text());
}

await writeBlob(`${RENDER_DIR}/montage.webp`, await presentation.export({ format: "webp", montage: true, scale: 1 }));
const inspection = await presentation.inspect({
  kind: "deck,slide,textbox,shape,chart,image,notes,layout",
  maxChars: 40000,
});
await fs.writeFile(`${WORKSPACE}/final-inspect.ndjson`, inspection.ndjson);

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(OUTPUT);
console.log(`Wrote ${OUTPUT}`);
