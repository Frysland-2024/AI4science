import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p3_innovation_20260901";
const sourcePath = path.join(tmpDir, "source-deck.pptx");
const outputPath = path.join(tmpDir, "staged-XRD_导师汇报.pptx");
const renderDir = path.join(tmpDir, "after-p3");

const FONT = "Microsoft YaHei";
const NAVY = "#143A63";
const BLUE = "#285F97";
const INK = "#27384A";
const MUTED = "#657384";
const RULE = "#D9E0E8";
const ORANGE = "#E77A25";
const MODEL_FILL = "#EEF4F9";
const MODEL_LINE = "#9BB2C8";

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function configureText(shape, position, style = {}) {
  shape.position = position;
  shape.text.typeface = FONT;
  shape.text.color = style.color ?? INK;
  shape.text.fontSize = style.fontSize ?? 20;
  shape.text.bold = style.bold ?? false;
  shape.text.alignment = style.alignment ?? "left";
  shape.text.verticalAlignment = style.verticalAlignment ?? "middle";
  shape.text.wrap = style.wrap ?? "square";
  shape.text.autoFit = style.autoFit ?? "none";
  shape.text.insets = style.insets ?? { top: 0, right: 0, bottom: 0, left: 0 };
}

function addTextBox(slide, name, position, text, style = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position,
    fill: style.fill ?? "none",
    line: style.line ?? { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  configureText(shape, position, style);
  return shape;
}

function addPlainRect(slide, name, position, fill, line) {
  return slide.shapes.add({
    geometry: "roundRect",
    name,
    position,
    fill,
    line,
    borderRadius: 7,
  });
}

function requireElement(layoutElements, aid, label) {
  const element = layoutElements.find((entry) => entry.aid === aid);
  if (!element) throw new Error(`Could not locate ${label}: ${aid}`);
  return element;
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 8) {
    throw new Error(`Expected 8 slides, found ${presentation.slides.items.length}`);
  }

  const slide = presentation.slides.items[2];
  if (!slide) throw new Error("Could not locate slide 3");
  const beforeLayout = JSON.parse(await (await slide.export({ format: "layout" })).text());
  const inherited = beforeLayout.elements ?? [];

  for (const [aid, label] of [
    ["sh/03ix43e5", "title"],
    ["sh/cza94vmx", "slide number"],
    ["sh/d0jax03i", "divider"],
    ["ch/18j69wbi", "spectrum A"],
    ["ch/q18nuxsv", "spectrum B"],
  ]) requireElement(inherited, aid, label);

  const title = presentation.resolve("sh/03ix43e5");
  title.text = "我的改进：同一结构的不同扰动谱，模型判断应保持一致";
  configureText(title, { left: 58, top: 26, width: 1104, height: 58 }, {
    fontSize: 38,
    bold: true,
    color: NAVY,
    alignment: "left",
    wrap: "none",
  });

  const pageNumber = presentation.resolve("sh/cza94vmx");
  pageNumber.text = "03 / 08";
  configureText(pageNumber, { left: 1176, top: 40, width: 48, height: 24 }, {
    fontSize: 14,
    color: MUTED,
    alignment: "right",
    wrap: "none",
  });

  const divider = presentation.resolve("sh/d0jax03i");
  divider.position = { left: 58, top: 102, width: 1166, height: 0 };

  const removableShapeIds = [
    "sh/298ryl4v",
    "sh/3ah8rqlg",
    "sh/obq90bml",
    "sh/pcjqtg36",
    "sh/m5cra54z",
    "sh/n6ls3alk",
    "sh/n2l4fq98",
    "sh/m1c3mlsn",
    "sh/943mhgre",
    "sh/83ulovat",
    "sh/v6l4jq94",
    "sh/a5c3ql8z",
    "sh/x8nml0ra",
    "sh/i9w3u58v",
    "sh/e10f2twf",
    "sh/f29gbyx0",
  ];
  for (const aid of removableShapeIds) {
    const shape = presentation.resolve(aid);
    slide.shapes.deleteById(shape.id);
  }

  addTextBox(slide, "p3-same-crystal", { left: 430, top: 116, width: 420, height: 42 }, "同一晶体结构", {
    fontSize: 31,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-branch-left", { left: 412, top: 148, width: 88, height: 38 }, "↙", {
    fontSize: 34,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-branch-right", { left: 780, top: 148, width: 88, height: 38 }, "↘", {
    fontSize: 34,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  addTextBox(slide, "p3-random-a", { left: 176, top: 172, width: 350, height: 28 }, "随机采样扰动 A", {
    fontSize: 17,
    color: MUTED,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-random-b", { left: 754, top: 172, width: 350, height: 28 }, "随机采样扰动 B", {
    fontSize: 17,
    color: MUTED,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-down-random-a", { left: 330, top: 194, width: 42, height: 30 }, "↓", {
    fontSize: 24,
    bold: true,
    color: ORANGE,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-down-random-b", { left: 908, top: 194, width: 42, height: 30 }, "↓", {
    fontSize: 24,
    bold: true,
    color: ORANGE,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-spectrum-a-label", { left: 176, top: 215, width: 350, height: 28 }, "扰动谱 A", {
    fontSize: 20,
    bold: true,
    color: BLUE,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-spectrum-b-label", { left: 754, top: 215, width: 350, height: 28 }, "扰动谱 B", {
    fontSize: 20,
    bold: true,
    color: ORANGE,
    alignment: "center",
    wrap: "none",
  });

  const chartA = presentation.resolve("ch/18j69wbi");
  const chartB = presentation.resolve("ch/q18nuxsv");
  chartA.position = { left: 176, top: 242, width: 350, height: 88 };
  chartB.position = { left: 754, top: 242, width: 350, height: 88 };

  addTextBox(slide, "p3-down-chart-a", { left: 330, top: 326, width: 42, height: 30 }, "↓", {
    fontSize: 25,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-down-chart-b", { left: 908, top: 326, width: 42, height: 30 }, "↓", {
    fontSize: 25,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  addPlainRect(
    slide,
    "p3-same-model-box",
    { left: 354, top: 358, width: 572, height: 38 },
    MODEL_FILL,
    { style: "solid", fill: MODEL_LINE, width: 1.1 },
  );
  addTextBox(slide, "p3-same-model-label", { left: 354, top: 358, width: 572, height: 38 }, "同一个模型", {
    fontSize: 19,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  addTextBox(slide, "p3-down-model-a", { left: 330, top: 396, width: 42, height: 30 }, "↓", {
    fontSize: 25,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-down-model-b", { left: 908, top: 396, width: 42, height: 30 }, "↓", {
    fontSize: 25,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-judgment-a", { left: 176, top: 424, width: 350, height: 34 }, "晶系判断 A", {
    fontSize: 22,
    bold: true,
    color: BLUE,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-judgment-b", { left: 754, top: 424, width: 350, height: 34 }, "晶系判断 B", {
    fontSize: 22,
    bold: true,
    color: ORANGE,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-converge-left", { left: 430, top: 452, width: 70, height: 34 }, "↘", {
    fontSize: 30,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p3-converge-right", { left: 780, top: 452, width: 70, height: 34 }, "↙", {
    fontSize: 30,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  addTextBox(slide, "p3-main-takeaway", { left: 190, top: 481, width: 900, height: 74 }, "两次判断保持一致", {
    fontSize: 58,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  const coreSentence = addTextBox(
    slide,
    "p3-core-sentence",
    { left: 120, top: 624, width: 1040, height: 34 },
    "方法核心：把“测量可变、结构不变”这一物理关系写进模型训练。",
    {
      fontSize: 20.5,
      color: INK,
      alignment: "center",
      wrap: "none",
    },
  );
  coreSentence.text.set([
    [
      { run: "方法核心：", textStyle: { bold: true, color: NAVY, fontSize: "20.5px", typeface: FONT } },
      { run: "把“测量可变、结构不变”这一物理关系写进模型训练。", textStyle: { bold: false, color: INK, fontSize: "20.5px", typeface: FONT } },
    ],
  ]);

  slide.speakerNotes.textFrame.setText(
    "讲述提示：前人随机生成很多训练谱后，通常把它们作为独立样本。本工作进一步利用生成过程里已经知道的同源关系：若两条谱来自同一晶体结构，模型对晶系的两次判断就应保持一致。",
  );

  const layoutBlob = await slide.export({ format: "layout" });
  const layoutText = await layoutBlob.text();
  await fs.writeFile(path.join(renderDir, "slide-03.layout.json"), layoutText, "utf8");
  const layout = JSON.parse(layoutText);
  const elements = layout.elements ?? [];

  const requiredPhrases = [
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
  ];
  for (const phrase of requiredPhrases) {
    const found = elements.some((entry) => typeof entry.text === "string" && entry.text.includes(phrase));
    if (!found) throw new Error(`Missing slide-3 phrase: ${phrase}`);
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
    "weak augmentation",
    "strong augmentation",
    "ResNet",
    "provenance",
    "预测 A ≈ 预测 B",
  ]) {
    if (elements.some((entry) => typeof entry.text === "string" && entry.text.includes(forbidden))) {
      throw new Error(`Slide 3 still contains forbidden wording: ${forbidden}`);
    }
  }

  const titleEntry = elements.find((entry) => entry.text === "我的改进：同一结构的不同扰动谱，模型判断应保持一致");
  const takeawayEntry = elements.find((entry) => entry.text === "两次判断保持一致");
  if (!titleEntry || titleEntry.textLayout?.lineCount !== 1) {
    throw new Error(`Slide-3 title wrapped: ${JSON.stringify(titleEntry)}`);
  }
  if (!takeawayEntry || takeawayEntry.textLayout?.lineCount !== 1) {
    throw new Error(`Slide-3 takeaway wrapped: ${JSON.stringify(takeawayEntry)}`);
  }

  const chartCount = elements.filter((entry) => entry.kind === "chart").length;
  if (chartCount !== 2) throw new Error(`Expected exactly two charts on slide 3, found ${chartCount}`);

  const sameModelCount = elements.filter((entry) => entry.text === "同一个模型").length;
  if (sameModelCount !== 1) throw new Error(`Expected one same-model label, found ${sameModelCount}`);

  const overflow = elements.filter((entry) => {
    const [left, top, width, height] = entry.bbox ?? [];
    if (![left, top, width, height].every(Number.isFinite)) return false;
    return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
  });
  if (overflow.length) throw new Error(`Slide-3 canvas overflow: ${JSON.stringify(overflow)}`);

  await writeBlob(
    path.join(renderDir, "slide-03.png"),
    await presentation.export({ slide, format: "png", scale: 1 }),
  );

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);
  console.log(JSON.stringify({ outputPath, renderedSlides: [3], slide3OverflowCount: 0, chartCount }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
