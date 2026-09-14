import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p2_prior_augmentation_20260901";
const sourcePath = path.join(tmpDir, "source-deck.pptx");
const outputPath = path.join(tmpDir, "staged-XRD_导师汇报.pptx");
const renderDir = path.join(tmpDir, "after-p2");

const FONT = "Microsoft YaHei";
const NAVY = "#143A63";
const BLUE = "#285F97";
const INK = "#27384A";
const MUTED = "#657384";
const RULE = "#D9E0E8";
const ORANGE = "#E77A25";
const ORANGE_FILL = "#FFF3E8";

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

  const slide = presentation.slides.items[1];
  if (!slide) throw new Error("Could not locate slide 2");
  const beforeLayout = JSON.parse(await (await slide.export({ format: "layout" })).text());
  const inherited = beforeLayout.elements ?? [];

  for (const [aid, label] of [
    ["sh/nu58f2hs", "title"],
    ["sh/9072xkry", "slide number"],
    ["sh/ozy1ofad", "divider"],
    ["sh/b29kza94", "crystal structure label"],
    ["sh/a10jqpsj", "PXRD computation label"],
    ["sh/x4r21kru", "perturbation label"],
    ["ch/47uh8zqh", "spectrum A"],
    ["ch/p83y1472", "spectrum B"],
    ["ch/25cz6p8b", "spectrum C"],
    ["sh/ove9o7yd", "first old separator"],
    ["sh/9wnqhczy", "second old separator"],
    ["sh/mtwrmxg7", "transition sentence"],
  ]) requireElement(inherited, aid, label);

  const title = presentation.resolve("sh/nu58f2hs");
  title.text = "前人工作：随机采样物理扰动，生成多样化训练谱";
  configureText(title, { left: 58, top: 26, width: 1096, height: 56 }, {
    fontSize: 38,
    bold: true,
    color: NAVY,
    alignment: "left",
    wrap: "none",
  });

  const pageNumber = presentation.resolve("sh/9072xkry");
  pageNumber.text = "02 / 08";
  configureText(pageNumber, { left: 1176, top: 40, width: 48, height: 24 }, {
    fontSize: 14,
    color: MUTED,
    alignment: "right",
    wrap: "none",
  });

  const divider = presentation.resolve("sh/ozy1ofad");
  divider.position = { left: 58, top: 140, width: 1166, height: 0 };

  addTextBox(
    slide,
    "p2-prior-work-subtitle",
    { left: 58, top: 91, width: 1146, height: 34 },
    "已有 PXRD-ML 工作通过峰移、展宽、噪声、择优取向等随机变化，使训练谱覆盖更多实验情况。",
    {
      fontSize: 18,
      color: MUTED,
      alignment: "left",
      wrap: "none",
    },
  );

  const crystal = presentation.resolve("sh/b29kza94");
  crystal.text = "晶体结构";
  configureText(crystal, { left: 54, top: 263, width: 140, height: 58 }, {
    fontSize: 26,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  const compute = presentation.resolve("sh/a10jqpsj");
  compute.text = "计算 PXRD";
  compute.fill = "none";
  compute.line = { style: "solid", fill: "none", width: 0 };
  configureText(compute, { left: 264, top: 263, width: 166, height: 58 }, {
    fontSize: 25,
    bold: true,
    color: BLUE,
    alignment: "center",
    wrap: "none",
  });

  const perturb = presentation.resolve("sh/x4r21kru");
  perturb.text = "随机采样\n物理扰动";
  perturb.fill = ORANGE_FILL;
  perturb.line = { style: "solid", fill: ORANGE, width: 1.8 };
  configureText(perturb, { left: 484, top: 239, width: 222, height: 104 }, {
    fontSize: 26,
    bold: true,
    color: ORANGE,
    alignment: "center",
    wrap: "square",
    insets: { top: 8, right: 8, bottom: 8, left: 8 },
  });

  addTextBox(slide, "p2-arrow-1", { left: 198, top: 256, width: 58, height: 68 }, "→", {
    fontSize: 38,
    bold: true,
    color: BLUE,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p2-arrow-2", { left: 426, top: 256, width: 54, height: 68 }, "→", {
    fontSize: 38,
    bold: true,
    color: BLUE,
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p2-arrow-3", { left: 710, top: 256, width: 58, height: 68 }, "→", {
    fontSize: 38,
    bold: true,
    color: ORANGE,
    alignment: "center",
    wrap: "none",
  });

  addTextBox(
    slide,
    "p2-perturbation-examples",
    { left: 444, top: 358, width: 300, height: 28 },
    "峰移 · 展宽 · 背景/噪声 · 择优取向",
    {
      fontSize: 16,
      color: MUTED,
      alignment: "center",
      wrap: "none",
    },
  );

  addTextBox(
    slide,
    "p2-output-heading",
    { left: 804, top: 168, width: 398, height: 38 },
    "生成多种训练谱",
    {
      fontSize: 25,
      bold: true,
      color: NAVY,
      alignment: "center",
      wrap: "none",
    },
  );

  const chartA = presentation.resolve("ch/47uh8zqh");
  const chartB = presentation.resolve("ch/p83y1472");
  const chartC = presentation.resolve("ch/25cz6p8b");
  chartA.position = { left: 866, top: 212, width: 348, height: 82 };
  chartB.position = { left: 866, top: 307, width: 348, height: 82 };
  chartC.position = { left: 866, top: 402, width: 348, height: 86 };

  for (const [label, top] of [["扰动谱 A", 227], ["扰动谱 B", 322], ["扰动谱 C", 417]]) {
    addTextBox(slide, `p2-${label}`, { left: 772, top, width: 86, height: 32 }, label, {
      fontSize: 17,
      bold: true,
      color: INK,
      alignment: "right",
      wrap: "none",
    });
  }

  const oldSeparator1 = presentation.resolve("sh/ove9o7yd");
  const oldSeparator2 = presentation.resolve("sh/9wnqhczy");
  slide.shapes.deleteById(oldSeparator1.id);
  slide.shapes.deleteById(oldSeparator2.id);

  const transition = presentation.resolve("sh/mtwrmxg7");
  transition.text = "这些生成谱通常作为彼此独立的训练样本使用。";
  configureText(transition, { left: 170, top: 526, width: 940, height: 38 }, {
    fontSize: 21,
    bold: false,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  addTextBox(
    slide,
    "p2-literature-line",
    { left: 58, top: 610, width: 1164, height: 24 },
    "代表性工作：Oviedo et al. (2019); Szymanski et al. (2021); Lee et al. (2023); Schopmans et al. (2023)",
    {
      fontSize: 12.5,
      color: MUTED,
      alignment: "left",
      wrap: "none",
    },
  );
  addTextBox(
    slide,
    "p2-online-generation-note",
    { left: 58, top: 641, width: 1164, height: 22 },
    "Schopmans et al. (2023)：训练过程中在线生成（on-the-fly generation）训练数据。",
    {
      fontSize: 11.5,
      color: MUTED,
      alignment: "left",
      wrap: "none",
    },
  );

  slide.speakerNotes.textFrame.setText([
    "讲述提示：前人已经会随机采样峰移、展宽、背景、噪声和择优取向等变化，以扩大训练谱覆盖的实验情况。本页只交代这条已有路线；下一页再说明本工作的新增关系约束。",
    "",
    "[Sources]",
    "- https://doi.org/10.1038/s41524-019-0196-x",
    "- https://doi.org/10.1021/acs.chemmater.1c01071",
    "- https://doi.org/10.1002/aisy.202300140",
    "- https://doi.org/10.1039/D3DD00071K",
  ].join("\n"));

  const layoutBlob = await slide.export({ format: "layout" });
  const layoutText = await layoutBlob.text();
  await fs.writeFile(path.join(renderDir, "slide-02.layout.json"), layoutText, "utf8");
  const layout = JSON.parse(layoutText);
  const elements = layout.elements ?? [];

  const requiredPhrases = [
    "前人工作：随机采样物理扰动，生成多样化训练谱",
    "已有 PXRD-ML 工作通过峰移、展宽、噪声、择优取向等随机变化，使训练谱覆盖更多实验情况。",
    "晶体结构",
    "计算 PXRD",
    "随机采样",
    "物理扰动",
    "生成多种训练谱",
    "扰动谱 A",
    "扰动谱 B",
    "扰动谱 C",
    "峰移 · 展宽 · 背景/噪声 · 择优取向",
    "这些生成谱通常作为彼此独立的训练样本使用。",
    "代表性工作：Oviedo et al. (2019)",
    "Schopmans et al. (2023)：训练过程中在线生成",
  ];
  for (const phrase of requiredPhrases) {
    const found = elements.some((entry) => typeof entry.text === "string" && entry.text.includes(phrase));
    if (!found) throw new Error(`Missing slide-2 phrase: ${phrase}`);
  }

  for (const forbidden of [
    "我的方法",
    "一致性训练",
    "JS divergence",
    "同一结构判断一致",
    "同母结构关系",
    "物理不变量约束",
    "ResNet",
    "CPU",
    "GPU",
    "每小时数百万条谱",
  ]) {
    if (elements.some((entry) => typeof entry.text === "string" && entry.text.includes(forbidden))) {
      throw new Error(`Slide 2 still contains forbidden wording: ${forbidden}`);
    }
  }

  const titleEntry = elements.find((entry) => entry.text === "前人工作：随机采样物理扰动，生成多样化训练谱");
  const subtitleEntry = elements.find((entry) => entry.text === "已有 PXRD-ML 工作通过峰移、展宽、噪声、择优取向等随机变化，使训练谱覆盖更多实验情况。");
  if (!titleEntry || titleEntry.textLayout?.lineCount !== 1) throw new Error(`Slide-2 title wrapped: ${JSON.stringify(titleEntry)}`);
  if (!subtitleEntry || subtitleEntry.textLayout?.lineCount !== 1) throw new Error(`Slide-2 subtitle wrapped: ${JSON.stringify(subtitleEntry)}`);

  const chartCount = elements.filter((entry) => entry.kind === "chart").length;
  if (chartCount !== 3) throw new Error(`Expected exactly three charts on slide 2, found ${chartCount}`);

  const overflow = elements.filter((entry) => {
    const [left, top, width, height] = entry.bbox ?? [];
    if (![left, top, width, height].every(Number.isFinite)) return false;
    return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
  });
  if (overflow.length) throw new Error(`Slide-2 canvas overflow: ${JSON.stringify(overflow)}`);

  await writeBlob(
    path.join(renderDir, "slide-02.png"),
    await presentation.export({ slide, format: "png", scale: 1 }),
  );

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);
  console.log(JSON.stringify({ outputPath, renderedSlides: [2], slide2OverflowCount: 0, chartCount }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
