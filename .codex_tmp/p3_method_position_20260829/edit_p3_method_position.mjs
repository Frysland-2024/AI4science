import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p3_method_position_20260829";
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(tempDir, "staged-XRD_导师汇报.pptx");
const beforeDir = path.join(tempDir, "before-render");
const afterDir = path.join(tempDir, "after-render");
const finalLayoutDir = path.join(tempDir, "final-layout");

const prediction = "预测 A   ≈   预测 B";
const positioning = "方法核心：把“谱可以变、结构不变”这一物理不变量写进模型训练。";

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

async function main() {
  await fs.mkdir(beforeDir, { recursive: true });
  await fs.mkdir(afterDir, { recursive: true });
  await fs.mkdir(finalLayoutDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 7) throw new Error("Expected seven slides");

  const before = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 100000,
  });
  await fs.writeFile(path.join(tempDir, "before-inspect.ndjson"), before.ndjson, "utf8");
  const entries = parseInspect(before.ndjson);
  const p3Entries = entries.filter((entry) => entry.slide === 3);
  const slideEntry = requireEntry(p3Entries, (entry) => entry.kind === "slide", "slide 3");
  const predictionEntry = requireEntry(p3Entries, (entry) => entry.id === "sh/f29gbyx0" && entry.text === prediction, "P3 prediction textbox");
  const slide = presentation.resolve(slideEntry.id);
  const target = presentation.resolve(predictionEntry.id);

  await writeBlob(path.join(beforeDir, "slide-03.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const beforeLayout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(beforeDir, "slide-03.layout.json"), await beforeLayout.text(), "utf8");

  target.position = { left: 160, top: 468, width: 960, height: 190 };
  target.text.set([
    [{ run: prediction, textStyle: { bold: true, color: "#143A63", fontSize: "76px", typeface: "Microsoft YaHei" } }],
    [{ run: "", textStyle: { fontSize: "8px", typeface: "Microsoft YaHei" } }],
    [
      { run: "方法核心：", textStyle: { bold: true, color: "#153E6A", fontSize: "22px", typeface: "Microsoft YaHei" } },
      { run: "把“谱可以变、结构不变”这一物理不变量写进模型训练。", textStyle: { bold: false, color: "#536779", fontSize: "22px", typeface: "Microsoft YaHei" } },
    ],
  ]);
  target.text.typeface = "Microsoft YaHei";
  target.text.color = "#143A63";
  target.text.alignment = "center";
  target.text.verticalAlignment = "top";
  target.text.wrap = "none";
  target.text.autoFit = "none";
  target.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  await writeBlob(path.join(afterDir, "slide-03.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const afterLayout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(afterDir, "slide-03.layout.json"), await afterLayout.text(), "utf8");
  await fs.writeFile(path.join(finalLayoutDir, "slide-03.layout.json"), await afterLayout.text(), "utf8");

  const after = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 100000,
  });
  await fs.writeFile(path.join(tempDir, "after-inspect.ndjson"), after.ndjson, "utf8");
  const afterEntry = requireEntry(
    parseInspect(after.ndjson).filter((entry) => entry.slide === 3),
    (entry) => entry.id === "sh/f29gbyx0",
    "updated P3 prediction textbox",
  );
  if (!afterEntry.text.includes(prediction) || !afterEntry.text.includes(positioning)) {
    throw new Error(`P3 positioning sentence verification failed: ${JSON.stringify(afterEntry)}`);
  }
  if (JSON.stringify(afterEntry.bbox) !== JSON.stringify([160, 468, 960, 190])) {
    throw new Error(`Unexpected P3 textbox geometry: ${JSON.stringify(afterEntry.bbox)}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
