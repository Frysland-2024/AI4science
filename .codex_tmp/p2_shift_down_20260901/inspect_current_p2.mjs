import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const source = "E:/AI4science/.codex_tmp/p2_shift_down_20260901/source-current.pptx";
const outDir = "E:/AI4science/.codex_tmp/p2_shift_down_20260901/before-p2";

await fs.mkdir(outDir, { recursive: true });
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const slide = presentation.slides.items[1];

const png = await presentation.export({ slide, format: "png", scale: 1 });
await fs.writeFile(`${outDir}/slide-02.png`, new Uint8Array(await png.arrayBuffer()));
const layout = await slide.export({ format: "layout" });
await fs.writeFile(`${outDir}/slide-02.layout.json`, await layout.text());

const snapshot = await presentation.inspect({
  kind: "slide,textbox,shape,chart",
  include: "id,slide,name,bbox,textPreview,chartType",
  exclude: "preview,comments",
  maxChars: 30000,
});
await fs.writeFile(`${outDir}/inspect.ndjson`, snapshot.ndjson);
console.log(snapshot.ndjson.split("\n").filter((line) => line.includes('"slide":2')).join("\n"));
