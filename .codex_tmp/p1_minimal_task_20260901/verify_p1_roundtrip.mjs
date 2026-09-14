import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p1_minimal_task_20260901";
const stagedPath = path.join(tmpDir, "staged-XRD_导师汇报.pptx");
const verifyDir = path.join(tmpDir, "roundtrip-p1");

async function main() {
  await fs.mkdir(verifyDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(stagedPath));
  if (presentation.slides.items.length !== 8) {
    throw new Error(`Expected 8 slides after round trip, found ${presentation.slides.items.length}`);
  }
  const slide = presentation.slides.items[0];
  if (!slide) throw new Error("Could not locate slide 1 after round trip");

  const layoutText = await (await slide.export({ format: "layout" })).text();
  await fs.writeFile(path.join(verifyDir, "slide-01.layout.json"), layoutText, "utf8");
  const layout = JSON.parse(layoutText);
  const elements = layout.elements ?? [];
  const texts = elements.map((entry) => entry.text).filter((text) => typeof text === "string");

  for (const required of [
    "研究任务：根据 PXRD 谱判断晶系",
    "PXRD 谱",
    "晶系",
    "7 种晶系之一",
    "立方 · 四方 · 正交 · 六方",
    "三方 · 单斜 · 三斜",
  ]) {
    if (!texts.some((text) => text.includes(required))) throw new Error(`Missing required text after round trip: ${required}`);
  }

  for (const forbidden of ["PXRD 衍射谱", "输入为 PXRD", "输出为晶体", "分类模型"]) {
    if (texts.some((text) => text.includes(forbidden))) throw new Error(`Forbidden text survived on slide 1: ${forbidden}`);
  }

  const chartCount = elements.filter((entry) => entry.kind === "chart").length;
  const arrowCount = elements.filter((entry) => entry.text === "→").length;
  if (chartCount !== 1) throw new Error(`Expected 1 chart after round trip, found ${chartCount}`);
  if (arrowCount !== 1) throw new Error(`Expected 1 arrow after round trip, found ${arrowCount}`);

  const overflow = elements.filter((entry) => {
    const [left, top, width, height] = entry.bbox ?? [];
    if (![left, top, width, height].every(Number.isFinite)) return false;
    return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
  });
  if (overflow.length) throw new Error(`Slide 1 overflow after round trip: ${JSON.stringify(overflow)}`);

  const result = {
    slideCount: presentation.slides.items.length,
    verifiedSlides: [1],
    chartCount,
    arrowCount,
    overflowCount: overflow.length,
  };
  await fs.writeFile(path.join(verifyDir, "verification.json"), JSON.stringify(result, null, 2), "utf8");
  console.log(JSON.stringify(result));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
