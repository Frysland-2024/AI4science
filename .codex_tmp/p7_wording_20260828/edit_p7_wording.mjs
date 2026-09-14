import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p7_wording_20260828";
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(tempDir, "staged-XRD_导师汇报.pptx");
const beforeDir = path.join(tempDir, "before-render");
const afterDir = path.join(tempDir, "after-render");
const finalLayoutDir = path.join(tempDir, "final-layout");

const oldSummary = "平均 +1.87 pp\n直接测试，结果全部提升";
const newRepeatLine = "在相同数据和训练设置下\n重复训练 5 次，结果都更好。";
const newSummary = `平均 +1.87 pp\n${newRepeatLine}`;
const oldBottom = "绝对性能仍较低，因此这里把 CNRS 作为独立真实谱来源上的直接迁移证据。";
const newBottom = "在另一套真实实验谱上直接测试，我的方法仍然表现出稳定增益。";

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
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
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 100000,
  });
  await fs.writeFile(path.join(tempDir, "before-inspect.ndjson"), before.ndjson, "utf8");
  const entries = parseInspect(before.ndjson);
  const p7Entries = entries.filter((entry) => entry.slide === 7);
  const slideEntry = p7Entries.find((entry) => entry.kind === "slide");
  const summaryEntry = p7Entries.find((entry) => entry.text === oldSummary);
  const bottomEntry = p7Entries.find((entry) => entry.text === oldBottom);
  if (!slideEntry || !summaryEntry || !bottomEntry) {
    throw new Error(`Could not locate all P7 targets: ${JSON.stringify({ slideEntry, summaryEntry, bottomEntry })}`);
  }

  const slide = presentation.resolve(slideEntry.id);
  const summary = presentation.resolve(summaryEntry.id);
  const bottom = presentation.resolve(bottomEntry.id);
  const summaryPosition = { ...summary.position };
  const bottomPosition = { ...bottom.position };

  await writeBlob(path.join(beforeDir, "slide-07.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const beforeLayout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(beforeDir, "slide-07.layout.json"), await beforeLayout.text(), "utf8");

  summary.text.replace("直接测试，结果全部提升", newRepeatLine);
  summary.position = summaryPosition;
  bottom.text = newBottom;
  bottom.position = bottomPosition;

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  await writeBlob(path.join(afterDir, "slide-07.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const afterLayout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(afterDir, "slide-07.layout.json"), await afterLayout.text(), "utf8");

  for (let index = 0; index < presentation.slides.items.length; index += 1) {
    const layout = await presentation.slides.items[index].export({ format: "layout" });
    await fs.writeFile(
      path.join(finalLayoutDir, `slide-${String(index + 1).padStart(2, "0")}.layout.json`),
      await layout.text(),
      "utf8",
    );
  }

  const after = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 100000,
  });
  await fs.writeFile(path.join(tempDir, "after-inspect.ndjson"), after.ndjson, "utf8");
  const afterEntries = parseInspect(after.ndjson).filter((entry) => entry.slide === 7);
  const afterSummary = afterEntries.find((entry) => entry.text === newSummary);
  const afterBottom = afterEntries.find((entry) => entry.text === newBottom);
  if (!afterSummary || !afterBottom) {
    throw new Error(`P7 replacement verification failed: ${JSON.stringify({ afterSummary, afterBottom })}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
