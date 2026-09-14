import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p7_cnrs_positioning_20260829";
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(tempDir, "staged-XRD_导师汇报.pptx");
const afterDir = path.join(tempDir, "after-render");
const finalLayoutDir = path.join(tempDir, "final-layout");

const oldTitle = "完全不用 CNRS 标注数据再训练，5 次重复结果仍全部提升";
const newTitle = "换到另一套真实实验谱直接测试，5 次重复结果仍全部提升";
const oldSubtitle = "CNRS-318｜独立真实实验谱来源｜不使用 CNRS 标注数据再训练，直接测试";
const newSubtitle = "CNRS-318：独立真实实验谱｜不使用 CNRS 数据调整模型，直接测试";
const oldBottom = "在另一套真实实验谱上直接测试，我的方法仍然表现出稳定增益。";
const newBottom = "不使用 CNRS 数据调整模型，直接测试仍有增益。";
const baselineExpected = [0.2067, 0.1469, 0.1842, 0.2149, 0.1892];
const methodExpected = [0.2212, 0.1756, 0.1971, 0.2295, 0.2120];

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
  const p7 = entries.filter((entry) => entry.slide === 7);

  const slideEntry = requireEntry(p7, (entry) => entry.kind === "slide", "slide 7");
  const titleEntry = requireEntry(p7, (entry) => entry.id === "sh/cbq1sv25" && entry.text === oldTitle, "P7 title");
  const subtitleEntry = requireEntry(p7, (entry) => entry.id === "sh/kzmdova1" && entry.text === oldSubtitle, "P7 subtitle");
  const summaryEntry = requireEntry(p7, (entry) => entry.id === "sh/zedcfa9g", "P7 right summary");
  const bottomEntry = requireEntry(p7, (entry) => entry.id === "sh/jedkn654" && entry.text === oldBottom, "P7 bottom takeaway");
  const chartEntry = requireEntry(p7, (entry) => entry.id === "ch/szmd4zyp", "P7 chart");

  const slide = presentation.resolve(slideEntry.id);
  const chart = presentation.resolve(chartEntry.id);
  if (!sameValues(chart.series.getItemAt(0).values, baselineExpected)) {
    throw new Error(`Baseline chart values changed: ${JSON.stringify(chart.series.getItemAt(0).values)}`);
  }
  if (!sameValues(chart.series.getItemAt(1).values, methodExpected)) {
    throw new Error(`Method chart values changed: ${JSON.stringify(chart.series.getItemAt(1).values)}`);
  }

  const title = presentation.resolve(titleEntry.id);
  title.text.replace(oldTitle, newTitle);

  const subtitle = presentation.resolve(subtitleEntry.id);
  subtitle.text.replace(oldSubtitle, newSubtitle);

  const summary = presentation.resolve(summaryEntry.id);
  summary.text.set([
    [{ run: "5 次重复全部提升", textStyle: { bold: false, color: "#536779", fontSize: "20px", typeface: "Microsoft YaHei" } }],
    [{ run: "", textStyle: { fontSize: "9px", typeface: "Microsoft YaHei" } }],
    [{ run: "平均 +1.87 pp", textStyle: { bold: true, color: "#153E6A", fontSize: "28px", typeface: "Microsoft YaHei" } }],
  ]);
  summary.text.typeface = "Microsoft YaHei";
  summary.text.color = "#153E6A";
  summary.text.alignment = "left";
  summary.text.verticalAlignment = "top";
  summary.text.wrap = "square";
  summary.text.autoFit = "shrinkText";
  summary.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  const bottom = presentation.resolve(bottomEntry.id);
  bottom.text.replace(oldBottom, newBottom);

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  await writeBlob(
    path.join(afterDir, "slide-07.png"),
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
  const afterP7 = parseInspect(after.ndjson).filter((entry) => entry.slide === 7);
  const finalTitle = requireEntry(afterP7, (entry) => entry.id === titleEntry.id, "updated P7 title");
  const finalSubtitle = requireEntry(afterP7, (entry) => entry.id === subtitleEntry.id, "updated P7 subtitle");
  const finalSummary = requireEntry(afterP7, (entry) => entry.id === summaryEntry.id, "updated P7 summary");
  const finalBottom = requireEntry(afterP7, (entry) => entry.id === bottomEntry.id, "updated P7 bottom takeaway");
  if (finalTitle.text !== newTitle || finalTitle.textLines !== 1) throw new Error(`Unexpected title: ${JSON.stringify(finalTitle)}`);
  if (finalSubtitle.text !== newSubtitle || finalSubtitle.textLines !== 1) throw new Error(`Unexpected subtitle: ${JSON.stringify(finalSubtitle)}`);
  if (finalSummary.text !== "5 次重复全部提升\n\n平均 +1.87 pp") throw new Error(`Unexpected summary: ${JSON.stringify(finalSummary)}`);
  if (finalBottom.text !== newBottom || finalBottom.textLines !== 1) throw new Error(`Unexpected bottom takeaway: ${JSON.stringify(finalBottom)}`);
  if (!sameValues(chart.series.getItemAt(0).values, baselineExpected) || !sameValues(chart.series.getItemAt(1).values, methodExpected)) {
    throw new Error("Chart values changed during wording edit");
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
