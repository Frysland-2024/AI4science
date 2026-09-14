import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p4_full_sampling_line_20260828");
const starterPath = path.join(tempDir, "template-starter.pptx");
const stagedPath = path.join(tempDir, "staged-XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "after-render");
const layoutDir = path.join(tempDir, "final-layout");

const oldText = [
  "按晶体结构划分",
  "同一晶体的不同谱始终留在同一数据集",
  "",
  "训练时实时生成谱",
  "每次随机采样一组测量扰动 → 生成不同训练谱",
].join("\n");

const newText = [
  "按晶体结构划分",
  "同一晶体的不同谱始终留在同一数据集",
  "",
  "训练时实时生成谱",
  "同一晶体 → 每次随机采样一组测量扰动 → 生成不同训练谱",
].join("\n");

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function requireEntry(entries, predicate, label) {
  const entry = entries.find(predicate);
  if (!entry) throw new Error(`Could not locate ${label}`);
  return entry;
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function setBaseTextFrame(shape) {
  shape.text.alignment = "left";
  shape.text.verticalAlignment = "top";
  shape.text.wrap = "square";
  shape.text.autoFit = "none";
  shape.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  await fs.mkdir(layoutDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(starterPath));
  if (presentation.slides.items.length !== 6) throw new Error("Expected six slides");

  const inspected = await presentation.inspect({
    kind: "slide,textbox,shape,table,chart,notes,layout",
    maxChars: 80000,
  });
  const entries = parseInspect(inspected.ndjson);
  const p4 = entries.filter((entry) => entry.slide === 4);
  const targetEntry = requireEntry(p4, (entry) => entry.id === "sh/g36tgryd", "P4 lower-left textbox");
  if (targetEntry.text !== oldText) throw new Error(`Unexpected source text: ${targetEntry.text}`);

  const table = requireEntry(p4, (entry) => entry.id === "tb/mhovq5k3", "P4 disturbance table");
  if (table.rows !== 6 || table.cols !== 2 || table.preview !== "扰动类型 | 对谱图的影响") {
    throw new Error("P4 table structure changed before edit");
  }

  const target = presentation.resolve(targetEntry.id);
  target.text.set([
    [{ run: "按晶体结构划分", textStyle: { bold: true, color: "#153E6A", fontSize: "23px", typeface: "Microsoft YaHei" } }],
    [{ run: "同一晶体的不同谱始终留在同一数据集", textStyle: { bold: false, color: "#657384", fontSize: "19px", typeface: "Microsoft YaHei" } }],
    [{ run: "", textStyle: { fontSize: "10px", typeface: "Microsoft YaHei" } }],
    [{ run: "训练时实时生成谱", textStyle: { bold: true, color: "#153E6A", fontSize: "23px", typeface: "Microsoft YaHei" } }],
    [
      { run: "同一晶体 → ", textStyle: { bold: false, color: "#657384", fontSize: "16px", typeface: "Microsoft YaHei" } },
      { run: "每次随机采样一组测量扰动", textStyle: { bold: true, color: "#E07A2A", fontSize: "16px", typeface: "Microsoft YaHei" } },
      { run: " → 生成不同训练谱", textStyle: { bold: false, color: "#657384", fontSize: "16px", typeface: "Microsoft YaHei" } },
    ],
  ]);
  setBaseTextFrame(target);

  const afterInspect = await presentation.inspect({
    target: { id: targetEntry.id, beforeLines: 0, afterLines: 0 },
    kind: "textbox",
    maxChars: 4000,
  });
  const updated = requireEntry(parseInspect(afterInspect.ndjson), (entry) => entry.id === targetEntry.id, "updated P4 textbox");
  if (updated.text !== newText) throw new Error(`P4 text mismatch: ${updated.text}`);

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(stagedPath);

  const slide4 = presentation.slides.items[3];
  await writeBlob(path.join(renderDir, "slide-04.png"), await presentation.export({ slide: slide4, format: "png", scale: 1 }));
  const layout = await slide4.export({ format: "layout" });
  const layoutText = await layout.text();
  await fs.writeFile(path.join(renderDir, "slide-04.layout.json"), layoutText, "utf8");
  await fs.writeFile(path.join(layoutDir, "slide-04.layout.json"), layoutText, "utf8");

  const finalInspect = await presentation.inspect({ kind: "slide,textbox,shape,table,chart,notes,layout", maxChars: 80000 });
  await fs.writeFile(
    path.join(tempDir, "final-p4-inspect.ndjson"),
    `${parseInspect(finalInspect.ndjson).filter((entry) => entry.slide === 4).map((entry) => JSON.stringify(entry)).join("\n")}\n`,
    "utf8",
  );
  console.log(JSON.stringify({ stagedPath, line: "同一晶体 → 每次随机采样一组测量扰动 → 生成不同训练谱" }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
