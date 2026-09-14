import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p6_retraining_language_20260828");
const finalPptx = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "roundtrip-p6");

const expectedTitle = "RRUFF-301 真实谱验证：仅用 7 条真实谱再训练，也能提升 +4.33 pp";
const expectedSubtitle = "先用模拟谱训练模型，再分别用每类 1 / 2 / 5 条真实谱进行少量再训练";
const expectedBaseline = [0.284718979578149, 0.3026150816434789, 0.35546430676138274];
const expectedMethod = [0.3280396420899909, 0.3486411093591271, 0.40993113162853434];

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
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
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(finalPptx));
  if (presentation.slides.items.length !== 6) throw new Error("Expected six slides after roundtrip");

  const inspected = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 80000,
  });
  const entries = parseInspect(inspected.ndjson);
  const p6 = entries.filter((entry) => entry.slide === 6);

  const title = p6.find((entry) => entry.id === "sh/u1kbu1ov");
  if (title?.text !== expectedTitle) throw new Error(`P6 title mismatch after roundtrip: ${title?.text}`);

  const subtitle = p6.find((entry) => entry.id === "sh/47mt0b6x");
  if (subtitle?.text !== expectedSubtitle) throw new Error(`P6 subtitle mismatch after roundtrip: ${subtitle?.text}`);

  const annotation = p6.find((entry) => entry.id === "sh/5svutgni");
  if (annotation?.text !== "仅 7 条真实谱") throw new Error("P6 first-budget annotation changed unexpectedly");

  const chartEntry = p6.find((entry) => entry.id === "ch/8va107ql");
  if (!chartEntry || JSON.stringify(chartEntry.bbox) !== JSON.stringify([58, 196, 1166, 456])) {
    throw new Error(`P6 chart geometry changed: ${JSON.stringify(chartEntry?.bbox)}`);
  }
  const chart = presentation.resolve(chartEntry.id);
  if (!sameValues(chart.series.getItemAt(0).values, expectedBaseline)) throw new Error("P6 baseline values changed");
  if (!sameValues(chart.series.getItemAt(1).values, expectedMethod)) throw new Error("P6 method values changed");

  const slide6 = presentation.slides.items[5];
  await writeBlob(
    path.join(renderDir, "slide-06.png"),
    await presentation.export({ slide: slide6, format: "png", scale: 1 }),
  );
  const layout = await slide6.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, "slide-06.layout.json"), await layout.text(), "utf8");
  await fs.writeFile(
    path.join(tempDir, "roundtrip-p6-inspect.ndjson"),
    `${p6.map((entry) => JSON.stringify(entry)).join("\n")}\n`,
    "utf8",
  );

  console.log("P6 roundtrip verification passed");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
