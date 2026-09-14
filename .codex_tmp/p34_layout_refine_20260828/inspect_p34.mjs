import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p34_layout_refine_20260828";
const sourcePath = path.join(tempDir, "source.pptx");
const renderDir = path.join(tempDir, "before-render");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
const inspect = await presentation.inspect({
  kind: "slide,textbox,shape,chart,table,notes,layout",
  maxChars: 40000,
});
const entries = inspect.ndjson.split(/\r?\n/).filter(Boolean).map(JSON.parse);
const selected = entries.filter((entry) => entry.slide === 3 || entry.slide === 4);
await fs.writeFile(path.join(tempDir, "source-p34-inspect.ndjson"), selected.map((entry) => JSON.stringify(entry)).join("\n") + "\n", "utf8");

const details = [];
for (const entry of selected.filter((item) => ["textbox", "shape", "chart", "table"].includes(item.kind))) {
  const element = presentation.resolve(entry.id);
  details.push({
    entry,
    internalId: element.id,
    name: element.name ?? null,
    position: element.position ?? element.frame ?? null,
    geometry: element.geometry ?? null,
    fill: element.fill ?? null,
    line: element.line ?? null,
    textStyle: element.text ? {
      fontSize: element.text.fontSize,
      fontSizePt: element.text.fontSizePt,
      bold: element.text.bold,
      color: element.text.color,
      fill: element.text.fill,
      alignment: element.text.alignment,
      verticalAlignment: element.text.verticalAlignment,
      wrap: element.text.wrap,
      autoFit: element.text.autoFit,
      insets: element.text.insets,
      typeface: element.text.typeface,
    } : null,
  });
}
await fs.writeFile(path.join(tempDir, "source-p34-details.json"), JSON.stringify(details, null, 2), "utf8");

await fs.mkdir(renderDir, { recursive: true });
for (const slideNumber of [3, 4]) {
  const slide = presentation.slides.items[slideNumber - 1];
  const stem = `slide-${String(slideNumber).padStart(2, "0")}`;
  await writeBlob(path.join(renderDir, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, `${stem}.layout.json`), await layout.text(), "utf8");
}
