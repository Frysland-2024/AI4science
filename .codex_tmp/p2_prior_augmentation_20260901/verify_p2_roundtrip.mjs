import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p2_prior_augmentation_20260901";
const stagedPath = path.join(tmpDir, "staged-XRD_导师汇报.pptx");
const verifyDir = path.join(tmpDir, "roundtrip-p2");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(verifyDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(stagedPath));
  if (presentation.slides.items.length !== 8) {
    throw new Error(`Expected 8 slides after round trip, found ${presentation.slides.items.length}`);
  }
  const slide = presentation.slides.items[1];
  if (!slide) throw new Error("Could not locate slide 2 after round trip");

  const layoutText = await (await slide.export({ format: "layout" })).text();
  await fs.writeFile(path.join(verifyDir, "slide-02.layout.json"), layoutText, "utf8");
  const layout = JSON.parse(layoutText);
  const elements = layout.elements ?? [];
  const texts = elements.map((entry) => entry.text).filter((text) => typeof text === "string");

  for (const required of [
    "前人工作：随机采样物理扰动，生成多样化训练谱",
    "随机采样\n物理扰动",
    "生成多种训练谱",
    "扰动谱 A",
    "扰动谱 B",
    "扰动谱 C",
    "这些生成谱通常作为彼此独立的训练样本使用。",
  ]) {
    if (!texts.some((text) => text.includes(required))) throw new Error(`Missing required text after round trip: ${required}`);
  }

  for (const forbidden of ["我的方法", "一致性训练", "JS divergence", "同母结构关系", "物理不变量约束", "ResNet"]) {
    if (texts.some((text) => text.includes(forbidden))) throw new Error(`Forbidden text survived on slide 2: ${forbidden}`);
  }

  const chartCount = elements.filter((entry) => entry.kind === "chart").length;
  if (chartCount !== 3) throw new Error(`Expected 3 charts after round trip, found ${chartCount}`);

  const overflow = elements.filter((entry) => {
    const [left, top, width, height] = entry.bbox ?? [];
    if (![left, top, width, height].every(Number.isFinite)) return false;
    return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
  });
  if (overflow.length) throw new Error(`Slide 2 overflow after round trip: ${JSON.stringify(overflow)}`);

  await writeBlob(path.join(verifyDir, "slide-02.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const result = {
    slideCount: presentation.slides.items.length,
    verifiedSlides: [2],
    chartCount,
    overflowCount: overflow.length,
    sourceNotesCheckedSeparatelyInPptxPackage: true,
  };
  await fs.writeFile(path.join(verifyDir, "verification.json"), JSON.stringify(result, null, 2), "utf8");
  console.log(JSON.stringify(result));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
