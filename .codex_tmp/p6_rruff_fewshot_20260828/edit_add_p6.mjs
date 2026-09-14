import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "file:///C:/Users/Lenovo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p6_rruff_fewshot_20260828");
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "p6-render");

const baseline = [0.284718979578149, 0.3026150816434789, 0.35546430676138274];
const consistency = [0.3280396420899909, 0.3486411093591271, 0.40993113162853434];
const gains = ["+4.33 pp", "+4.60 pp", "+5.45 pp"];
const categories = ["每类 1 条\n（共 7 条）", "每类 2 条\n（共 14 条）", "每类 5 条\n（共 35 条）"];
const groupCenters = [261, 528, 795];

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

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function setTextBox(shape, text, position, style) {
  shape.text = text;
  shape.position = position;
  shape.text.style = {
    ...style,
    wrap: "square",
    autoFit: "shrinkText",
    verticalAlignment: "middle",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
}

function addText(slide, name, text, position, style) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position,
    fill: "none",
    line: { style: "solid", fill: "#FFFFFF", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    ...style,
    wrap: "square",
    autoFit: "shrinkText",
    verticalAlignment: "middle",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
  return shape;
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 5) {
    throw new Error(`Expected five source slides, found ${presentation.slides.items.length}`);
  }

  // Adding P6 makes the old /05 denominators stale. This is the only change to P1-P5.
  const sourceInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes",
    maxChars: 40000,
  });
  const sourceEntries = parseInspect(sourceInspect.ndjson);
  const pageEntries = sourceEntries.filter(
    (entry) => entry.kind === "textbox" && /^0[2-5] \/ (04|05)$/.test(entry.text ?? ""),
  );
  if (pageEntries.length !== 4) {
    throw new Error(`Expected page markers on P2-P5, found ${pageEntries.length}`);
  }
  for (const entry of pageEntries) {
    const page = presentation.resolve(entry.id);
    page.text = String(entry.text).replace(/\/ (04|05)$/, "/ 06");
  }

  // Reuse the approved P5 evidence-slide frame and edit the duplicate only.
  const p6 = presentation.slides.items[4].duplicate();
  p6.moveTo(5);
  if (presentation.slides.items.length !== 6) throw new Error("P6 duplication failed");

  const duplicatedInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes",
    maxChars: 50000,
  });
  const p6Entries = parseInspect(duplicatedInspect.ndjson).filter((entry) => entry.slide === 6);

  const titleEntry = requireEntry(p6Entries, (entry) => entry.name === "slide-2-title", "P6 title");
  const title = presentation.resolve(titleEntry.id);
  title.text = "只需极少真实谱适配，三档标注预算下性能均提升";
  title.text.autoFit = "shrinkText";
  title.text.wrap = "none";

  const pageEntry = requireEntry(p6Entries, (entry) => entry.text === "05 / 06", "P6 page marker");
  presentation.resolve(pageEntry.id).text = "06 / 06";

  for (const entry of p6Entries.filter((entry) => entry.kind === "textbox" && /^p5-gain-/.test(entry.name ?? ""))) {
    presentation.resolve(entry.id).delete();
  }

  const chartEntry = requireEntry(p6Entries, (entry) => entry.kind === "chart", "P6 inherited chart");
  p6.charts.deleteById(presentation.resolve(chartEntry.id).id);

  setTextBox(
    presentation.resolve(requireEntry(p6Entries, (entry) => entry.text === "5 / 5 ↑", "P6 headline line 1").id),
    "仅 7 条",
    { left: 978, top: 205, width: 225, height: 62 },
    { fontSize: 42, bold: true, color: "#153E6A", alignment: "left" },
  );
  setTextBox(
    presentation.resolve(requireEntry(p6Entries, (entry) => entry.text === "全部独立训练均提升", "P6 headline line 2").id),
    "真实标注谱",
    { left: 978, top: 264, width: 238, height: 38 },
    { fontSize: 25, bold: true, color: "#153E6A", alignment: "left" },
  );
  setTextBox(
    presentation.resolve(requireEntry(p6Entries, (entry) => entry.text === "平均 +5.46 pp", "P6 headline line 3").id),
    "+4.33 pp",
    { left: 978, top: 352, width: 238, height: 50 },
    { fontSize: 31, bold: true, color: "#153E6A", alignment: "left" },
  );
  addText(
    p6,
    "p6-summary-caption",
    "仍然提升",
    { left: 978, top: 401, width: 238, height: 32 },
    { fontSize: 18, bold: false, color: "#6B7B8D", alignment: "left" },
  );

  addText(
    p6,
    "p6-dataset-context",
    "RRUFF：301 条真实实验谱｜每个晶系仅使用 1 / 2 / 5 条标注进行少样本适配",
    { left: 64, top: 108, width: 870, height: 28 },
    { fontSize: 17, bold: false, color: "#627386", alignment: "left" },
  );

  gains.forEach((text, index) => {
    addText(
      p6,
      `p6-gain-${index + 1}`,
      text,
      { left: groupCenters[index] - 64, top: 143, width: 128, height: 26 },
      { fontSize: 18, bold: true, color: "#153E6A", alignment: "center" },
    );
  });

  const chart = p6.charts.add("bar", {
    position: { left: 62, top: 172, width: 880, height: 468 },
    categories,
    series: [
      {
        name: "基线",
        values: baseline,
        fill: "#CDD2D7",
        line: { style: "solid", fill: "#BFC4C9", width: 0.5 },
        dataLabelOverrides: baseline.map((value, idx) => ({
          idx,
          text: value.toFixed(3),
          position: "outEnd",
          showValue: false,
          textStyle: { fontSize: 16, fill: "#69727C", bold: true, alignment: "center" },
          fill: { color: "#FFFFFF", transparency: 100000 },
          line: { style: "solid", fill: "#FFFFFF", width: 0 },
        })),
      },
      {
        name: "一致性训练",
        values: consistency,
        fill: "#0B5EAA",
        line: { style: "solid", fill: "#084B87", width: 0.5 },
        dataLabelOverrides: consistency.map((value, idx) => ({
          idx,
          text: value.toFixed(3),
          position: "outEnd",
          showValue: false,
          textStyle: { fontSize: 16, fill: "#0B5EAA", bold: true, alignment: "center" },
          fill: { color: "#FFFFFF", transparency: 100000 },
          line: { style: "solid", fill: "#FFFFFF", width: 0 },
        })),
      },
    ],
    barOptions: {
      direction: "column",
      grouping: "clustered",
      varyColors: false,
      gapWidth: 85,
      overlap: 0,
    },
    hasLegend: true,
    legend: {
      position: "bottom",
      overlay: false,
      fill: { color: "#FFFFFF", transparency: 100000 },
      line: { style: "solid", fill: "#FFFFFF", width: 0 },
      textStyle: { fontSize: 18, fill: "#536273" },
    },
    xAxis: {
      visible: true,
      position: "bottom",
      tickLabelPosition: "nextTo",
      textStyle: { fontSize: 16, fill: "#4D5D6E" },
      line: { style: "solid", fill: "#AAB4BF", width: 1 },
      majorGridlines: null,
      minorGridlines: null,
    },
    yAxis: {
      visible: true,
      position: "left",
      title: {
        text: "Macro-F1",
        textStyle: { fontSize: 17, fill: "#4D5D6E", bold: false },
      },
      numberFormatCode: "0.0",
      min: 0,
      max: 0.5,
      majorUnit: 0.1,
      tickLabelPosition: "nextTo",
      textStyle: { fontSize: 15, fill: "#718091" },
      line: { style: "solid", fill: "#AAB4BF", width: 1 },
      majorGridlines: { style: "solid", fill: "#EEF1F4", width: 1 },
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
  chart.name = "p6-rruff-fewshot-bars";

  p6.speakerNotes.textFrame.setText([
    "本页强调真实标签效率，而不是再次重复上一页的五种子稳定性。",
    "RRUFF-301 包含 301 个唯一 RRUFF 实测样本，每个样本对应一条规范化 PXRD 谱；301 不代表 301 种不同矿物。",
    "数据覆盖 7 个晶系，每类 43 条：10 条进入 adaptation pool，33 条进入 locked test。",
    "K=1/2/5 是 labels per class；每个 episode 的支持集因此共有 7/14/35 条真实标注谱。",
    "图中数值为 5 个 pretraining seeds × 5 个 episode seeds 共 25 组配对运行的平均 Macro-F1。",
    "K=1: 0.2847 → 0.3280 (+4.33 pp)",
    "K=2: 0.3026 → 0.3486 (+4.60 pp)",
    "K=5: 0.3555 → 0.4099 (+5.45 pp)",
    "该证据为 retrospectively verified locked-test few-shot 结果，不表述为 provenance-complete prospective confirmatory run。",
    "[Sources]",
    "- E:/AI4science/xrd_robustness/reports/rruff301_fewshot_results.json",
    "- E:/AI4science/xrd_robustness/data/real_xrd/rruff371/contracts/dataset_contract.json",
    "- E:/AI4science/xrd_robustness/data/real_xrd/rruff371/splits/rruff301_manifest.json",
    "- E:/AI4science/xrd_robustness/data/real_xrd/rruff371/manifests/rruff371_master_manifest.csv",
  ].join("\n"));

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  await writeBlob(path.join(renderDir, "slide-06.png"), await presentation.export({ slide: p6, format: "png", scale: 1 }));
  const layout = await p6.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, "slide-06.layout.json"), await layout.text(), "utf8");

  const after = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 60000,
  });
  const p6Lines = parseInspect(after.ndjson)
    .filter((entry) => entry.slide === 6)
    .map((entry) => JSON.stringify(entry))
    .join("\n");
  await fs.writeFile(path.join(tempDir, "p6-inspect.ndjson"), `${p6Lines}\n`, "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
