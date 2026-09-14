import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p2_shift_down_20260901";
const staged = `${tmpDir}/staged-XRD_导师汇报.pptx`;
const verifyDir = `${tmpDir}/roundtrip-p2`;

await fs.mkdir(verifyDir, { recursive: true });
const presentation = await PresentationFile.importPptx(await FileBlob.load(staged));
if (presentation.slides.items.length !== 8) {
  throw new Error(`Expected 8 slides, found ${presentation.slides.items.length}`);
}

const slide = presentation.slides.items[1];
const layoutText = await (await slide.export({ format: "layout" })).text();
await fs.writeFile(`${verifyDir}/slide-02.layout.json`, layoutText);
const layout = JSON.parse(layoutText);
const elements = layout.elements ?? [];

const findText = (needle) => elements.find((entry) =>
  typeof entry.text === "string" && entry.text.includes(needle),
);
const computation = findText("根据晶体结构");
const baselineLabel = findText("基准计算谱");
const baselineNote = findText("未加入测量扰动");
if (!computation || !baselineLabel || !baselineNote) {
  throw new Error("Could not locate every shifted baseline-spectrum text element after round trip");
}

const charts = elements.filter((entry) => entry.kind === "chart");
const baselineChart = charts.find((entry) => {
  const [, , width, height] = entry.bbox ?? [];
  return width >= 200 && width <= 230 && height >= 50 && height <= 62;
});
if (!baselineChart) throw new Error("Could not locate the shifted baseline chart after round trip");

const topOf = (entry) => entry.bbox?.[1];
const expectedTops = [
  ["computation", computation, 208],
  ["baselineChart", baselineChart, 260],
  ["baselineLabel", baselineLabel, 316.5],
  ["baselineNote", baselineNote, 350.5],
];
for (const [name, entry, expected] of expectedTops) {
  const actual = topOf(entry);
  if (!Number.isFinite(actual) || Math.abs(actual - expected) > 2) {
    throw new Error(`${name} top mismatch: expected about ${expected}, found ${actual}`);
  }
}

const overflow = elements.filter((entry) => {
  const [left, top, width, height] = entry.bbox ?? [];
  if (![left, top, width, height].every(Number.isFinite)) return false;
  return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
});
if (overflow.length) throw new Error(`Slide 2 overflow: ${JSON.stringify(overflow)}`);

const result = {
  slideCount: presentation.slides.items.length,
  verifiedSlides: [2],
  shiftedModuleDeltaPx: 18,
  shiftedElementCount: 4,
  p2OverflowCount: overflow.length,
  renderedSlidesDuringRoundTrip: [],
};
await fs.writeFile(`${verifyDir}/verification.json`, JSON.stringify(result, null, 2));
console.log(JSON.stringify(result));
