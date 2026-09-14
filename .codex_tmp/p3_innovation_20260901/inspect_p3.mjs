import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p3_innovation_20260901";
const sourcePath = path.join(tmpDir, "source-deck.pptx");
const inspectDir = path.join(tmpDir, "before-p3");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(inspectDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  const slide = presentation.slides.items[2];
  if (!slide) throw new Error("Could not locate slide 3");
  await writeBlob(
    path.join(inspectDir, "slide-03.png"),
    await presentation.export({ slide, format: "png", scale: 1 }),
  );
  const layout = await slide.export({ format: "layout" });
  const layoutText = await layout.text();
  await fs.writeFile(path.join(inspectDir, "slide-03.layout.json"), layoutText, "utf8");
  const parsed = JSON.parse(layoutText);
  const summary = {
    slideCount: presentation.slides.items.length,
    slideId: slide.id,
    shapeCount: slide.shapes.items.length,
    chartCount: slide.charts.items.length,
    imageCount: slide.images.items.length,
    tableCount: slide.tables.items.length,
    placeholderSummary: slide.placeholders.summary(),
    elements: (parsed.elements ?? []).map((entry) => ({
      aid: entry.aid,
      kind: entry.kind,
      text: entry.text,
      bbox: entry.bbox,
      lineCount: entry.textLayout?.lineCount,
      fontSize: entry.textLayout?.fontSize,
    })),
  };
  await fs.writeFile(path.join(inspectDir, "slide-03.summary.json"), JSON.stringify(summary, null, 2), "utf8");
  console.log(JSON.stringify({
    slideCount: summary.slideCount,
    slideId: summary.slideId,
    shapeCount: summary.shapeCount,
    chartCount: summary.chartCount,
    imageCount: summary.imageCount,
    tableCount: summary.tableCount,
  }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
