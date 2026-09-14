import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const workspace = "E:/AI4science/.codex_tmp/mentor_deck_single_file_edit_20260828_p3p4";
const source = `${workspace}/source.pptx`;
const renderDir = `${workspace}/source-inspect`;

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()));
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
await fs.mkdir(renderDir, { recursive: true });

for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(`${renderDir}/${stem}.png`, await presentation.export({ slide, format: "png", scale: 1 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${renderDir}/${stem}.layout.json`, await layout.text());
}

await writeBlob(`${renderDir}/montage.webp`, await presentation.export({ format: "webp", montage: true, scale: 1 }));
const inspection = await presentation.inspect({
  kind: "deck,slide,textbox,shape,chart,image,notes,layout",
  maxChars: 50000,
});
await fs.writeFile(`${workspace}/source-inspect.ndjson`, inspection.ndjson);
await fs.writeFile(`${workspace}/source-structure.txt`, [
  `slides=${presentation.slides.items.length}`,
  `masters=${presentation.masters.items.length}`,
  `layouts=${presentation.layouts.items.length}`,
].join("\n"));
console.log(`Inspected ${presentation.slides.items.length} slides.`);
