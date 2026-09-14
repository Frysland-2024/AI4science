import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p3_innovation_20260901";
const stagedPath = path.join(tmpDir, "staged-XRD_导师汇报.pptx");
const verifyDir = path.join(tmpDir, "roundtrip-p3");

async function main() {
  await fs.mkdir(verifyDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(stagedPath));
  if (presentation.slides.items.length !== 8) {
    throw new Error(`Expected 8 slides after round trip, found ${presentation.slides.items.length}`);
  }
  const slide = presentation.slides.items[2];
  if (!slide) throw new Error("Could not locate slide 3 after round trip");

  const layoutText = await (await slide.export({ format: "layout" })).text();
  await fs.writeFile(path.join(verifyDir, "slide-03.layout.json"), layoutText, "utf8");
  const layout = JSON.parse(layoutText);
  const elements = layout.elements ?? [];
  const texts = elements.map((entry) => entry.text).filter((value) => typeof value === "string");

  for (const required of [
    "我的改进：同一结构的不同扰动谱，模型判断应保持一致",
    "同一晶体结构",
    "随机采样扰动 A",
    "随机采样扰动 B",
    "扰动谱 A",
    "扰动谱 B",
    "同一个模型",
    "晶系判断 A",
    "晶系判断 B",
    "两次判断保持一致",
    "方法核心：把“测量可变、结构不变”这一物理关系写进模型训练。",
  ]) {
    if (!texts.some((value) => value.includes(required))) {
      throw new Error(`Missing required slide-3 text after round trip: ${required}`);
    }
  }

  for (const forbidden of [
    "核心假设",
    "JS",
    "divergence",
    "consistency loss",
    "p₁",
    "p₂",
    "λ",
    "loss function",
    "ResNet",
    "provenance",
    "预测 A ≈ 预测 B",
  ]) {
    if (texts.some((value) => value.includes(forbidden))) {
      throw new Error(`Forbidden slide-3 text survived round trip: ${forbidden}`);
    }
  }

  const chartCount = elements.filter((entry) => entry.kind === "chart").length;
  if (chartCount !== 2) throw new Error(`Expected 2 charts after round trip, found ${chartCount}`);

  const titleEntry = elements.find((entry) => entry.text === "我的改进：同一结构的不同扰动谱，模型判断应保持一致");
  const takeawayEntry = elements.find((entry) => entry.text === "两次判断保持一致");
  if (!titleEntry || titleEntry.textLayout?.lineCount !== 1) throw new Error("Slide-3 title wraps after round trip");
  if (!takeawayEntry || takeawayEntry.textLayout?.lineCount !== 1) throw new Error("Slide-3 takeaway wraps after round trip");

  const overflow = elements.filter((entry) => {
    const [left, top, width, height] = entry.bbox ?? [];
    if (![left, top, width, height].every(Number.isFinite)) return false;
    return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
  });
  if (overflow.length) throw new Error(`Slide 3 overflow after round trip: ${JSON.stringify(overflow)}`);

  const result = {
    slideCount: presentation.slides.items.length,
    verifiedSlides: [3],
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
