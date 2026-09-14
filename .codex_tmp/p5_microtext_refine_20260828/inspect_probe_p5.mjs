import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p5_microtext_refine_20260828";
const sourcePath = path.join(tempDir, "source.pptx");
const renderDir = path.join(tempDir, "before-render");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function serializableKeys(value) {
  return Reflect.ownKeys(value ?? {}).filter((key) => typeof key === "string");
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 5) throw new Error("Expected five slides");

  const inspect = await presentation.inspect({ kind: "slide,textbox,shape,chart,notes,layout", maxChars: 30000 });
  const p5Entries = inspect.ndjson
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line))
    .filter((entry) => entry.slide === 5);
  await fs.writeFile(
    path.join(tempDir, "before-p5-inspect.ndjson"),
    `${p5Entries.map((entry) => JSON.stringify(entry)).join("\n")}\n`,
    "utf8",
  );

  const slide = presentation.slides.items[4];
  await writeBlob(path.join(renderDir, "slide-05.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, "slide-05.layout.json"), await layout.text(), "utf8");

  const chartEntry = p5Entries.find((entry) => entry.kind === "chart");
  if (!chartEntry) throw new Error("P5 chart not found");
  const chart = presentation.resolve(chartEntry.id);
  const methodSeries = chart.series.getItemAt(1);
  const overrides = methodSeries.dataLabelOverrides;
  const overrideProbe = [];
  for (let i = 0; i < 5; i += 1) {
    try {
      const item = overrides.getItemAt(i);
      overrideProbe.push({
        index: i,
        found: Boolean(item),
        keys: serializableKeys(item),
        text: item?.text,
        position: item?.position,
        textStyleKeys: serializableKeys(item?.textStyle),
        fontSize: item?.textStyle?.fontSize,
        fill: item?.textStyle?.fill,
      });
    } catch (error) {
      overrideProbe.push({ index: i, error: String(error) });
    }
  }
  const probe = {
    chartId: chartEntry.id,
    bbox: chartEntry.bbox,
    chartKeys: serializableKeys(chart),
    seriesCount: chart.series.items.length,
    baselineValues: chart.series.getItemAt(0).values,
    methodValues: methodSeries.values,
    overrideCollectionKeys: serializableKeys(overrides),
    overrideItemsLength: overrides.items?.length,
    overrideProbe,
  };
  await fs.writeFile(path.join(tempDir, "p5-chart-probe.json"), JSON.stringify(probe, null, 2), "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
