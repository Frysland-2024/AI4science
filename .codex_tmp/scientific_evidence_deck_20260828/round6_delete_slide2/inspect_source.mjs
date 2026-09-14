import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const workspace = "E:/AI4science/.codex_tmp/scientific_evidence_deck_20260828/round6_delete_slide2";
const source = `${workspace}/source_round5.pptx`;
const renderDir = `${workspace}/source-inspect`;

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()));
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
await fs.mkdir(renderDir, { recursive: true });
console.log("slideCollectionProto", Reflect.ownKeys(Object.getPrototypeOf(presentation.slides)));
console.log("slideItemsType", presentation.slides.items?.constructor?.name, "isArray", Array.isArray(presentation.slides.items));
console.log("slideRemove", presentation.slides.remove.toString());

const snapshot = await presentation.inspect({
  kind: "deck,slide,textbox,shape,chart,image,notes,layout",
  maxChars: 30000,
});
await fs.writeFile(`${workspace}/source-inspect.ndjson`, snapshot.ndjson);

for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(`${renderDir}/${stem}.png`, await presentation.export({ slide, format: "png", scale: 1 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${renderDir}/${stem}.layout.json`, await layout.text());
}

const help = presentation.help("*", {
  search: "slides collection remove delete slide",
  include: ["index", "notes", "examples"],
  maxChars: 12000,
});
await fs.writeFile(`${workspace}/slides-remove-help.txt`, help.ndjson ?? String(help));
console.log(`slides=${presentation.slides.items.length}`);
