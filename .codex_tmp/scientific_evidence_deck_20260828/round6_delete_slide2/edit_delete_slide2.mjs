import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const workspace = "E:/AI4science/.codex_tmp/scientific_evidence_deck_20260828/round6_delete_slide2";
const source = `${workspace}/source_round5.pptx`;
const output = "E:/AI4science/outputs/XRD_导师汇报_第六轮_删除第二页_2页_2026-08-28.pptx";
const renderDir = `${workspace}/final-render`;

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()));
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
if (presentation.slides.items.length !== 3) {
  throw new Error(`Expected 3 source slides, found ${presentation.slides.items.length}`);
}

const pageMarker = presentation.resolve("sh/cza94vmx");
pageMarker.text = "02 / 02";
presentation.slides.remove(1);

if (presentation.slides.items.length !== 2) {
  throw new Error(`Expected 2 final slides, found ${presentation.slides.items.length}`);
}

await fs.mkdir(renderDir, { recursive: true });
await fs.mkdir("E:/AI4science/outputs", { recursive: true });
for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  const png = await presentation.export({ slide, format: "png", scale: 1 });
  await writeBlob(`${renderDir}/${stem}.png`, png);
  await writeBlob(`E:/AI4science/outputs/XRD_导师汇报_第六轮_${stem}.png`, png);
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${renderDir}/${stem}.layout.json`, await layout.text());
}

await writeBlob(`${renderDir}/montage.webp`, await presentation.export({ format: "webp", montage: true, scale: 1 }));
const inspection = await presentation.inspect({
  kind: "deck,slide,textbox,shape,chart,image,notes,layout",
  maxChars: 30000,
});
await fs.writeFile(`${workspace}/final-inspect.ndjson`, inspection.ndjson);

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(output);
console.log(`Wrote ${output}`);
