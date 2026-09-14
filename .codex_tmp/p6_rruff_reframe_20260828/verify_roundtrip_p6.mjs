import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p6_rruff_reframe_20260828");
const finalPptx = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "roundtrip-p6");

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
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 80000,
  });
  const entries = parseInspect(inspected.ndjson);
  const p6 = entries.filter((entry) => entry.slide === 6);
  const title = p6.find((entry) => entry.id === "sh/u1kbu1ov");
  if (!title?.text?.includes("RRUFF-301 真实谱少样本适配") || !title.text.includes("+4.33 pp")) {
    throw new Error("Slide 6 title did not survive PPTX roundtrip");
  }
  const context = p6.find((entry) => entry.id === "sh/47mt0b6x");
  if (!context?.text?.includes("301 条实验 PXRD 谱") || !context.text.includes("7 个晶系")) {
    throw new Error("Slide 6 dataset context did not survive PPTX roundtrip");
  }
  for (const id of ["sh/87ipkzal", "sh/98rqt4r6", "sh/ml07i9sv"]) {
    if (p6.some((entry) => entry.id === id)) throw new Error(`Deleted right-side fragment survived: ${id}`);
  }
  const annotation = p6.find((entry) => entry.id === "sh/5svutgni");
  if (annotation?.text !== "仅 7 条真实标注谱") throw new Error("K=1 annotation did not survive");
  const chart = p6.find((entry) => entry.kind === "chart" && entry.name === "p6-rruff-fewshot-bars");
  if (!chart || chart.bbox?.[2] < 1100) throw new Error("Expanded native chart did not survive");
  const notes = p6.find((entry) => entry.kind === "notes");
  if (!notes?.text?.includes("301 个唯一 RRUFF 实测样本") || !notes.text.includes("K=1: 0.2847 → 0.3280")) {
    throw new Error("Slide 6 source notes did not survive PPTX roundtrip");
  }

  const slide6 = presentation.slides.items[5];
  await writeBlob(
    path.join(renderDir, "slide-06.png"),
    await presentation.export({ slide: slide6, format: "png", scale: 1 }),
  );
  const layout = await slide6.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, "slide-06.layout.json"), await layout.text(), "utf8");
  await fs.writeFile(
    path.join(tempDir, "roundtrip-p6-inspect.ndjson"),
    `${p6.map((entry) => JSON.stringify(entry)).join("\n")}\n`,
    "utf8",
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
