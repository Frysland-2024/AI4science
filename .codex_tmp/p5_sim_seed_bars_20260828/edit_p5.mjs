import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p5_sim_seed_bars_20260828");
const starterPath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "final-render");

const baseline = [0.6390, 0.6553, 0.6577, 0.6517, 0.6500];
const consistency = [0.6939, 0.7167, 0.7075, 0.6967, 0.7118];
const gains = ["+5.48 pp", "+6.14 pp", "+4.99 pp", "+4.51 pp", "+6.18 pp"];
const categories = ["Seed 1", "Seed 2", "Seed 3", "Seed 4", "Seed 5"];

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function deleteElement(presentation, slide, entry) {
  const element = presentation.resolve(entry.id);
  if (entry.kind === "chart") {
    slide.charts.deleteById(element.id);
    return;
  }
  if (typeof element.delete === "function") {
    element.delete();
    return;
  }
  throw new Error(`Resolved element ${entry.id} does not support deletion`);
}

function setTextBox(shape, text, position, style) {
  shape.text = text;
  shape.position = position;
  shape.text.style = {
    ...style,
    wrap: "none",
    autoFit: "shrinkText",
    verticalAlignment: "middle",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
}

function parseInspect(ndjson) {
  return ndjson
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function requireEntry(entries, predicate, label) {
  const entry = entries.find(predicate);
  if (!entry) throw new Error(`Could not locate ${label}`);
  return entry;
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(starterPath));
  if (presentation.slides.items.length !== 5) {
    throw new Error(`Expected 5 slides in starter, found ${presentation.slides.items.length}`);
  }

  const slide = presentation.slides.items[4];
  // Artifact-tool assigns fresh anchors on import; inspect this live instance
  // and resolve its current anchors instead of relying on stale IDs.
  const beforeInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes",
    maxChars: 30000,
  });
  const p5Entries = parseInspect(beforeInspect.ndjson).filter((entry) => entry.slide === 5);

  // Preserve the inherited title/rule/page rhythm; only rewrite P5's text.
  const titleEntry = requireEntry(p5Entries, (entry) => entry.name === "slide-2-title", "P5 title");
  const title = presentation.resolve(titleEntry.id);
  title.text = "五次独立训练全部提升，平均 Macro-F1 +5.46 个百分点";
  title.text.autoFit = "shrinkText";
  title.text.wrap = "none";

  const pageEntry = requireEntry(p5Entries, (entry) => entry.text === "02 / 04", "P5 page marker");
  const page = presentation.resolve(pageEntry.id);
  page.text = "05 / 05";

  // Clear duplicated P2 content from P5 only.
  for (const entry of p5Entries.filter((item) => item.kind === "shape" && item.bbox?.[3] === 0 && item.bbox?.[1] > 150)) {
    deleteElement(presentation, slide, entry);
  }
  const takeawayEntry = requireEntry(
    p5Entries,
    (entry) => entry.text === "变化来自测量条件，而非晶体结构本身。",
    "P5 inherited takeaway",
  );
  deleteElement(presentation, slide, takeawayEntry);
  for (const entry of p5Entries.filter((item) => item.kind === "chart")) {
    deleteElement(presentation, slide, entry);
  }

  // Reuse three existing text objects for the only auxiliary summary.
  setTextBox(
    presentation.resolve(requireEntry(p5Entries, (entry) => entry.text === "理想 / 基准谱", "P5 summary line 1").id),
    "5 / 5 ↑",
    { left: 978, top: 178, width: 225, height: 68 },
    { fontSize: 42, bold: true, color: "#153E6A", alignment: "left" },
  );
  setTextBox(
    presentation.resolve(requireEntry(p5Entries, (entry) => entry.text === "峰移或展宽后的谱", "P5 summary line 2").id),
    "全部独立训练均提升",
    { left: 978, top: 246, width: 238, height: 36 },
    { fontSize: 18, bold: false, color: "#6B7B8D", alignment: "left" },
  );
  setTextBox(
    presentation.resolve(requireEntry(p5Entries, (entry) => entry.text === "加背景 / 噪声后的谱", "P5 summary line 3").id),
    "平均 +5.46 pp",
    { left: 978, top: 338, width: 238, height: 44 },
    { fontSize: 27, bold: true, color: "#153E6A", alignment: "left" },
  );

  // Main evidence: five clustered column pairs, with a truthful zero baseline.
  slide.charts.add("bar", {
    position: { left: 62, top: 135, width: 880, height: 505 },
    categories,
    series: [
      {
        name: "基线",
        values: baseline,
        fill: "#AAB8C5",
        line: { style: "solid", fill: "#AAB8C5", width: 0 },
      },
      {
        name: "一致性训练",
        values: consistency,
        fill: "#245F95",
        line: { style: "solid", fill: "#245F95", width: 0 },
        dataLabelOverrides: gains.map((text, idx) => ({
          idx,
          text,
          position: "outEnd",
          showValue: false,
          textStyle: { fontSize: 14, fill: "#153E6A", bold: true, alignment: "center" },
          fill: { color: "#FFFFFF", transparency: 100000 },
          line: { style: "solid", fill: "#FFFFFF", width: 0 },
        })),
      },
    ],
    barOptions: {
      direction: "column",
      grouping: "clustered",
      varyColors: false,
      gapWidth: 65,
      overlap: 0,
    },
    hasLegend: true,
    legend: {
      position: "bottom",
      overlay: false,
      fill: { color: "#FFFFFF", transparency: 100000 },
      line: { style: "solid", fill: "#FFFFFF", width: 0 },
      textStyle: { fontSize: 15, fill: "#536273" },
    },
    xAxis: {
      visible: true,
      position: "bottom",
      tickLabelPosition: "nextTo",
      textStyle: { fontSize: 14, fill: "#4D5D6E" },
      line: { style: "solid", fill: "#AAB4BF", width: 1 },
      majorGridlines: null,
      minorGridlines: null,
    },
    yAxis: {
      visible: true,
      position: "left",
      title: {
        text: "Macro-F1",
        textStyle: { fontSize: 15, fill: "#4D5D6E", bold: false },
      },
      numberFormatCode: "0.0",
      min: 0,
      max: 0.8,
      majorUnit: 0.2,
      tickLabelPosition: "nextTo",
      textStyle: { fontSize: 13, fill: "#718091" },
      line: { style: "solid", fill: "#AAB4BF", width: 1 },
      majorGridlines: { style: "solid", fill: "#E4EAF0", width: 1 },
      minorGridlines: null,
    },
    dataLabels: {
      showValue: false,
      showSeriesName: false,
      showCategoryName: false,
      showPercent: false,
      showLeaderLines: false,
    },
    chartFill: "#FFFFFF",
    chartLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    plotAreaFill: "#FFFFFF",
    plotAreaLine: { style: "solid", fill: "#FFFFFF", width: 0 },
  });

  slide.speakerNotes.textFrame.setText([
    "本页只展示冻结模拟扰动 Test 的 Macro-F1。",
    "五次独立训练中，一致性训练均优于基线。",
    "Seed 1: 0.6390 → 0.6939 (+5.48 pp)",
    "Seed 2: 0.6553 → 0.7167 (+6.14 pp)",
    "Seed 3: 0.6577 → 0.7075 (+4.99 pp)",
    "Seed 4: 0.6517 → 0.6967 (+4.51 pp)",
    "Seed 5: 0.6500 → 0.7118 (+6.18 pp)",
    "平均: 0.6507 → 0.7053 (+5.46 pp)",
    "[Sources]",
    "- E:/AI4science/xrd_robustness/reports/simulated_test_results.json",
  ].join("\n"));

  const pptxBlob = await PresentationFile.exportPptx(presentation);
  await pptxBlob.save(outputPath);

  for (const [index, oneSlide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(path.join(renderDir, `${stem}.png`), await presentation.export({ slide: oneSlide, format: "png", scale: 1 }));
    const layout = await oneSlide.export({ format: "layout" });
    await fs.writeFile(path.join(renderDir, `${stem}.layout.json`), await layout.text(), "utf8");
  }
  await writeBlob(path.join(renderDir, "montage.webp"), await presentation.export({ format: "webp", montage: true, scale: 1 }));

  const inspect = await presentation.inspect({
    kind: "slide,textbox,shape,image,table,chart,notes,layout",
    maxChars: 40000,
  });
  await fs.writeFile(path.join(tempDir, "final-inspect.ndjson"), inspect.ndjson, "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
