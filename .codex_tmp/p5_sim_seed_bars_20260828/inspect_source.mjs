import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p5_sim_seed_bars_20260828";
const sourcePptx = path.join(tmpDir, "source.pptx");
const renderDir = path.join(tmpDir, "source-render");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePptx));
  const inspect = await presentation.inspect({
    kind: "slide,textbox,shape,image,table,chart,notes,layout",
    maxChars: 30000,
  });
  await fs.writeFile(path.join(tmpDir, "source-inspect.ndjson"), inspect.ndjson, "utf8");

  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(path.join(renderDir, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(renderDir, `${stem}.layout.json`), await layout.text(), "utf8");
  }

  await writeBlob(path.join(renderDir, "montage.webp"), await presentation.export({ format: "webp", montage: true, scale: 1 }));
  await fs.writeFile(path.join(tmpDir, "source-structure.txt"), JSON.stringify({
    slideCount: presentation.slides.items.length,
    masters: presentation.masters.items.map((master) => ({ id: master.id, name: master.name, placeholders: master.placeholders?.summary?.() ?? null })),
    layouts: presentation.layouts.items.map((layout) => ({ id: layout.id, name: layout.name, parentLayoutId: layout.parentLayoutId, placeholders: layout.placeholders?.summary?.() ?? null })),
  }, null, 2), "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
