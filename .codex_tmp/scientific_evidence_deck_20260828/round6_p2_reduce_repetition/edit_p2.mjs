import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const workspace = "E:/AI4science/.codex_tmp/scientific_evidence_deck_20260828/round6_p2_reduce_repetition";
const source = `${workspace}/template-starter.pptx`;
const output = "E:/AI4science/outputs/XRD_导师汇报_第六轮_P2减重复_3页_2026-08-28.pptx";
const renderDir = `${workspace}/final-render`;

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()));
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
if (presentation.slides.items.length !== 3) {
  throw new Error(`Expected 3 source slides, found ${presentation.slides.items.length}`);
}

const beforeSlide = presentation.resolve("sl/hwbqtkby");
await fs.mkdir(renderDir, { recursive: true });
await writeBlob(`${renderDir}/before-slide-02.png`, await presentation.export({ slide: beforeSlide, format: "png", scale: 1 }));
const beforeLayout = await beforeSlide.export({ format: "layout" });
await fs.writeFile(`${renderDir}/before-slide-02.layout.json`, await beforeLayout.text());

const title = presentation.resolve("sh/nu58f2hs");
title.text = "同一晶体，仅改变测量条件，谱形就会明显变化";

const conclusion = presentation.resolve("sh/mtwrmxg7");
conclusion.text = "变化来自测量，而不是晶体结构。";
conclusion.text.style = {
  typeface: "Microsoft YaHei",
  fontSize: 20,
  bold: false,
  color: "#657384",
  alignment: "center",
  verticalAlignment: "middle",
  lineSpacing: 1.06,
  wrap: "square",
  autoFit: "none",
  insets: { top: 0, right: 0, bottom: 0, left: 0 },
};

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
