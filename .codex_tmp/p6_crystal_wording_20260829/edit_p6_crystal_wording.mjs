import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p6_crystal_wording_20260829";
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(tempDir, "staged-XRD_导师汇报.pptx");
const afterDir = path.join(tempDir, "after-render");
const finalLayoutDir = path.join(tempDir, "final-layout");

const newSubtitle = "RRUFF-301：301 条真实实验 PXRD 谱｜每个晶系各取 1 / 2 / 5 条真实谱进行少量再训练";
const newCategories = [
  "每个晶系 1 条\n（共 7 条）",
  "每个晶系 2 条\n（共 14 条）",
  "每个晶系 5 条\n（共 35 条）",
];
const baselineExpected = [0.284718979578149, 0.3026150816434789, 0.35546430676138274];
const methodExpected = [0.3280396420899909, 0.3486411093591271, 0.40993113162853434];

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

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(afterDir, { recursive: true });
  await fs.mkdir(finalLayoutDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 7) throw new Error("Expected seven slides");

  const before = await presentation.inspect({
    kind: "deck,slide,textbox,shape,chart,table,image,notes,layout",
    maxChars: 120000,
  });
  await fs.writeFile(path.join(tempDir, "before-inspect.ndjson"), before.ndjson, "utf8");
  const entries = parseInspect(before.ndjson);
  const p6Entries = entries.filter((entry) => entry.slide === 6);

  const slideEntry = requireEntry(p6Entries, (entry) => entry.kind === "slide", "slide 6");
  const subtitleEntry = requireEntry(p6Entries, (entry) => entry.id === "sh/47mt0b6x", "P6 subtitle");
  const summaryEntry = requireEntry(p6Entries, (entry) => entry.id === "sh/5svutgni", "P6 summary");
  const chartEntry = requireEntry(p6Entries, (entry) => entry.id === "ch/8va107ql", "P6 chart");
  const slide = presentation.resolve(slideEntry.id);

  const chart = presentation.resolve(chartEntry.id);
  if (!sameValues(chart.series.getItemAt(0).values, baselineExpected)) {
    throw new Error(`Baseline chart values changed: ${JSON.stringify(chart.series.getItemAt(0).values)}`);
  }
  if (!sameValues(chart.series.getItemAt(1).values, methodExpected)) {
    throw new Error(`Method chart values changed: ${JSON.stringify(chart.series.getItemAt(1).values)}`);
  }

  const subtitle = presentation.resolve(subtitleEntry.id);
  subtitle.text.set([
    [
      {
        run: "RRUFF-301：301 条真实实验 PXRD 谱",
        textStyle: { bold: true, color: "#234B73", fontSize: "19px", typeface: "Microsoft YaHei" },
      },
      {
        run: "｜每个晶系各取 1 / 2 / 5 条真实谱进行少量再训练",
        textStyle: { bold: false, color: "#3F5368", fontSize: "19px", typeface: "Microsoft YaHei" },
      },
    ],
  ]);
  subtitle.text.fontSize = 19;
  subtitle.text.typeface = "Microsoft YaHei";
  subtitle.text.color = "#3F5368";
  subtitle.text.alignment = "left";
  subtitle.text.verticalAlignment = "middle";
  subtitle.text.wrap = "none";
  subtitle.text.autoFit = "shrinkText";
  subtitle.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  chart.categories = newCategories;
  chart.series.getItemAt(0).categories = newCategories;
  chart.series.getItemAt(1).categories = newCategories;

  const summary = presentation.resolve(summaryEntry.id);
  summary.text.set([
    [{ run: "① 三档真实标注预算均提升", textStyle: { bold: true, color: "#153E6A", fontSize: "23px", typeface: "Microsoft YaHei" } }],
    [
      { run: "平均约 ", textStyle: { bold: false, color: "#536779", fontSize: "19px", typeface: "Microsoft YaHei" } },
      { run: "+4.8 pp", textStyle: { bold: true, color: "#07579D", fontSize: "30px", typeface: "Microsoft YaHei" } },
    ],
    [{ run: "", textStyle: { fontSize: "14px", typeface: "Microsoft YaHei" } }],
    [{ run: "② 本方法用更少真实谱，\n也能达到相近甚至更好性能", textStyle: { bold: true, color: "#153E6A", fontSize: "22px", typeface: "Microsoft YaHei" } }],
    [{ run: "", textStyle: { fontSize: "10px", typeface: "Microsoft YaHei" } }],
    [{ run: "本方法 14 条 ≈ 基线 35 条", textStyle: { bold: true, color: "#234B73", fontSize: "20px", typeface: "Microsoft YaHei" } }],
    [{ run: "0.349 ≈ 0.356", textStyle: { bold: false, color: "#536779", fontSize: "19px", typeface: "Microsoft YaHei" } }],
    [{ run: "", textStyle: { fontSize: "8px", typeface: "Microsoft YaHei" } }],
    [{ run: "本方法 7 条 > 基线 14 条", textStyle: { bold: true, color: "#234B73", fontSize: "20px", typeface: "Microsoft YaHei" } }],
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

  await writeBlob(
    path.join(afterDir, "slide-06.png"),
    await presentation.export({ slide, format: "png", scale: 1 }),
  );
  for (let index = 0; index < presentation.slides.items.length; index += 1) {
    const item = presentation.slides.items[index];
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const layout = await item.export({ format: "layout" });
    await fs.writeFile(path.join(finalLayoutDir, `${stem}.layout.json`), await layout.text(), "utf8");
  }

  const after = await presentation.inspect({
    kind: "deck,slide,textbox,shape,chart,table,image,notes,layout",
    maxChars: 120000,
  });
  await fs.writeFile(path.join(tempDir, "after-inspect.ndjson"), after.ndjson, "utf8");
  const afterEntries = parseInspect(after.ndjson).filter((entry) => entry.slide === 6);
  const afterSubtitle = requireEntry(afterEntries, (entry) => entry.id === subtitleEntry.id, "updated P6 subtitle");
  const afterSummary = requireEntry(afterEntries, (entry) => entry.id === summaryEntry.id, "updated P6 summary");
  const afterChart = requireEntry(afterEntries, (entry) => entry.id === chartEntry.id, "updated P6 chart");

  if (afterSubtitle.text !== newSubtitle || afterSubtitle.textLines !== 1) {
    throw new Error(`Unexpected subtitle after edit: ${JSON.stringify(afterSubtitle)}`);
  }
  for (const phrase of [
    "② 本方法用更少真实谱，\n也能达到相近甚至更好性能",
    "本方法 14 条 ≈ 基线 35 条",
    "0.349 ≈ 0.356",
    "本方法 7 条 > 基线 14 条",
    "0.328 > 0.303",
  ]) {
    if (!afterSummary.text.includes(phrase)) throw new Error(`Missing summary phrase: ${phrase}`);
  }
  if (JSON.stringify(afterChart.bbox) !== JSON.stringify(chartEntry.bbox)) {
    throw new Error(`Chart geometry changed: ${JSON.stringify(afterChart.bbox)}`);
  }
  if (JSON.stringify(chart.categories) !== JSON.stringify(newCategories)) {
    throw new Error(`Chart categories not updated: ${JSON.stringify(chart.categories)}`);
  }
  if (!sameValues(chart.series.getItemAt(0).values, baselineExpected) || !sameValues(chart.series.getItemAt(1).values, methodExpected)) {
    throw new Error("Chart values changed during wording edit");
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
