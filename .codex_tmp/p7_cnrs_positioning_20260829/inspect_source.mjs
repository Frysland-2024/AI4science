import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p7_cnrs_positioning_20260829";
const sourcePath = path.join(tempDir, "source.pptx");
const layoutDir = path.join(tempDir, "template-starter-layout");
const previewDir = path.join(tempDir, "before-render");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(layoutDir, { recursive: true });
  await fs.mkdir(previewDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 7) throw new Error("Expected seven slides");

  const inspect = await presentation.inspect({
    kind: "deck,slide,textbox,shape,chart,table,image,notes,layout",
    maxChars: 120000,
  });
  await fs.writeFile(path.join(tempDir, "template-inspect.ndjson"), inspect.ndjson, "utf8");

  for (let index = 0; index < presentation.slides.items.length; index += 1) {
    const slide = presentation.slides.items[index];
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(layoutDir, `${stem}.layout.json`), await layout.text(), "utf8");
  }

  const slide7 = presentation.slides.items[6];
  await writeBlob(
    path.join(previewDir, "slide-07.png"),
    await presentation.export({ slide: slide7, format: "png", scale: 1 }),
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
