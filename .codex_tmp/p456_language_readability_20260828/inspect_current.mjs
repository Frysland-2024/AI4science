import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p456_language_readability_20260828";
const sourcePath = path.join(tempDir, "source.pptx");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
if (presentation.slides.items.length !== 6) throw new Error(`Expected 6 slides, found ${presentation.slides.items.length}`);

const snapshot = await presentation.inspect({
  kind: "slide,textbox,shape,chart,table,notes,layout",
  maxChars: 80000,
});
await fs.writeFile(path.join(tempDir, "source-inspect.ndjson"), snapshot.ndjson, "utf8");

const beforeDir = path.join(tempDir, "before-render");
await fs.mkdir(beforeDir, { recursive: true });
for (const slideNumber of [4, 5, 6]) {
  const slide = presentation.slides.items[slideNumber - 1];
  const stem = `slide-${String(slideNumber).padStart(2, "0")}`;
  await writeBlob(path.join(beforeDir, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(beforeDir, `${stem}.layout.json`), await layout.text(), "utf8");
}
