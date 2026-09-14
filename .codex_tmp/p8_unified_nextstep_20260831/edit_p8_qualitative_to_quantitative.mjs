import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p8_unified_nextstep_20260831";
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(tempDir, "staged-XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "after-render");

const titleText = "下一步：把同一种物理约束思想，从分类延伸到定量反演";
const unifiedText = "统一思路：把已知的物理关系，转化为模型训练和结果判断时必须满足的约束。";

function configureText(shape, position, style = {}) {
  shape.position = position;
  shape.text.typeface = "Microsoft YaHei";
  shape.text.color = style.color ?? "#153E6A";
  shape.text.fontSize = style.fontSize ?? 20;
  shape.text.bold = style.bold ?? false;
  shape.text.alignment = style.alignment ?? "left";
  shape.text.verticalAlignment = style.verticalAlignment ?? "middle";
  shape.text.wrap = style.wrap ?? "square";
  shape.text.autoFit = style.autoFit ?? "shrinkText";
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

function requireLayoutElement(elements, predicate, label) {
  const element = elements.find(predicate);
  if (!element?.aid) throw new Error(`Could not locate ${label} on slide 8`);
  return element;
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  const slide = presentation.slides.items[7];
  if (!slide) throw new Error("Could not locate slide 8");

  const beforeLayout = JSON.parse(await (await slide.export({ format: "layout" })).text());
  const inherited = beforeLayout.elements ?? [];

  const title = presentation.resolve(requireLayoutElement(
    inherited,
    (entry) => entry.name === "slide-2-title",
    "title slot",
  ).aid);
  title.text = titleText;
  configureText(title, { left: 58, top: 24, width: 1080, height: 58 }, {
    fontSize: 34,
    bold: true,
    color: "#153E6A",
    alignment: "left",
    wrap: "none",
  });

  const pageNumber = presentation.resolve(requireLayoutElement(
    inherited,
    (entry) => entry.text === "04 / 07",
    "page-number slot",
  ).aid);
  pageNumber.text = "08 / 08";

  const leftHeading = presentation.resolve(requireLayoutElement(
    inherited,
    (entry) => entry.text === "14,060",
    "left-heading slot",
  ).aid);
  leftHeading.text = "当前：定性判断";
  configureText(leftHeading, { left: 72, top: 148, width: 382, height: 40 }, {
    fontSize: 24,
    bold: true,
    color: "#153E6A",
    alignment: "left",
    wrap: "none",
  });

  const leftSubtitle = presentation.resolve(requireLayoutElement(
    inherited,
    (entry) => entry.text === "来自 Materials Project 的晶体结构",
    "left-subtitle slot",
  ).aid);
  leftSubtitle.text = "同一结构的不同测量谱，模型判断应一致";
  configureText(leftSubtitle, { left: 72, top: 190, width: 382, height: 48 }, {
    fontSize: 18,
    color: "#536779",
    alignment: "left",
    wrap: "square",
  });

  const sameStructure = presentation.resolve(requireLayoutElement(
    inherited,
    (entry) => entry.text === "训练 / 验证 / 测试",
    "same-structure slot",
  ).aid);
  sameStructure.text = "同一晶体结构";
  configureText(sameStructure, { left: 72, top: 254, width: 382, height: 34 }, {
    fontSize: 21,
    bold: true,
    color: "#27384A",
    alignment: "center",
    wrap: "none",
  });

  addTextBox(slide, "p8-left-branch", { left: 72, top: 286, width: 382, height: 30 }, "↙                         ↘", {
    fontSize: 20,
    bold: true,
    color: "#8A99A8",
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p8-spectrum-a", { left: 86, top: 318, width: 140, height: 36 }, "谱 A", {
    fontSize: 22,
    bold: true,
    color: "#27384A",
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p8-spectrum-b", { left: 300, top: 318, width: 140, height: 36 }, "谱 B", {
    fontSize: 22,
    bold: true,
    color: "#27384A",
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p8-spectrum-a-arrow", { left: 86, top: 352, width: 140, height: 28 }, "↓", {
    fontSize: 18,
    bold: true,
    color: "#8A99A8",
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p8-spectrum-b-arrow", { left: 300, top: 352, width: 140, height: 28 }, "↓", {
    fontSize: 18,
    bold: true,
    color: "#8A99A8",
    alignment: "center",
    wrap: "none",
  });

  const prediction = presentation.resolve(requireLayoutElement(
    inherited,
    (entry) => entry.text === "9,842 / 2,109 / 2,109",
    "prediction-relation slot",
  ).aid);
  prediction.text = "预测 A  ≈  预测 B";
  configureText(prediction, { left: 72, top: 384, width: 382, height: 62 }, {
    fontSize: 31,
    bold: true,
    color: "#07579D",
    alignment: "center",
    wrap: "none",
  });

  addTextBox(slide, "p8-left-physical-relation", { left: 72, top: 462, width: 382, height: 54 }, "物理关系：测量条件可以变，晶体结构不变", {
    fontSize: 18,
    bold: true,
    color: "#153E6A",
    alignment: "center",
    wrap: "square",
  });

  const separator = presentation.resolve(requireLayoutElement(
    inherited,
    (entry) => entry.name === "直接连接符 18",
    "separator",
  ).aid);
  slide.shapes.deleteById(separator.id);

  const stageTransition = addTextBox(slide, "p8-stage-transition", { left: 455, top: 252, width: 116, height: 238 }, "", {
    alignment: "center",
    wrap: "square",
  });
  stageTransition.text.set([
    { runs: [{ run: "定性判断", textStyle: { bold: true, color: "#07579D", fontSize: "23px", typeface: "Microsoft YaHei" } }], spaceAfter: 6 },
    { runs: [{ run: "→", textStyle: { bold: true, color: "#07579D", fontSize: "40px", typeface: "Microsoft YaHei" } }], spaceAfter: 6 },
    { runs: [{ run: "定量反演", textStyle: { bold: true, color: "#07579D", fontSize: "23px", typeface: "Microsoft YaHei" } }] },
  ]);
  stageTransition.text.alignment = "center";
  stageTransition.text.verticalAlignment = "middle";
  stageTransition.text.wrap = "square";
  stageTransition.text.autoFit = "shrinkText";
  stageTransition.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  const table = presentation.resolve(requireLayoutElement(
    inherited,
    (entry) => entry.kind === "table",
    "right-side table",
  ).aid);
  slide.tables.deleteById(table.id);

  addTextBox(slide, "p8-next-heading", { left: 575, top: 148, width: 633, height: 40 }, "下一步：定量反演", {
    fontSize: 24,
    bold: true,
    color: "#153E6A",
    alignment: "left",
    wrap: "none",
  });
  addTextBox(slide, "p8-next-subtitle", { left: 575, top: 190, width: 633, height: 48 }, "反演出的参数，应能够重新解释输入实验谱", {
    fontSize: 18,
    color: "#536779",
    alignment: "left",
    wrap: "square",
  });
  addTextBox(slide, "p8-input-xrd", { left: 575, top: 252, width: 633, height: 38 }, "输入实验 XRD", {
    fontSize: 22,
    bold: true,
    color: "#27384A",
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p8-input-arrow", { left: 575, top: 289, width: 633, height: 26 }, "↓", {
    fontSize: 18,
    bold: true,
    color: "#8A99A8",
    alignment: "center",
    wrap: "none",
  });

  const parameterBlock = addTextBox(slide, "p8-parameter-block", { left: 575, top: 316, width: 633, height: 70 }, "", {
    alignment: "center",
    wrap: "square",
  });
  parameterBlock.text.set([
    { runs: [{ run: "反演物理参数", textStyle: { bold: true, color: "#153E6A", fontSize: "22px", typeface: "Microsoft YaHei" } }], spaceAfter: 2 },
    { runs: [{ run: "a、c、零点偏移、FWHM", textStyle: { bold: false, color: "#536779", fontSize: "16px", typeface: "Microsoft YaHei" } }] },
  ]);
  parameterBlock.text.alignment = "center";
  parameterBlock.text.verticalAlignment = "middle";
  parameterBlock.text.wrap = "square";
  parameterBlock.text.autoFit = "shrinkText";
  parameterBlock.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  addTextBox(slide, "p8-parameter-arrow", { left: 575, top: 385, width: 633, height: 26 }, "↓", {
    fontSize: 18,
    bold: true,
    color: "#8A99A8",
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p8-regenerate-xrd", { left: 575, top: 412, width: 633, height: 40 }, "根据参数重新生成 XRD", {
    fontSize: 22,
    bold: true,
    color: "#27384A",
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p8-regenerate-arrow", { left: 575, top: 452, width: 633, height: 26 }, "↓", {
    fontSize: 18,
    bold: true,
    color: "#8A99A8",
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p8-generation-relation", { left: 575, top: 482, width: 633, height: 76 }, "生成谱  ≈  输入谱", {
    fontSize: 40,
    bold: true,
    color: "#07579D",
    alignment: "center",
    wrap: "none",
  });
  addTextBox(slide, "p8-right-physical-relation", { left: 575, top: 562, width: 633, height: 54 }, "物理关系：参数如果合理，生成的谱就应该与实验谱相符", {
    fontSize: 18,
    bold: true,
    color: "#153E6A",
    alignment: "center",
    wrap: "square",
  });

  const synthesis = presentation.resolve(requireLayoutElement(
    inherited,
    (entry) => entry.text?.includes("按晶体结构划分") && entry.text?.includes("训练时实时生成谱"),
    "bottom synthesis slot",
  ).aid);
  synthesis.text = unifiedText;
  configureText(synthesis, { left: 72, top: 644, width: 1136, height: 42 }, {
    fontSize: 18,
    bold: false,
    color: "#42566A",
    alignment: "center",
    wrap: "none",
  });

  const layoutBlob = await slide.export({ format: "layout" });
  const layoutText = await layoutBlob.text();
  await fs.writeFile(path.join(renderDir, "slide-08.layout.json"), layoutText, "utf8");
  const layout = JSON.parse(layoutText);
  const elements = layout.elements ?? [];

  for (const phrase of [
    titleText,
    "当前：定性判断",
    "同一结构的不同测量谱，模型判断应一致",
    "同一晶体结构",
    "谱 A",
    "谱 B",
    "预测 A  ≈  预测 B",
    "物理关系：测量条件可以变，晶体结构不变",
    "定性判断",
    "定量反演",
    "下一步：定量反演",
    "反演出的参数，应能够重新解释输入实验谱",
    "输入实验 XRD",
    "反演物理参数",
    "a、c、零点偏移、FWHM",
    "根据参数重新生成 XRD",
    "生成谱  ≈  输入谱",
    "物理关系：参数如果合理，生成的谱就应该与实验谱相符",
    unifiedText,
  ]) {
    const found = elements.some((entry) => typeof entry.text === "string" && entry.text.includes(phrase));
    if (!found) throw new Error(`Missing slide-8 phrase: ${phrase}`);
  }
  if (elements.some((entry) => typeof entry.text === "string" && entry.text.includes("同一个模型"))) {
    throw new Error("Slide 8 still contains the removed implementation-level model label");
  }
  if (elements.some((entry) => entry.kind === "table")) throw new Error("Slide 8 still contains the replaced source table");

  const titleEntry = elements.find((entry) => entry.name === "slide-2-title");
  const predictionEntry = elements.find((entry) => entry.text === "预测 A  ≈  预测 B");
  const generationEntry = elements.find((entry) => entry.name === "p8-generation-relation");
  const transitionEntry = elements.find((entry) => entry.name === "p8-stage-transition");
  const synthesisEntry = elements.find((entry) => entry.text === unifiedText);
  if (!titleEntry || titleEntry.textLayout?.lineCount !== 1) throw new Error(`Slide-8 title wrapped: ${JSON.stringify(titleEntry)}`);
  if (!predictionEntry || predictionEntry.textLayout?.lineCount !== 1) throw new Error(`Prediction relation wrapped: ${JSON.stringify(predictionEntry)}`);
  if (!generationEntry || generationEntry.textLayout?.lineCount !== 1) throw new Error(`Generation relation wrapped: ${JSON.stringify(generationEntry)}`);
  if (!transitionEntry || transitionEntry.textLayout?.lineCount > 3) throw new Error(`Stage transition wrapped unexpectedly: ${JSON.stringify(transitionEntry)}`);
  if (!synthesisEntry || synthesisEntry.textLayout?.lineCount !== 1) throw new Error(`Bottom synthesis wrapped: ${JSON.stringify(synthesisEntry)}`);

  const overflow = elements.filter((element) => {
    const [left, top, width, height] = element.bbox ?? [];
    if (![left, top, width, height].every(Number.isFinite)) return false;
    return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
  });
  if (overflow.length) throw new Error(`Slide-8 canvas overflow: ${JSON.stringify(overflow)}`);

  await writeBlob(
    path.join(renderDir, "slide-08.png"),
    await presentation.export({ slide, format: "png", scale: 1 }),
  );

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);
  console.log(JSON.stringify({ outputPath, renderedSlides: [8], slide8OverflowCount: 0 }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
