import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p6_rruff_reframe_20260828";

async function exportDeckLayouts(pptxPath, outDir, inspectPath) {
  await fs.mkdir(outDir, { recursive: true });
  const deck = await PresentationFile.importPptx(await FileBlob.load(pptxPath));
  if (deck.slides.items.length !== 6) throw new Error(`Expected 6 slides in ${pptxPath}`);
  for (const [index, slide] of deck.slides.items.entries()) {
    const layout = await slide.export({ format: "layout" });
    const stem = `slide-${String(index + 1).padStart(2, "0")}.layout.json`;
    await fs.writeFile(path.join(outDir, stem), await layout.text(), "utf8");
  }
  const inspect = await deck.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 90000,
  });
  await fs.writeFile(inspectPath, inspect.ndjson, "utf8");
}

await exportDeckLayouts(
  path.join(tempDir, "source.pptx"),
  path.join(tempDir, "template-starter-layout"),
  path.join(tempDir, "source-inspect-for-fidelity.ndjson"),
);
await exportDeckLayouts(
  "E:/AI4science/outputs/XRD_导师汇报.pptx",
  path.join(tempDir, "final-layout-all"),
  path.join(tempDir, "final-inspect-all.ndjson"),
);
