import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p8_unified_nextstep_20260831";
const sourcePath = path.join(tempDir, "source.pptx");
const outputPath = path.join(tempDir, "template-starter.pptx");
const layoutDir = path.join(tempDir, "template-starter-layout");

async function main() {
  await fs.mkdir(layoutDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 7) throw new Error("Expected seven source slides");

  const sourceSlide4 = presentation.slides.items[3];
  const appended = sourceSlide4.duplicate();
  appended.moveTo(7);
  if (presentation.slides.items.length !== 8) throw new Error("Failed to append duplicated source slide 4");

  const inspect = await presentation.inspect({
    kind: "deck,slide,textbox,shape,chart,table,image,notes,layout",
    maxChars: 200000,
  });
  await fs.writeFile(path.join(tempDir, "template-starter-inspect.ndjson"), inspect.ndjson, "utf8");

  for (let index = 0; index < presentation.slides.items.length; index += 1) {
    const slide = presentation.slides.items[index];
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(layoutDir, `${stem}.layout.json`), await layout.text(), "utf8");
  }

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);
  console.log(JSON.stringify({ outputPath, slideCount: presentation.slides.items.length }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
