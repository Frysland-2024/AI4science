import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p5_contrast_refine_20260828";
const finalPath = "E:/AI4science/outputs/XRD_导师汇报.pptx";
const renderDir = path.join(tempDir, "export-render");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(finalPath));
  if (presentation.slides.items.length !== 5) throw new Error("Final deck must have five slides");
  const slide = presentation.slides.items[4];
  await writeBlob(path.join(renderDir, "slide-05.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const inspect = await presentation.inspect({ kind: "slide,textbox,shape,chart,notes,layout", maxChars: 30000 });
  const p5 = inspect.ndjson
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line))
    .filter((entry) => entry.slide === 5)
    .map((entry) => JSON.stringify(entry))
    .join("\n");
  await fs.writeFile(path.join(tempDir, "export-p5-inspect.ndjson"), `${p5}\n`, "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
