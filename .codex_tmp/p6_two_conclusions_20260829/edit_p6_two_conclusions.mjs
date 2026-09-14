import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p6_two_conclusions_20260829";
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(tempDir, "staged-XRD_导师汇报.pptx");
const beforeDir = path.join(tempDir, "before-render");
const afterDir = path.join(tempDir, "after-render");
const finalLayoutDir = path.join(tempDir, "final-layout");

const oldTitle = "RRUFF-301 真实谱验证：仅用 7 条真实谱再训练，也能提升 +4.33 pp";
const newTitle = "RRUFF-301 真实谱少样本验证：仅用 7 条真实谱再训练，也能提升 +4.33 pp";
const subtitle = "RRUFF-301：301 条真实实验 PXRD 谱｜每类仅用 1 / 2 / 5 条真实谱进行少量再训练";
const baselineExpected = [0.284718979578149, 0.3026150816434789, 0.35546430676138274];
const methodExpected = [0.3280396420899909, 0.3486411093591271, 0.40993113162853434];
const gainNames = ["p6-gain-1", "p6-gain-2", "p6-gain-3"];
const gainPositions = [
  { left: 150, top: 168, width: 160, height: 25 },
  { left: 381, top: 168, width: 160, height: 25 },
  { left: 612, top: 168, width: 160, height: 25 },
];

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function requireEntry(entries, predicate, label) {
  const entry = entries.find(predicate);
  if (!entry) throw new Error(`Could not locate ${label}`);
  return entry;
}

function sameValues(actual, expected) {
  return Array.isArray(actual)
    && actual.length === expected.length
    && actual.every((value, index) => Math.abs(Number(value) - expected[index]) < 1e-9);
}

