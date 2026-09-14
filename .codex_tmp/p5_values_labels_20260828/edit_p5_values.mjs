import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p5_values_labels_20260828");
const starterPath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "after-render");

const baseline = [0.6390, 0.6553, 0.6577, 0.6517, 0.6500];
const method = [0.6939, 0.7167, 0.7075, 0.6967, 0.7118];
const gains = ["+5.48 pp", "+6.14 pp", "+4.99 pp", "+4.51 pp", "+6.18 pp"];
const categories = ["Seed 1", "Seed 2", "Seed 3", "Seed 4", "Seed 5"];
const groupCenters = [212, 371, 530, 689, 848];

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

function addGainLabel(slide, text, centerX, index) {
  const width = 108;
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: centerX - width / 2, top: 108, width, height: 24 },
    fill: "none",
    line: { style: "solid", fill: "#FFFFFF", width: 0 },
  });
  shape.name = `p5-gain-${index + 1}`;
  shape.text = text;
  shape.text.style = {
    fontSize: 18,
    bold: true,
    color: "#153E6A",
    alignment: "center",
    verticalAlignment: "middle",
    wrap: "none",
    autoFit: "shrinkText",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(starterPath));
  if (presentation.slides.items.length !== 5) throw new Error("Expected five slides");

  const inspect = await presentation.inspect({ kind: "slide,textbox,shape,chart,notes", maxChars: 30000 });
  const p5Entries = parseInspect(inspect.ndjson).filter((entry) => entry.slide === 5);
  const chartEntry = p5Entries.find((entry) => entry.kind === "chart");
  if (!chartEntry) throw new Error("P5 chart not found");
  if (JSON.stringify(chartEntry.bbox) !== JSON.stringify([62, 135, 880, 505])) {
    throw new Error(`Unexpected chart geometry: ${JSON.stringify(chartEntry.bbox)}`);
  }
  const oldChart = presentation.resolve(chartEntry.id);
  if (!sameValues(oldChart.series.getItemAt(0).values, baseline)) throw new Error("Baseline values changed");
  if (!sameValues(oldChart.series.getItemAt(1).values, method)) throw new Error("Method values changed");

  const slide = presentation.slides.items[4];
  slide.charts.deleteById(oldChart.id);
  slide.charts.add("bar", {
    position: { left: 62, top: 135, width: 880, height: 505 },
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
        values: method,
        fill: "#0B5EAA",
        line: { style: "solid", fill: "#084B87", width: 0.5 },
        dataLabelOverrides: method.map((value, idx) => ({
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
      gapWidth: 65,
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
      textStyle: { fontSize: 17, fill: "#4D5D6E" },
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
      max: 0.8,
      majorUnit: 0.2,
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

  gains.forEach((text, index) => addGainLabel(slide, text, groupCenters[index], index));

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  await writeBlob(path.join(renderDir, "slide-05.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, "slide-05.layout.json"), await layout.text(), "utf8");
  const after = await presentation.inspect({ kind: "slide,textbox,shape,chart,notes,layout", maxChars: 30000 });
  const p5Lines = parseInspect(after.ndjson)
    .filter((entry) => entry.slide === 5)
    .map((entry) => JSON.stringify(entry))
    .join("\n");
  await fs.writeFile(path.join(tempDir, "after-p5-inspect.ndjson"), `${p5Lines}\n`, "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
