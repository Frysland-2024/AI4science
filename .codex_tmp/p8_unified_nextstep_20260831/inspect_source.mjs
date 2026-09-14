import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p8_unified_nextstep_20260831";
const sourcePath = path.join(tempDir, "source.pptx");
const layoutDir = path.join(tempDir, "source-layout");

async function main() {
  await fs.mkdir(layoutDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  const inspect = await presentation.inspect({
    kind: "deck,slide,textbox,shape,chart,table,image,notes,layout",
    maxChars: 180000,
  });
  await fs.writeFile(path.join(tempDir, "template-inspect.ndjson"), inspect.ndjson, "utf8");

  for (let index = 0; index < presentation.slides.items.length; index += 1) {
    const slide = presentation.slides.items[index];
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(layoutDir, `${stem}.layout.json`), await layout.text(), "utf8");
  }

  console.log(JSON.stringify({ slideCount: presentation.slides.items.length }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
