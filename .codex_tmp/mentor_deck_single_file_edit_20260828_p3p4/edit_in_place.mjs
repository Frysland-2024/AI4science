import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const workspace = "E:/AI4science/.codex_tmp/mentor_deck_single_file_edit_20260828_p3p4";
const source = `${workspace}/template-starter.pptx`;
const output = "E:/AI4science/outputs/XRD_导师汇报.pptx";
const renderDir = `${workspace}/final-render`;

const BASE_BLUE = "#285F97";
const PERTURB_ORANGE = "#E77A25";

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()));
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
if (presentation.slides.items.length !== 4) {
  throw new Error(`Expected 4 slides, found ${presentation.slides.items.length}`);
}

const labelA = presentation.resolve("sh/a5c3ql8z");
labelA.text = "受测量扰动的谱 A";
labelA.position = { left: 100, top: 176, width: 230, height: 28 };

const labelB = presentation.resolve("sh/x8nml0ra");
labelB.text = "受测量扰动的谱 B";
labelB.position = { left: 950, top: 176, width: 230, height: 28 };

presentation.resolve("sh/p0batw72").text = "蓝色：基准谱　橙色：扰动谱";
presentation.resolve("sh/g36tgryd").text = "按晶体结构划分，避免同一晶体的不同谱\n同时出现在训练集和测试集。";

const chartIds = ["ch/etsjm14b", "ch/fe10f6lw", "ch/gfu1obm1", "ch/1g3ihw3m", "ch/6psjih4z"];
for (const id of chartIds) {
  const chart = presentation.resolve(id);
  if (chart.series.length !== 2) throw new Error(`Expected 2 series in ${id}, found ${chart.series.length}`);
  chart.series.getItemAt(0).line = { style: "solid", fill: BASE_BLUE, width: 1.8 };
  chart.series.getItemAt(1).line = { style: "solid", fill: PERTURB_ORANGE, width: 2.4 };
}

const notes = presentation.resolve("nt/jyx0ra1s");
notes.setText(notes.text.replace(
  "灰色为 level0 基准，蓝色为对应扰动缓存。",
  "蓝色为 level0 基准，橙色为对应扰动缓存。",
));

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
await fs.writeFile(`${workspace}/final-inspect.ndjson`, inspection.ndjson);

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(output);
console.log(`Updated ${output}`);
