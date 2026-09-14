import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p4_training_sampling_20260828");
const finalPptx = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "roundtrip-p4");
const expectedText = [
  "按晶体结构划分",
  "同一晶体的不同谱始终留在同一数据集",
  "",
  "训练时实时生成谱",
  "每次随机采样一组测量扰动 → 生成不同训练谱",
].join("\n");

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(finalPptx));
  if (presentation.slides.items.length !== 6) throw new Error("Expected six slides after roundtrip");

  const inspected = await presentation.inspect({
    kind: "slide,textbox,shape,table,chart,notes,layout",
    maxChars: 80000,
  });
  const entries = parseInspect(inspected.ndjson);
  const p4 = entries.filter((entry) => entry.slide === 4);
  const target = p4.find((entry) => entry.id === "sh/g36tgryd");
  if (target?.text !== expectedText) throw new Error(`P4 replacement did not survive roundtrip: ${target?.text}`);
  if (JSON.stringify(target.bbox) !== JSON.stringify([72, 446, 420, 190])) {
    throw new Error(`P4 textbox geometry changed: ${JSON.stringify(target.bbox)}`);
  }

  const table = p4.find((entry) => entry.id === "tb/mhovq5k3");
  if (!table || table.rows !== 6 || table.cols !== 2 || JSON.stringify(table.bbox) !== JSON.stringify([545, 142, 655, 470])) {
    throw new Error("P4 table changed unexpectedly");
  }

  const slide4 = presentation.slides.items[3];
  await writeBlob(
    path.join(renderDir, "slide-04.png"),
    await presentation.export({ slide: slide4, format: "png", scale: 1 }),
  );
  const layout = await slide4.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, "slide-04.layout.json"), await layout.text(), "utf8");
  await fs.writeFile(
    path.join(tempDir, "roundtrip-p4-inspect.ndjson"),
    `${p4.map((entry) => JSON.stringify(entry)).join("\n")}\n`,
    "utf8",
  );
  console.log("P4 roundtrip verification passed");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
