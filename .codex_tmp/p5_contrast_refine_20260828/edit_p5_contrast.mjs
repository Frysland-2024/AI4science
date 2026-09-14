import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p5_contrast_refine_20260828");
const starterPath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "after-render");

const baselineExpected = [0.6390, 0.6553, 0.6577, 0.6517, 0.6500];
const methodExpected = [0.6939, 0.7167, 0.7075, 0.6967, 0.7118];

function parseInspect(ndjson) {
  return ndjson
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
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
  const presentation = await PresentationFile.importPptx(await FileBlob.load(starterPath));
  if (presentation.slides.items.length !== 5) {
    throw new Error(`Expected five slides, found ${presentation.slides.items.length}`);
  }

  const beforeInspect = await presentation.inspect({ kind: "slide,textbox,shape,chart,notes", maxChars: 30000 });
  const p5Entries = parseInspect(beforeInspect.ndjson).filter((entry) => entry.slide === 5);
  const chartEntry = p5Entries.find((entry) => entry.kind === "chart");
  if (!chartEntry) throw new Error("P5 chart was not found");
  if (JSON.stringify(chartEntry.bbox) !== JSON.stringify([62, 135, 880, 505])) {
    throw new Error(`Unexpected P5 chart geometry: ${JSON.stringify(chartEntry.bbox)}`);
  }

  const chart = presentation.resolve(chartEntry.id);
  const baselineSeries = chart.series.getItemAt(0);
  const methodSeries = chart.series.getItemAt(1);
  if (!baselineSeries || !methodSeries) throw new Error("Expected two chart series");
  if (!sameValues(baselineSeries.values, baselineExpected)) {
    throw new Error(`Baseline data changed unexpectedly: ${JSON.stringify(baselineSeries.values)}`);
  }
  if (!sameValues(methodSeries.values, methodExpected)) {
    throw new Error(`Method data changed unexpectedly: ${JSON.stringify(methodSeries.values)}`);
  }

  // Contrast-only edit. Orange remains reserved for measurement perturbations.
  baselineSeries.fill = "#CDD2D7";
  baselineSeries.line = { style: "solid", fill: "#BFC4C9", width: 0.5 };
  methodSeries.fill = "#0B5EAA";
  methodSeries.line = { style: "solid", fill: "#084B87", width: 0.5 };

  // Reapply the approved axis configuration verbatim, changing only gridline color.
  chart.yAxis = {
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
    majorGridlines: { style: "solid", fill: "#EEF1F4", width: 1 },
    minorGridlines: null,
  };

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  const slide = presentation.slides.items[4];
  await writeBlob(path.join(renderDir, "slide-05.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, "slide-05.layout.json"), await layout.text(), "utf8");

  const afterInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 30000,
  });
  const p5Lines = parseInspect(afterInspect.ndjson)
    .filter((entry) => entry.slide === 5)
    .map((entry) => JSON.stringify(entry))
    .join("\n");
  await fs.writeFile(path.join(tempDir, "after-p5-inspect.ndjson"), `${p5Lines}\n`, "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
