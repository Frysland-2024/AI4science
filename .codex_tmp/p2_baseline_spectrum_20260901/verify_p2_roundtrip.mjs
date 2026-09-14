import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p2_baseline_spectrum_20260901";
const stagedPath = path.join(tmpDir, "staged-XRD_导师汇报.pptx");
const verifyDir = path.join(tmpDir, "roundtrip-p2");

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
  const texts = elements.map((entry) => entry.text).filter((value) => typeof value === "string");

  for (const required of [
    "前人工作：随机采样扰动参数，生成多样化训练谱",
    "晶体结构",
    "基准计算谱",
    "未加入测量扰动",
    "随机采样",
    "扰动参数",
    "生成多种训练谱",
    "训练谱 A",
    "训练谱 B",
    "训练谱 C",
    "但这些同源生成谱，通常仍被当作彼此独立的训练样本使用。",
  ]) {
    if (!texts.some((value) => value.includes(required))) {
      throw new Error(`Missing required slide-2 text after round trip: ${required}`);
    }
  }

  for (const forbidden of [
    "根据晶体结构\n计算 XRD 谱",
    "根据晶体结构计算 XRD 谱",
    "干净谱",
    "但是这些生成谱仍然作为彼此独立的训练样本使用。",
  ]) {
    if (texts.some((value) => value.includes(forbidden))) {
      throw new Error(`Forbidden slide-2 text survived round trip: ${forbidden}`);
    }
  }

  const chartCount = elements.filter((entry) => entry.kind === "chart").length;
  if (chartCount !== 4) throw new Error(`Expected 4 charts after round trip, found ${chartCount}`);

  const titleEntry = elements.find((entry) => entry.text === "前人工作：随机采样扰动参数，生成多样化训练谱");
  const transitionEntry = elements.find((entry) => entry.text === "但这些同源生成谱，通常仍被当作彼此独立的训练样本使用。");
  if (!titleEntry || titleEntry.textLayout?.lineCount !== 1) throw new Error("Slide-2 title wraps after round trip");
  if (!transitionEntry || transitionEntry.textLayout?.lineCount !== 1) throw new Error("Slide-2 transition wraps after round trip");

  const overflow = elements.filter((entry) => {
    const [left, top, width, height] = entry.bbox ?? [];
    if (![left, top, width, height].every(Number.isFinite)) return false;
    return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
  });
  if (overflow.length) throw new Error(`Slide 2 overflow after round trip: ${JSON.stringify(overflow)}`);

  const result = {
    slideCount: presentation.slides.items.length,
    verifiedSlides: [2],
    chartCount,
    overflowCount: overflow.length,
    renderedSlidesDuringRoundTrip: [],
  };
  await fs.writeFile(path.join(verifyDir, "verification.json"), JSON.stringify(result, null, 2), "utf8");
  console.log(JSON.stringify(result));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
