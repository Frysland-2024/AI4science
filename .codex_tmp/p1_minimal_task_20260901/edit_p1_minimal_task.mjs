import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p1_minimal_task_20260901";
const sourcePath = path.join(tmpDir, "source-deck.pptx");
const outputPath = path.join(tmpDir, "staged-XRD_导师汇报.pptx");
const renderDir = path.join(tmpDir, "after-p1");

const FONT = "Microsoft YaHei";
const NAVY = "#143A63";
const BLUE = "#285F97";
const INK = "#27384A";
const MUTED = "#657384";

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
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  configureText(shape, position, style);
  return shape;
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

  const slide = presentation.slides.items[0];
  if (!slide) throw new Error("Could not locate slide 1");
  const beforeLayout = JSON.parse(await (await slide.export({ format: "layout" })).text());
  const inherited = beforeLayout.elements ?? [];

  for (const [aid, label] of [
    ["sh/ul4vaxgb", "title"],
    ["sh/547294r6", "subtitle"],
    ["sh/k3yl0zql", "divider"],
    ["sh/7qp4be9c", "input label"],
    ["ch/b2psje9c", "PXRD chart"],
    ["sh/fu94fe98", "classification model"],
    ["sh/4r6dg7et", "first arrow"],
    ["sh/5sfepcfe", "second arrow"],
    ["sh/utg3698n", "crystal-system output"],
    ["sh/65g3298r", "output qualifier"],
    ["sh/ipovexwn", "crystal-system list"],
    ["sh/hofulsf2", "footer"],
  ]) requireElement(inherited, aid, label);

  const title = presentation.resolve("sh/ul4vaxgb");
  title.text = "研究任务：根据 PXRD 谱判断晶系";
  configureText(title, { left: 44, top: 56, width: 1192, height: 66 }, {
    fontSize: 46,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  const subtitle = presentation.resolve("sh/547294r6");
  slide.shapes.deleteById(subtitle.id);

  const divider = presentation.resolve("sh/k3yl0zql");
  divider.position = { left: 178, top: 158, width: 924, height: 0 };

  const inputLabel = presentation.resolve("sh/7qp4be9c");
  inputLabel.text = "PXRD 谱";
  configureText(inputLabel, { left: 72, top: 204, width: 520, height: 42 }, {
    fontSize: 26,
    bold: true,
    color: BLUE,
    alignment: "center",
    wrap: "none",
  });

  const inputChart = presentation.resolve("ch/b2psje9c");
  inputChart.position = { left: 66, top: 252, width: 532, height: 268 };

  const model = presentation.resolve("sh/fu94fe98");
  slide.shapes.deleteById(model.id);
  const firstArrow = presentation.resolve("sh/4r6dg7et");
  const secondArrow = presentation.resolve("sh/5sfepcfe");
  slide.shapes.deleteById(firstArrow.id);
  slide.shapes.deleteById(secondArrow.id);

  addTextBox(slide, "p1-direct-task-arrow", { left: 610, top: 326, width: 150, height: 94 }, "→", {
    fontSize: 58,
    bold: true,
    color: BLUE,
    alignment: "center",
    wrap: "none",
  });

  const output = presentation.resolve("sh/utg3698n");
  configureText(output, { left: 824, top: 260, width: 376, height: 78 }, {
    fontSize: 46,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  const outputQualifier = presentation.resolve("sh/65g3298r");
  configureText(outputQualifier, { left: 824, top: 345, width: 376, height: 36 }, {
    fontSize: 21,
    color: MUTED,
    alignment: "center",
    wrap: "none",
  });

  const crystalSystemList = presentation.resolve("sh/ipovexwn");
  configureText(crystalSystemList, { left: 804, top: 404, width: 416, height: 82 }, {
    fontSize: 20,
    color: INK,
    alignment: "center",
    wrap: "square",
  });

  const layoutBlob = await slide.export({ format: "layout" });
  const layoutText = await layoutBlob.text();
  await fs.writeFile(path.join(renderDir, "slide-01.layout.json"), layoutText, "utf8");
  const layout = JSON.parse(layoutText);
  const elements = layout.elements ?? [];

  for (const phrase of [
    "研究任务：根据 PXRD 谱判断晶系",
    "PXRD 谱",
    "晶系",
    "7 种晶系之一",
    "立方 · 四方 · 正交 · 六方",
    "三方 · 单斜 · 三斜",
  ]) {
    const found = elements.some((entry) => typeof entry.text === "string" && entry.text.includes(phrase));
    if (!found) throw new Error(`Missing slide-1 phrase: ${phrase}`);
  }

  for (const forbidden of ["PXRD 衍射谱", "输入为 PXRD", "输出为晶体", "分类模型"]) {
    if (elements.some((entry) => typeof entry.text === "string" && entry.text.includes(forbidden))) {
      throw new Error(`Slide 1 still contains forbidden wording: ${forbidden}`);
    }
  }

  const titleEntry = elements.find((entry) => entry.text === "研究任务：根据 PXRD 谱判断晶系");
  if (!titleEntry || titleEntry.textLayout?.lineCount !== 1) {
    throw new Error(`Slide-1 title wrapped: ${JSON.stringify(titleEntry)}`);
  }

  const arrowCount = elements.filter((entry) => entry.text === "→").length;
  if (arrowCount !== 1) throw new Error(`Expected exactly one arrow on slide 1, found ${arrowCount}`);
  const chartCount = elements.filter((entry) => entry.kind === "chart").length;
  if (chartCount !== 1) throw new Error(`Expected exactly one chart on slide 1, found ${chartCount}`);

  const overflow = elements.filter((entry) => {
    const [left, top, width, height] = entry.bbox ?? [];
    if (![left, top, width, height].every(Number.isFinite)) return false;
    return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
  });
  if (overflow.length) throw new Error(`Slide-1 canvas overflow: ${JSON.stringify(overflow)}`);

  await writeBlob(path.join(renderDir, "slide-01.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);
  console.log(JSON.stringify({ outputPath, renderedSlides: [1], slide1OverflowCount: 0, chartCount, arrowCount }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
