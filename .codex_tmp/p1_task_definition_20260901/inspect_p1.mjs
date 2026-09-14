import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p1_task_definition_20260901";
const sourcePath = path.join(tmpDir, "source-deck.pptx");
const inspectDir = path.join(tmpDir, "before-p1");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(inspectDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  const slide = presentation.slides.items[0];
  if (!slide) throw new Error("Could not locate slide 1");

  await writeBlob(
    path.join(inspectDir, "slide-01.png"),
    await presentation.export({ slide, format: "png", scale: 1 }),
  );
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(inspectDir, "slide-01.layout.json"), await layout.text(), "utf8");

  const summary = {
    slideCount: presentation.slides.items.length,
    slideSize: presentation.slideSize,
    slideId: slide.id,
    shapeCount: slide.shapes.items.length,
    chartCount: slide.charts.items.length,
    imageCount: slide.images.items.length,
    tableCount: slide.tables.items.length,
    placeholderSummary: slide.placeholders.summary(),
    layoutId: slide.layoutId ?? null,
  };
  await fs.writeFile(path.join(inspectDir, "slide-01.summary.json"), JSON.stringify(summary, null, 2), "utf8");
  console.log(JSON.stringify(summary));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
