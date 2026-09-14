import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p1_task_definition_20260901";
const sourcePath = path.join(tmpDir, "source-deck.pptx");
const outputPath = path.join(tmpDir, "staged-XRD_导师汇报.pptx");
const renderDir = path.join(tmpDir, "after-p1");

const FONT = "Microsoft YaHei";
const NAVY = "#143A63";
const BLUE = "#285F97";
const INK = "#27384A";
const MUTED = "#657384";
const RULE = "#D9E0E8";
const MODEL_FILL = "#EEF4F8";
const MODEL_LINE = "#AFC2D4";

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
    ["sh/65g3298r", "output qualifier"],
    ["ch/3epsfe9g", "input PXRD chart"],
    ["ch/c3itcjqx", "obsolete second chart"],
    ["sh/fu94fe98", "model box"],
    ["sh/utg3698n", "crystal-system output"],
    ["sh/wn6dc7eh", "obsolete underline"],
    ["sh/hofulsf2", "footer"],
  ]) requireElement(inherited, aid, label);

  const title = presentation.resolve("sh/ul4vaxgb");
  title.text = "研究任务：根据 PXRD 衍射谱判断晶系";
  configureText(title, { left: 44, top: 54, width: 1192, height: 66 }, {
    fontSize: 46,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  const subtitle = presentation.resolve("sh/547294r6");
  subtitle.text = "输入为 PXRD 衍射谱，输出为晶体所属晶系。";
  configureText(subtitle, { left: 116, top: 136, width: 1048, height: 36 }, {
    fontSize: 23,
    color: MUTED,
    alignment: "center",
    wrap: "none",
  });

  const divider = presentation.resolve("sh/k3yl0zql");
  divider.position = { left: 178, top: 204, width: 924, height: 0 };

  const inputLabel = presentation.resolve("sh/7qp4be9c");
  inputLabel.text = "PXRD 衍射谱";
  configureText(inputLabel, { left: 84, top: 248, width: 452, height: 38 }, {
    fontSize: 24,
    bold: true,
    color: BLUE,
    alignment: "center",
    wrap: "none",
  });

  const inputChart = presentation.resolve("ch/3epsfe9g");
  inputChart.position = { left: 70, top: 294, width: 480, height: 228 };

  const obsoleteChart = presentation.resolve("ch/c3itcjqx");
  slide.charts.deleteById(obsoleteChart.id);

  const model = presentation.resolve("sh/fu94fe98");
  model.text = "分类模型";
  model.fill = MODEL_FILL;
  model.line = { style: "solid", fill: MODEL_LINE, width: 1.2 };
  configureText(model, { left: 602, top: 344, width: 176, height: 70 }, {
    fontSize: 24,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  const output = presentation.resolve("sh/utg3698n");
  output.text = "晶系";
  configureText(output, { left: 864, top: 292, width: 326, height: 76 }, {
    fontSize: 46,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  const outputQualifier = presentation.resolve("sh/65g3298r");
  outputQualifier.text = "7 种晶系之一";
  configureText(outputQualifier, { left: 864, top: 372, width: 326, height: 34 }, {
    fontSize: 21,
    bold: false,
    color: MUTED,
    alignment: "center",
    wrap: "none",
  });

  const obsoleteUnderline = presentation.resolve("sh/wn6dc7eh");
  slide.shapes.deleteById(obsoleteUnderline.id);

  addTextBox(slide, "p1-input-arrow", { left: 538, top: 340, width: 64, height: 76 }, "→", {
    fontSize: 43,
    bold: true,
    color: BLUE,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p1-output-arrow", { left: 786, top: 340, width: 64, height: 76 }, "→", {
    fontSize: 43,
    bold: true,
    color: BLUE,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(
    slide,
    "p1-crystal-system-list",
    { left: 842, top: 420, width: 370, height: 82 },
    "立方 · 四方 · 正交 · 六方\n三方 · 单斜 · 三斜",
    {
      fontSize: 20,
      color: INK,
      alignment: "center",
      wrap: "square",
    },
  );

  const footer = presentation.resolve("sh/hofulsf2");
  footer.text = "阶段性研究汇报";
  configureText(footer, { left: 76, top: 654, width: 1128, height: 24 }, {
    fontSize: 16,
    color: MUTED,
    alignment: "center",
    wrap: "none",
  });

  const layoutBlob = await slide.export({ format: "layout" });
  const layoutText = await layoutBlob.text();
  await fs.writeFile(path.join(renderDir, "slide-01.layout.json"), layoutText, "utf8");
  const layout = JSON.parse(layoutText);
  const elements = layout.elements ?? [];

  const requiredPhrases = [
    "研究任务：根据 PXRD 衍射谱判断晶系",
    "输入为 PXRD 衍射谱，输出为晶体所属晶系。",
    "PXRD 衍射谱",
    "分类模型",
    "晶系",
    "7 种晶系之一",
    "立方 · 四方 · 正交 · 六方",
    "三方 · 单斜 · 三斜",
  ];
  for (const phrase of requiredPhrases) {
    const found = elements.some((entry) => typeof entry.text === "string" && entry.text.includes(phrase));
    if (!found) throw new Error(`Missing slide-1 phrase: ${phrase}`);
  }

  for (const forbidden of ["研究问题", "稳健", "受测量扰动", "晶系不变", "同一晶体", "测量条件变化", "一致性"] ) {
    if (elements.some((entry) => typeof entry.text === "string" && entry.text.includes(forbidden))) {
      throw new Error(`Slide 1 still contains forbidden wording: ${forbidden}`);
    }
  }

  const titleEntry = elements.find((entry) => entry.text === "研究任务：根据 PXRD 衍射谱判断晶系");
  const subtitleEntry = elements.find((entry) => entry.text === "输入为 PXRD 衍射谱，输出为晶体所属晶系。");
  if (!titleEntry || titleEntry.textLayout?.lineCount !== 1) throw new Error(`Slide-1 title wrapped: ${JSON.stringify(titleEntry)}`);
  if (!subtitleEntry || subtitleEntry.textLayout?.lineCount !== 1) throw new Error(`Slide-1 subtitle wrapped: ${JSON.stringify(subtitleEntry)}`);

  const chartCount = elements.filter((entry) => entry.kind === "chart").length;
  if (chartCount !== 1) throw new Error(`Expected exactly one chart on slide 1, found ${chartCount}`);

  const overflow = elements.filter((entry) => {
    const [left, top, width, height] = entry.bbox ?? [];
    if (![left, top, width, height].every(Number.isFinite)) return false;
    return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
  });
  if (overflow.length) throw new Error(`Slide-1 canvas overflow: ${JSON.stringify(overflow)}`);

  await writeBlob(
    path.join(renderDir, "slide-01.png"),
    await presentation.export({ slide, format: "png", scale: 1 }),
  );

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);
  console.log(JSON.stringify({ outputPath, renderedSlides: [1], slide1OverflowCount: 0, chartCount }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
