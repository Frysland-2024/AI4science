import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p1_task_definition_20260901";
const deckPath = path.join(tmpDir, "staged-XRD_导师汇报.pptx");
const qaDir = path.join(tmpDir, "roundtrip-p1");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(qaDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(deckPath));
  if (presentation.slides.items.length !== 8) throw new Error(`Expected 8 slides, found ${presentation.slides.items.length}`);
  const slide = presentation.slides.items[0];
  const layoutBlob = await slide.export({ format: "layout" });
  const layoutText = await layoutBlob.text();
  await fs.writeFile(path.join(qaDir, "slide-01.layout.json"), layoutText, "utf8");
  const layout = JSON.parse(layoutText);
  const elements = layout.elements ?? [];

  const allText = elements.map((entry) => entry.text ?? "").join("\n");
  for (const phrase of [
    "研究任务：根据 PXRD 衍射谱判断晶系",
    "输入为 PXRD 衍射谱，输出为晶体所属晶系。",
    "分类模型",
    "7 种晶系之一",
    "立方 · 四方 · 正交 · 六方",
    "三方 · 单斜 · 三斜",
  ]) {
    if (!allText.includes(phrase)) throw new Error(`Missing exported slide-1 phrase: ${phrase}`);
  }
  for (const phrase of ["研究问题", "稳健", "受测量扰动", "晶系不变", "同一晶体", "一致性"]) {
    if (allText.includes(phrase)) throw new Error(`Forbidden slide-1 wording survived export: ${phrase}`);
  }

  const chartCount = elements.filter((entry) => entry.kind === "chart").length;
  if (chartCount !== 1) throw new Error(`Expected one exported slide-1 chart, found ${chartCount}`);
  const overflow = elements.filter((entry) => {
    const [left, top, width, height] = entry.bbox ?? [];
    if (![left, top, width, height].every(Number.isFinite)) return false;
    return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
  });
  if (overflow.length) throw new Error(`Exported slide-1 overflow: ${JSON.stringify(overflow)}`);

  await writeBlob(path.join(qaDir, "slide-01.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  console.log(JSON.stringify({ slideCount: 8, checkedSlides: [1], chartCount, overflowCount: 0 }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
