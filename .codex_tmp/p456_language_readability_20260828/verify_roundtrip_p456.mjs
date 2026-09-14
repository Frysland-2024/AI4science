import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p456_language_readability_20260828");
const outputPath = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "roundtrip-render");
const finalLayoutDir = path.join(tempDir, "final-layout-all");

const p5Baseline = [0.6390, 0.6553, 0.6577, 0.6517, 0.6500];
const p5Method = [0.6939, 0.7167, 0.7075, 0.6967, 0.7118];
const p6Baseline = [0.284718979578149, 0.3026150816434789, 0.35546430676138274];
const p6Method = [0.3280396420899909, 0.3486411093591271, 0.40993113162853434];

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function requireEntry(entries, predicate, label) {
  const entry = entries.find(predicate);
  if (!entry) throw new Error(`Missing ${label}`);
  return entry;
}

function sameValues(actual, expected) {
  return Array.isArray(actual)
    && actual.length === expected.length
    && actual.every((value, index) => Math.abs(Number(value) - expected[index]) < 1e-9);
}

function sameBox(actual, expected) {
  return Array.isArray(actual)
    && actual.length === expected.length
    && actual.every((value, index) => Math.abs(Number(value) - expected[index]) < 0.1);
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(outputPath));
if (presentation.slides.items.length !== 6) throw new Error(`Expected 6 slides, found ${presentation.slides.items.length}`);

const snapshot = await presentation.inspect({
  kind: "slide,textbox,shape,chart,table,notes,layout",
  maxChars: 90000,
});
await fs.writeFile(path.join(tempDir, "roundtrip-inspect-all.ndjson"), snapshot.ndjson, "utf8");
const entries = parseInspect(snapshot.ndjson);

const p4Entries = entries.filter((entry) => entry.slide === 4);
requireEntry(p4Entries, (entry) => entry.text === "来自 Materials Project 的晶体结构", "P4 data-source label");
requireEntry(p4Entries, (entry) => (entry.text ?? "").includes("随机“换测量条件”"), "P4 online-generation explanation");
if (p4Entries.some((entry) => entry.text === "5 类扰动及其对谱图的影响")) throw new Error("P4 redundant heading still present");
const p4TableEntry = requireEntry(p4Entries, (entry) => entry.kind === "table" && entry.preview === "扰动类型 | 对谱图的影响", "P4 table");
if (!sameBox(p4TableEntry.bbox, [545, 142, 655, 470])) throw new Error(`Unexpected P4 table bbox: ${JSON.stringify(p4TableEntry.bbox)}`);

const p5Entries = entries.filter((entry) => entry.slide === 5);
requireEntry(p5Entries, (entry) => entry.text === "5 次重复训练全部提升，平均 Macro-F1 +5.46 个百分点", "P5 title");
requireEntry(p5Entries, (entry) => entry.text === "5 次重复训练均提升", "P5 summary");
requireEntry(
  p5Entries,
  (entry) => entry.text === "重复训练 5 次：数据、模型和训练设置相同，每次只改变随机初始化等随机因素。",
  "P5 repeated-training definition",
);
if (p5Entries.some((entry) => (entry.text ?? "").includes("Seed"))) throw new Error("Visible Seed wording remains on P5");
const p5ChartEntry = requireEntry(p5Entries, (entry) => entry.kind === "chart", "P5 chart");
if (!sameBox(p5ChartEntry.bbox, [62, 135, 880, 505])) throw new Error(`Unexpected P5 chart bbox: ${JSON.stringify(p5ChartEntry.bbox)}`);
const p5Chart = presentation.resolve(p5ChartEntry.id);
if (!sameValues(p5Chart.series.getItemAt(0).values, p5Baseline)) throw new Error("Round-trip P5 baseline values changed");
if (!sameValues(p5Chart.series.getItemAt(1).values, p5Method)) throw new Error("Round-trip P5 method values changed");
const expectedP5Categories = ["重复 1", "重复 2", "重复 3", "重复 4", "重复 5"];
for (let seriesIndex = 0; seriesIndex < 2; seriesIndex += 1) {
  const actualCategories = p5Chart.series.getItemAt(seriesIndex).categories;
  if (JSON.stringify(actualCategories) !== JSON.stringify(expectedP5Categories)) {
    throw new Error(`Unexpected P5 series ${seriesIndex + 1} categories: ${JSON.stringify(actualCategories)}`);
  }
}

const p6Entries = entries.filter((entry) => entry.slide === 6);
requireEntry(
  p6Entries,
  (entry) => entry.text === "RRUFF-301 真实谱少样本适配：仅用 7 条真实谱适配，也能提升 +4.33 pp",
  "P6 title",
);
requireEntry(
  p6Entries,
  (entry) => entry.text === "RRUFF-301：301 条真实实验 PXRD 谱｜每类仅用 1 / 2 / 5 条进行少样本适配",
  "P6 subtitle",
);
requireEntry(p6Entries, (entry) => entry.text === "仅 7 条真实谱", "P6 first-budget annotation");
const p6ChartEntry = requireEntry(p6Entries, (entry) => entry.kind === "chart", "P6 chart");
if (!sameBox(p6ChartEntry.bbox, [58, 196, 1166, 456])) throw new Error(`Unexpected P6 chart bbox: ${JSON.stringify(p6ChartEntry.bbox)}`);
const p6Chart = presentation.resolve(p6ChartEntry.id);
if (!sameValues(p6Chart.series.getItemAt(0).values, p6Baseline)) throw new Error("Round-trip P6 baseline values changed");
if (!sameValues(p6Chart.series.getItemAt(1).values, p6Method)) throw new Error("Round-trip P6 method values changed");

await fs.mkdir(renderDir, { recursive: true });
await fs.mkdir(finalLayoutDir, { recursive: true });
for (let slideNumber = 1; slideNumber <= 6; slideNumber += 1) {
  const slide = presentation.slides.items[slideNumber - 1];
  const stem = `slide-${String(slideNumber).padStart(2, "0")}`;
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(finalLayoutDir, `${stem}.layout.json`), await layout.text(), "utf8");
  if (slideNumber >= 4) {
    await writeBlob(path.join(renderDir, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
  }
}

const p456Lines = entries.filter((entry) => [4, 5, 6].includes(entry.slide));
await fs.writeFile(
  path.join(tempDir, "roundtrip-p456-inspect.ndjson"),
  `${p456Lines.map((entry) => JSON.stringify(entry)).join("\n")}\n`,
  "utf8",
);
