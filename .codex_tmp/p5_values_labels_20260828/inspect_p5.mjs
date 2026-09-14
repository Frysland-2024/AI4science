import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p5_values_labels_20260828";
const sourcePath = path.join(tempDir, "source.pptx");
const renderDir = path.join(tempDir, "before-render");

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 5) throw new Error("Expected five slides");
  const slide = presentation.slides.items[4];
  const png = await presentation.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(path.join(renderDir, "slide-05.png"), new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, "slide-05.layout.json"), await layout.text(), "utf8");
  const inspect = await presentation.inspect({ kind: "slide,textbox,shape,chart,notes,layout", maxChars: 30000 });
  const p5 = inspect.ndjson
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line))
    .filter((entry) => entry.slide === 5)
    .map((entry) => JSON.stringify(entry))
    .join("\n");
  await fs.writeFile(path.join(tempDir, "before-p5-inspect.ndjson"), `${p5}\n`, "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
