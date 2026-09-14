import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p4_dynamic_generation_20260828");
const finalPptx = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "roundtrip-p4");

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
    kind: "slide,textbox,shape,table,notes,layout",
    maxChars: 60000,
  });
  const entries = parseInspect(inspected.ndjson);
  const p4 = entries.filter((entry) => entry.slide === 4);
  const updated = p4.find((entry) => entry.id === "sh/g36tgryd");
  if (!updated || !updated.text?.includes("训练时实时生成谱") || !updated.text?.includes("随机“换测量条件”")) {
    throw new Error("Updated slide 4 text did not survive PPTX roundtrip");
  }
  const table = p4.find((entry) => entry.id === "tb/8jqxsf29" && entry.kind === "table");
  if (!table || table.preview !== "扰动类型 | 对谱图的影响" || table.rows !== 6 || table.cols !== 2) {
    throw new Error("Slide 4 right-side table changed or disappeared");
  }
  const notes = p4.find((entry) => entry.kind === "notes");
  if (!notes?.text?.includes("在线采样两组测量条件") || !notes.text.includes("完全相同的固定谱")) {
    throw new Error("Slide 4 provenance notes did not survive PPTX roundtrip");
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
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