function setTextBox(shape, text, position, style) {
  shape.text = text;
  shape.position = position;
  shape.text.style = {
    typeface: "Microsoft YaHei",
    ...style,
    wrap: "none",
    autoFit: "shrinkText",
    verticalAlignment: "middle",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(beforeDir, { recursive: true });
  await fs.mkdir(afterDir, { recursive: true });
  await fs.mkdir(finalLayoutDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 7) throw new Error("Expected seven slides");

  const before = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 100000,
  });
  await fs.writeFile(path.join(tempDir, "before-inspect.ndjson"), before.ndjson, "utf8");
  const entries = parseInspect(before.ndjson);
  const p6Entries = entries.filter((entry) => entry.slide === 6);
  const slideEntry = requireEntry(p6Entries, (entry) => entry.kind === "slide", "slide 6");
  const titleEntry = requireEntry(p6Entries, (entry) => entry.name === "slide-2-title" && entry.text === oldTitle, "P6 title");
  const subtitleEntry = requireEntry(p6Entries, (entry) => entry.name === "p6-dataset-context", "P6 subtitle");
  const summaryEntry = requireEntry(p6Entries, (entry) => entry.name === "p6-summary-caption", "P6 summary textbox");
  const chartEntry = requireEntry(p6Entries, (entry) => entry.name === "p6-rruff-fewshot-bars", "P6 chart");

  const slide = presentation.resolve(slideEntry.id);
  await writeBlob(path.join(beforeDir, "slide-06.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const beforeLayout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(beforeDir, "slide-06.layout.json"), await beforeLayout.text(), "utf8");

  const chart = presentation.resolve(chartEntry.id);
  if (!sameValues(chart.series.getItemAt(0).values, baselineExpected)) {
    throw new Error(`Baseline chart values changed: ${JSON.stringify(chart.series.getItemAt(0).values)}`);
  }
  if (!sameValues(chart.series.getItemAt(1).values, methodExpected)) {
    throw new Error(`Method chart values changed: ${JSON.stringify(chart.series.getItemAt(1).values)}`);
  }

  const title = presentation.resolve(titleEntry.id);
  setTextBox(
    title,
    newTitle,
    { left: 58, top: 28, width: 1096, height: 62 },
    { fontSize: 32, bold: true, color: "#153E6A", alignment: "left" },
  );

  const context = presentation.resolve(subtitleEntry.id);
  context.position = { left: 64, top: 108, width: 1158, height: 32 };
  context.text.set([
    [
      {
        run: "RRUFF-301：301 条真实实验 PXRD 谱",
        textStyle: { bold: true, color: "#234B73", fontSize: "19px", typeface: "Microsoft YaHei" },
      },
      {
        run: "｜每类仅用 1 / 2 / 5 条真实谱进行少量再训练",
        textStyle: { bold: false, color: "#3F5368", fontSize: "19px", typeface: "Microsoft YaHei" },
      },
    ],
  ]);
  context.text.fontSize = 19;
  context.text.typeface = "Microsoft YaHei";
  context.text.color = "#3F5368";
  context.text.alignment = "left";
  context.text.verticalAlignment = "middle";
  context.text.wrap = "none";
  context.text.autoFit = "shrinkText";
  context.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  chart.position = { left: 58, top: 196, width: 760, height: 456 };

  for (let index = 0; index < gainNames.length; index += 1) {
    const gainEntry = requireEntry(p6Entries, (entry) => entry.name === gainNames[index], gainNames[index]);
    const gain = presentation.resolve(gainEntry.id);
    gain.position = gainPositions[index];
  }

  const summary = presentation.resolve(summaryEntry.id);
  summary.position = { left: 852, top: 176, width: 350, height: 464 };
  summary.text.set([
    [{ run: "① 三档真实标注预算均提升", textStyle: { bold: true, color: "#153E6A", fontSize: "23px", typeface: "Microsoft YaHei" } }],
    [
      { run: "平均约 ", textStyle: { bold: false, color: "#536779", fontSize: "19px", typeface: "Microsoft YaHei" } },
      { run: "+4.8 pp", textStyle: { bold: true, color: "#07579D", fontSize: "30px", typeface: "Microsoft YaHei" } },
    ],
    [{ run: "", textStyle: { fontSize: "14px", typeface: "Microsoft YaHei" } }],
    [{ run: "② 达到相近甚至更好的性能，\n所需真实谱更少", textStyle: { bold: true, color: "#153E6A", fontSize: "22px", typeface: "Microsoft YaHei" } }],
    [{ run: "", textStyle: { fontSize: "10px", typeface: "Microsoft YaHei" } }],
    [{ run: "14 条 ≈ 基线 35 条", textStyle: { bold: true, color: "#234B73", fontSize: "20px", typeface: "Microsoft YaHei" } }],
    [{ run: "0.349 ≈ 0.356", textStyle: { bold: false, color: "#536779", fontSize: "19px", typeface: "Microsoft YaHei" } }],
    [{ run: "", textStyle: { fontSize: "8px", typeface: "Microsoft YaHei" } }],
    [{ run: "7 条 > 基线 14 条", textStyle: { bold: true, color: "#234B73", fontSize: "20px", typeface: "Microsoft YaHei" } }],
    [{ run: "0.328 > 0.303", textStyle: { bold: false, color: "#536779", fontSize: "19px", typeface: "Microsoft YaHei" } }],
  ]);
  summary.text.typeface = "Microsoft YaHei";
  summary.text.color = "#153E6A";
  summary.text.alignment = "left";
  summary.text.verticalAlignment = "top";
  summary.text.wrap = "square";
  summary.text.autoFit = "shrinkText";
  summary.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  await writeBlob(path.join(afterDir, "slide-06.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const afterLayout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(afterDir, "slide-06.layout.json"), await afterLayout.text(), "utf8");
  await fs.writeFile(path.join(finalLayoutDir, "slide-06.layout.json"), await afterLayout.text(), "utf8");

  const after = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 100000,
  });
  await fs.writeFile(path.join(tempDir, "after-inspect.ndjson"), after.ndjson, "utf8");
  const afterEntries = parseInspect(after.ndjson).filter((entry) => entry.slide === 6);
  const afterTitle = requireEntry(afterEntries, (entry) => entry.text === newTitle, "updated P6 title");
  const afterSubtitle = requireEntry(afterEntries, (entry) => entry.text === subtitle, "updated P6 subtitle");
  const afterSummary = requireEntry(afterEntries, (entry) => entry.name === "p6-summary-caption", "updated P6 summary");
  const afterChart = requireEntry(afterEntries, (entry) => entry.kind === "chart", "updated P6 chart");
  if (afterTitle.textLines !== 1 || afterSubtitle.textLines !== 1) {
    throw new Error(`Unexpected title/subtitle wrapping: ${JSON.stringify({ afterTitle, afterSubtitle })}`);
  }
  for (const phrase of [
    "① 三档真实标注预算均提升",
    "平均约 +4.8 pp",
    "② 达到相近甚至更好的性能，\n所需真实谱更少",
    "14 条 ≈ 基线 35 条",
    "0.349 ≈ 0.356",
    "7 条 > 基线 14 条",
    "0.328 > 0.303",
  ]) {
    if (!afterSummary.text.includes(phrase)) throw new Error(`Missing summary phrase: ${phrase}`);
  }
  if (JSON.stringify(afterChart.bbox) !== JSON.stringify([58, 196, 760, 456])) {
    throw new Error(`Unexpected chart geometry: ${JSON.stringify(afterChart.bbox)}`);
  }
  if (!sameValues(chart.series.getItemAt(0).values, baselineExpected) || !sameValues(chart.series.getItemAt(1).values, methodExpected)) {
    throw new Error("Chart values changed after repositioning");
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
