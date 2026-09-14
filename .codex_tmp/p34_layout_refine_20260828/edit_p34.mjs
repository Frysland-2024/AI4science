import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p34_layout_refine_20260828");
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "after-render");
const finalLayoutDir = path.join(tempDir, "final-layout");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function requireEntry(entries, predicate, label) {
  const entry = entries.find(predicate);
  if (!entry) throw new Error(`Could not locate ${label}`);
  return entry;
}

function byText(entries, slideNumber, text, label = text) {
  return requireEntry(entries, (entry) => entry.slide === slideNumber && entry.text === text, label);
}

function byBox(entries, slideNumber, kind, bbox, label) {
  return requireEntry(
    entries,
    (entry) => entry.slide === slideNumber && entry.kind === kind &&
      Array.isArray(entry.bbox) && bbox.every((value, index) => entry.bbox[index] === value),
    label,
  );
}

function resolve(presentation, entry) {
  return presentation.resolve(entry.id);
}

function move(element, position) {
  element.position = position;
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  await fs.mkdir(finalLayoutDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 5) {
    throw new Error(`Expected 5 slides, found ${presentation.slides.items.length}`);
  }

  const snapshot = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes",
    maxChars: 40000,
  });
  const entries = parseInspect(snapshot.ndjson);

  // ------------------------------
  // Slide 3: move the existing method chain downward; no new content.
  // ------------------------------
  move(resolve(presentation, byText(entries, 3, "同一晶体结构")),
    { left: 518, top: 128, width: 244, height: 34 });

  move(resolve(presentation, byBox(entries, 3, "shape", [640, 151, 0, 22], "P3 root vertical connector")),
    { left: 640, top: 162, width: 0, height: 22 });
  move(resolve(presentation, byBox(entries, 3, "shape", [330, 173, 620, 0], "P3 horizontal branch")),
    { left: 330, top: 184, width: 620, height: 0 });
  move(resolve(presentation, byBox(entries, 3, "shape", [330, 173, 0, 12], "P3 left branch leg")),
    { left: 330, top: 184, width: 0, height: 12 });
  move(resolve(presentation, byBox(entries, 3, "shape", [950, 173, 0, 12], "P3 right branch leg")),
    { left: 950, top: 184, width: 0, height: 12 });
  move(resolve(presentation, byBox(entries, 3, "shape", [320, 181, 20, 24], "P3 left top arrow")),
    { left: 320, top: 192, width: 20, height: 24 });
  move(resolve(presentation, byBox(entries, 3, "shape", [940, 181, 20, 24], "P3 right top arrow")),
    { left: 940, top: 192, width: 20, height: 24 });

  const labelA = resolve(presentation, byText(entries, 3, "受测量扰动的谱 A"));
  labelA.text = "受测量扰动的\n谱 A";
  move(labelA, { left: 82, top: 196, width: 220, height: 52 });
  labelA.text.fontSize = 20;
  labelA.text.alignment = "center";
  labelA.text.verticalAlignment = "middle";
  labelA.text.wrap = "square";
  labelA.text.autoFit = "none";
  labelA.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  const labelB = resolve(presentation, byText(entries, 3, "受测量扰动的谱 B"));
  labelB.text = "受测量扰动的\n谱 B";
  move(labelB, { left: 978, top: 196, width: 220, height: 52 });
  labelB.text.fontSize = 20;
  labelB.text.alignment = "center";
  labelB.text.verticalAlignment = "middle";
  labelB.text.wrap = "square";
  labelB.text.autoFit = "none";
  labelB.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  move(resolve(presentation, byBox(entries, 3, "chart", [160, 202, 340, 100], "P3 chart A")),
    { left: 160, top: 250, width: 340, height: 100 });
  move(resolve(presentation, byBox(entries, 3, "chart", [780, 202, 340, 100], "P3 chart B")),
    { left: 780, top: 250, width: 340, height: 100 });

  move(resolve(presentation, byBox(entries, 3, "shape", [320, 296, 20, 35], "P3 left arrow to model")),
    { left: 320, top: 345, width: 20, height: 38 });
  move(resolve(presentation, byBox(entries, 3, "shape", [940, 296, 20, 35], "P3 right arrow to model")),
    { left: 940, top: 345, width: 20, height: 38 });

  move(resolve(presentation, byBox(entries, 3, "shape", [260, 331, 760, 43], "P3 model bridge")),
    { left: 260, top: 383, width: 760, height: 36 });
  const modelText = resolve(presentation, byText(entries, 3, "同一个模型"));
  move(modelText, { left: 410, top: 388, width: 460, height: 26 });
  modelText.text.verticalAlignment = "middle";

  move(resolve(presentation, byBox(entries, 3, "shape", [490, 374, 22, 42], "P3 left arrow to prediction")),
    { left: 490, top: 419, width: 22, height: 42 });
  move(resolve(presentation, byBox(entries, 3, "shape", [768, 374, 22, 42], "P3 right arrow to prediction")),
    { left: 768, top: 419, width: 22, height: 42 });

  const prediction = resolve(presentation, byText(entries, 3, "预测 A   ≈   预测 B"));
  move(prediction, { left: 190, top: 456, width: 900, height: 134 });
  prediction.text.fontSize = 76;
  prediction.text.alignment = "center";
  prediction.text.verticalAlignment = "middle";
  prediction.text.wrap = "none";
  prediction.text.autoFit = "none";

  // ------------------------------
  // Slide 4: preserve the left data block; replace only the loose right list.
  // ------------------------------
  const slide4 = presentation.slides.items[3];
  const sectionHeading = resolve(presentation, byText(entries, 4, "峰位偏移　　峰整体左右移动"));
  sectionHeading.text = "5 类扰动及其对谱图的影响";
  move(sectionHeading, { left: 545, top: 142, width: 655, height: 30 });
  sectionHeading.text.fontSize = 18;
  sectionHeading.text.bold = true;
  sectionHeading.text.color = "#153E6A";
  sectionHeading.text.alignment = "left";
  sectionHeading.text.verticalAlignment = "middle";
  sectionHeading.text.wrap = "none";
  sectionHeading.text.autoFit = "none";
  sectionHeading.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  for (const text of [
    "峰展宽　　　峰变宽、相邻峰可能重叠",
    "背景变化　　基线及背景形状发生变化",
    "计数噪声　　谱线上出现随机波动",
    "择优取向　　各衍射峰的相对强度改变",
  ]) {
    resolve(presentation, byText(entries, 4, text)).delete();
  }

  const table = slide4.tables.add({
    rows: 6,
    columns: 2,
    left: 545,
    top: 184,
    width: 655,
    height: 396,
    columnWidths: [180, 475],
    values: [
      ["扰动类型", "对谱图的影响"],
      ["峰位偏移", "各峰整体左右移动"],
      ["峰展宽", "峰变宽，相邻峰更易重叠"],
      ["背景变化", "基线或背景形状发生变化"],
      ["计数噪声", "谱线上出现随机波动"],
      ["择优取向", "各衍射峰的相对强度改变"],
    ],
  });
  table.rows[0].height = 46;
  for (let row = 1; row < 6; row += 1) table.rows[row].height = 70;
  table.borders.assign({ style: "solid", fill: "#D8E1E9", width: 1 });

  for (let row = 0; row < 6; row += 1) {
    for (let col = 0; col < 2; col += 1) {
      const cell = table.getCell(row, col);
      cell.fill = row === 0 ? "#EAF0F5" : (col === 0 ? "#F6F8FA" : "#FFFFFF");
      cell.text.style = {
        fontSize: row === 0 ? 17 : 18,
        bold: row === 0 || col === 0,
        color: row === 0 || col === 0 ? "#153E6A" : "#66788A",
        alignment: "left",
        verticalAlignment: "middle",
        wrap: "square",
        autoFit: "shrinkText",
        insets: { top: 5, right: 13, bottom: 5, left: 13 },
      };
    }
  }

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  // Render and inspect only the two slides named in this round.
  for (const slideNumber of [3, 4]) {
    const slide = presentation.slides.items[slideNumber - 1];
    const stem = `slide-${String(slideNumber).padStart(2, "0")}`;
    await writeBlob(path.join(renderDir, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
    const layout = await slide.export({ format: "layout" });
    const layoutText = await layout.text();
    await fs.writeFile(path.join(renderDir, `${stem}.layout.json`), layoutText, "utf8");
    await fs.writeFile(path.join(finalLayoutDir, `${stem}.layout.json`), layoutText, "utf8");
  }

  const finalInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes",
    maxChars: 40000,
  });
  const finalEntries = parseInspect(finalInspect.ndjson)
    .filter((entry) => entry.slide === 3 || entry.slide === 4);
  await fs.writeFile(path.join(tempDir, "final-p34-inspect.ndjson"), finalEntries.map((entry) => JSON.stringify(entry)).join("\n") + "\n", "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
