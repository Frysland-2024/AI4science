import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "file:///C:/Users/Lenovo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const deckPath = "E:/AI4science/outputs/XRD_导师汇报.pptx";
const tempDir = "E:/AI4science/.codex_tmp/p6_rruff_fewshot_20260828";
const renderDir = path.join(tempDir, "roundtrip-p6");
const expectedBaseline = [0.284718979578149, 0.3026150816434789, 0.35546430676138274];
const expectedConsistency = [0.3280396420899909, 0.3486411093591271, 0.40993113162853434];

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
  const presentation = await PresentationFile.importPptx(await FileBlob.load(deckPath));
  if (presentation.slides.items.length !== 6) throw new Error("Expected six slides after round-trip import");

  const inspect = await presentation.inspect({ kind: "slide,textbox,shape,chart,notes,layout", maxChars: 60000 });
  const entries = parseInspect(inspect.ndjson);
  const p6Entries = entries.filter((entry) => entry.slide === 6);
  const chartEntry = p6Entries.find((entry) => entry.kind === "chart" && entry.name === "p6-rruff-fewshot-bars");
  if (!chartEntry) throw new Error("Round-trip P6 chart not found");
  const chart = presentation.resolve(chartEntry.id);
  if (!sameValues(chart.series.getItemAt(0).values, expectedBaseline)) throw new Error("Round-trip baseline values changed");
  if (!sameValues(chart.series.getItemAt(1).values, expectedConsistency)) throw new Error("Round-trip consistency values changed");

  const p6 = presentation.slides.items[5];
  await writeBlob(path.join(renderDir, "slide-06.png"), await presentation.export({ slide: p6, format: "png", scale: 1 }));
  const layout = await p6.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, "slide-06.layout.json"), await layout.text(), "utf8");
  await fs.writeFile(
    path.join(tempDir, "roundtrip-p6-inspect.ndjson"),
    `${p6Entries.map((entry) => JSON.stringify(entry)).join("\n")}\n`,
    "utf8",
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
