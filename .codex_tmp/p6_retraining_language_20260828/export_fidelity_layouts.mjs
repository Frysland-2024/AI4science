import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p6_retraining_language_20260828");
const finalPptx = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const layoutDir = path.join(tempDir, "fidelity-final-layout");

async function main() {
  await fs.mkdir(layoutDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(finalPptx));
  if (presentation.slides.items.length !== 6) throw new Error("Expected six slides");
  for (let index = 0; index < presentation.slides.items.length; index += 1) {
    const layout = await presentation.slides.items[index].export({ format: "layout" });
    await fs.writeFile(
      path.join(layoutDir, `final-slide-${String(index + 1).padStart(2, "0")}.layout.json`),
      await layout.text(),
      "utf8",
    );
  }
  console.log(layoutDir);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
