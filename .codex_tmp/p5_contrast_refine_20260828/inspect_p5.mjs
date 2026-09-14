import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p5_contrast_refine_20260828";
const sourcePath = path.join(tempDir, "source.pptx");
const renderDir = path.join(tempDir, "before-render");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 5) {
    throw new Error(`Expected five slides, found ${presentation.slides.items.length}`);
  }

  const slide = presentation.slides.items[4];
  const inspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 30000,
  });
  const p5Lines = inspect.ndjson
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line))
    .filter((entry) => entry.slide === 5)
    .map((entry) => JSON.stringify(entry))
    .join("\n");
  await fs.writeFile(path.join(tempDir, "before-p5-inspect.ndjson"), `${p5Lines}\n`, "utf8");
  await writeBlob(path.join(renderDir, "slide-05.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, "slide-05.layout.json"), await layout.text(), "utf8");

  const chartEntry = p5Lines
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line))
    .find((entry) => entry.kind === "chart");
  if (!chartEntry) throw new Error("P5 chart was not found");
  const chart = presentation.resolve(chartEntry.id);
  const summary = {
    id: chartEntry.id,
    bbox: chartEntry.bbox,
    chartType: chart.chartType,
    barOptions: chart.barOptions,
    hasLegend: chart.hasLegend,
    legend: chart.legend,
    xAxis: chart.xAxis,
    yAxis: chart.yAxis,
    series: chart.series.items.map((series) => ({
      name: series.name,
      fill: series.fill,
      line: series.line,
      dataLabelOverrides: series.dataLabelOverrides,
    })),
  };
  await fs.writeFile(path.join(tempDir, "before-chart-properties.json"), JSON.stringify(summary, null, 2), "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
