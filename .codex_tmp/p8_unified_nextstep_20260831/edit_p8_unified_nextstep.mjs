import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p8_unified_nextstep_20260831";
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(tempDir, "staged-XRD_导师汇报.pptx");
const beforeDir = path.join(tempDir, "before-render");
const afterDir = path.join(tempDir, "after-render");
const finalLayoutDir = path.join(tempDir, "final-layout");

const titleText = "下一步：从“判断一致”走向“参数可验证”";
const subtitleText = "将物理约束从分类扩展到定量反演";
const unifiedText = "统一思路：把测量过程中隐含的物理关系，转化为模型约束。";

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function requireEntry(entries, predicate, label) {
  const entry = entries.find(predicate);
  if (!entry) throw new Error(`Could not locate ${label}`);
  return entry;
}

function normalizeEntries(entries) {
  return entries
    .filter((entry) => Number.isInteger(entry.slide) && entry.slide <= 7)
    .map((entry) => {
      const { id, ...rest } = entry;
      return rest;
    });
}

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

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(beforeDir, { recursive: true });
  await fs.mkdir(afterDir, { recursive: true });
  await fs.mkdir(finalLayoutDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 8) throw new Error("Expected eight-slide starter deck");

  const before = await presentation.inspect({
    kind: "deck,slide,textbox,shape,chart,table,image,notes,layout",
    maxChars: 220000,
  });
  await fs.writeFile(path.join(tempDir, "before-inspect.ndjson"), before.ndjson, "utf8");
  const beforeEntries = parseInspect(before.ndjson);
  const beforeFirstSeven = normalizeEntries(beforeEntries);
  const p8 = beforeEntries.filter((entry) => entry.slide === 8);
  const slideEntry = requireEntry(p8, (entry) => entry.kind === "slide", "slide 8");
  const slide = presentation.resolve(slideEntry.id);

  await writeBlob(
    path.join(beforeDir, "slide-08.png"),
    await presentation.export({ slide, format: "png", scale: 1 }),
  );

  const title = presentation.resolve(requireEntry(
    p8,
    (entry) => entry.kind === "textbox" && entry.name === "slide-2-title" && entry.text === "14,060 个晶体结构，覆盖 5 类常见测量扰动",
    "P8 title",
  ).id);
  title.position = { left: 58, top: 18, width: 1050, height: 82 };
  title.text.set([
    { runs: [{ run: titleText, textStyle: { bold: true, color: "#153E6A", fontSize: "34px", typeface: "Microsoft YaHei" } }], spaceAfter: 2 },
    { runs: [{ run: subtitleText, textStyle: { bold: false, color: "#536779", fontSize: "18px", typeface: "Microsoft YaHei" } }] },
  ]);
  title.text.style = {
    typeface: "Microsoft YaHei",
    alignment: "left",
    verticalAlignment: "middle",
    wrap: "none",
    autoFit: "shrinkText",
    lineSpacing: 0.95,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };

  const pageNumber = presentation.resolve(requireEntry(p8, (entry) => entry.kind === "textbox" && entry.text === "04 / 07", "P8 page number").id);
  pageNumber.text = "08 / 08";

  const leftHeading = presentation.resolve(requireEntry(p8, (entry) => entry.kind === "textbox" && entry.text === "14,060", "P8 left heading").id);
  leftHeading.text = "现在：用物理不变量约束分类";
  configureText(leftHeading, { left: 72, top: 174, width: 305, height: 42 }, {
    fontSize: 22,
    bold: true,
    color: "#153E6A",
    alignment: "left",
    wrap: "none",
  });

  const currentFlow = presentation.resolve(requireEntry(
    p8,
    (entry) => entry.kind === "textbox" && entry.text === "来自 Materials Project 的晶体结构",
    "P8 current flow",
  ).id);
  currentFlow.position = { left: 72, top: 246, width: 305, height: 84 };
  currentFlow.text.set([
    [{ run: "谱 A              谱 B", textStyle: { bold: true, color: "#27384A", fontSize: "24px", typeface: "Microsoft YaHei" } }],
    [{ run: "↓                  ↓", textStyle: { bold: true, color: "#8A99A8", fontSize: "18px", typeface: "Microsoft YaHei" } }],
  ]);
  currentFlow.text.style = {
    typeface: "Microsoft YaHei",
    color: "#42566A",
    alignment: "center",
    verticalAlignment: "middle",
    wrap: "square",
    autoFit: "shrinkText",
    lineSpacing: 0.95,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };

  const prediction = presentation.resolve(requireEntry(p8, (entry) => entry.kind === "textbox" && entry.text === "训练 / 验证 / 测试", "P8 prediction endpoint").id);
  prediction.text = "预测 A  ≈  预测 B";
  configureText(prediction, { left: 72, top: 332, width: 305, height: 72 }, {
    fontSize: 31,
    bold: true,
    color: "#07579D",
    alignment: "center",
    wrap: "none",
  });

  const invariant = presentation.resolve(requireEntry(p8, (entry) => entry.kind === "textbox" && entry.text === "9,842 / 2,109 / 2,109", "P8 invariant statement").id);
  invariant.position = { left: 72, top: 416, width: 305, height: 48 };
  invariant.text.set([
    [
      { run: "谱可以变，结构不变", textStyle: { bold: true, color: "#153E6A", fontSize: "19px", typeface: "Microsoft YaHei" } },
    ],
  ]);
  invariant.text.typeface = "Microsoft YaHei";
  invariant.text.alignment = "center";
  invariant.text.verticalAlignment = "middle";
  invariant.text.wrap = "none";
  invariant.text.autoFit = "shrinkText";
  invariant.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  const separator = presentation.resolve(requireEntry(p8, (entry) => entry.kind === "shape" && entry.name === "直接连接符 18", "P8 separator").id);
  slide.shapes.deleteById(separator.id);

  const transition = slide.shapes.add({
    geometry: "textbox",
    name: "p8-transition",
    position: { left: 390, top: 250, width: 125, height: 210 },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  transition.text.set([
    { runs: [{ run: "→", textStyle: { bold: true, color: "#07579D", fontSize: "58px", typeface: "Microsoft YaHei" } }], spaceAfter: 8 },
    { runs: [{ run: "从“判断一致”", textStyle: { bold: true, color: "#42566A", fontSize: "16px", typeface: "Microsoft YaHei" } }], spaceAfter: 0 },
    { runs: [{ run: "到“参数可验证”", textStyle: { bold: true, color: "#42566A", fontSize: "16px", typeface: "Microsoft YaHei" } }] },
  ]);
  transition.text.style = {
    typeface: "Microsoft YaHei",
    alignment: "center",
    verticalAlignment: "middle",
    wrap: "square",
    autoFit: "shrinkText",
    lineSpacing: 0.95,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };

  const table = presentation.resolve(requireEntry(p8, (entry) => entry.kind === "table", "P8 inversion flow table").id);
  slide.tables.deleteById(table.id);

  const nextHeading = slide.shapes.add({
    geometry: "textbox",
    name: "p8-next-heading",
    position: { left: 535, top: 174, width: 665, height: 42 },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  nextHeading.text = "下一步：用前向物理关系验证参数";
  nextHeading.text.style = {
    typeface: "Microsoft YaHei",
    fontSize: 23,
    bold: true,
    color: "#153E6A",
    alignment: "left",
    verticalAlignment: "middle",
    wrap: "none",
    autoFit: "shrinkText",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };

  const nextFlow = slide.shapes.add({
    geometry: "textbox",
    name: "p8-next-flow",
    position: { left: 535, top: 236, width: 665, height: 142 },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  nextFlow.text.set([
    {
      runs: [
        { run: "输入 XRD", textStyle: { bold: true, color: "#27384A", fontSize: "20px", typeface: "Microsoft YaHei" } },
        { run: "  →  ", textStyle: { bold: true, color: "#8A99A8", fontSize: "20px", typeface: "Microsoft YaHei" } },
        { run: "反演物理参数", textStyle: { bold: true, color: "#153E6A", fontSize: "20px", typeface: "Microsoft YaHei" } },
        { run: "  →  ", textStyle: { bold: true, color: "#8A99A8", fontSize: "20px", typeface: "Microsoft YaHei" } },
        { run: "前向生成 XRD", textStyle: { bold: true, color: "#27384A", fontSize: "20px", typeface: "Microsoft YaHei" } },
        { run: "  →  ", textStyle: { bold: true, color: "#8A99A8", fontSize: "20px", typeface: "Microsoft YaHei" } },
        { run: "重建 XRD", textStyle: { bold: true, color: "#27384A", fontSize: "20px", typeface: "Microsoft YaHei" } },
      ],
      spaceAfter: 8,
    },
    { runs: [{ run: "a、c、零点偏移、FWHM", textStyle: { bold: false, color: "#536779", fontSize: "17px", typeface: "Microsoft YaHei" } }], spaceAfter: 4 },
    { runs: [{ run: "↓", textStyle: { bold: true, color: "#8A99A8", fontSize: "22px", typeface: "Microsoft YaHei" } }] },
  ]);
  nextFlow.text.style = {
    typeface: "Microsoft YaHei",
    alignment: "center",
    verticalAlignment: "middle",
    wrap: "none",
    autoFit: "shrinkText",
    lineSpacing: 0.95,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };

  const reconstruction = slide.shapes.add({
    geometry: "textbox",
    name: "p8-reconstruction",
    position: { left: 535, top: 384, width: 665, height: 82 },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  reconstruction.text = "重建谱  ≈  输入谱";
  reconstruction.text.style = {
    typeface: "Microsoft YaHei",
    fontSize: 40,
    bold: true,
    color: "#07579D",
    alignment: "center",
    verticalAlignment: "middle",
    wrap: "none",
    autoFit: "shrinkText",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };

  const explanation = slide.shapes.add({
    geometry: "textbox",
    name: "p8-explanation",
    position: { left: 560, top: 472, width: 615, height: 50 },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  explanation.text = "参数合理，就应该能够重新解释原始实验谱。";
  explanation.text.style = {
    typeface: "Microsoft YaHei",
    fontSize: 20,
    bold: false,
    color: "#42566A",
    alignment: "center",
    verticalAlignment: "middle",
    wrap: "none",
    autoFit: "shrinkText",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };

  const synthesis = presentation.resolve(requireEntry(
    p8,
    (entry) => entry.kind === "textbox" && entry.text?.includes("按晶体结构划分") && entry.text?.includes("训练时实时生成谱"),
    "P8 synthesis",
  ).id);
  synthesis.position = { left: 72, top: 622, width: 1128, height: 54 };
  synthesis.text.set([
    {
      runs: [
        { run: "统一思路：", textStyle: { bold: true, color: "#153E6A", fontSize: "20px", typeface: "Microsoft YaHei" } },
        { run: "把测量过程中隐含的物理关系，转化为模型约束。", textStyle: { bold: false, color: "#42566A", fontSize: "20px", typeface: "Microsoft YaHei" } },
      ],
    },
  ]);
  synthesis.text.typeface = "Microsoft YaHei";
  synthesis.text.alignment = "center";
  synthesis.text.verticalAlignment = "middle";
  synthesis.text.wrap = "square";
  synthesis.text.autoFit = "shrinkText";
  synthesis.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  const after = await presentation.inspect({
    kind: "deck,slide,textbox,shape,chart,table,image,notes,layout",
    maxChars: 220000,
  });
  await fs.writeFile(path.join(tempDir, "after-inspect.ndjson"), after.ndjson, "utf8");
  const afterEntries = parseInspect(after.ndjson);
  const afterFirstSeven = normalizeEntries(afterEntries);
  if (JSON.stringify(beforeFirstSeven) !== JSON.stringify(afterFirstSeven)) {
    throw new Error("Slides 1-7 changed during slide-8 authoring");
  }

  const afterP8 = afterEntries.filter((entry) => entry.slide === 8);
  const finalTitle = requireEntry(
    afterP8,
    (entry) => entry.text?.includes(titleText) && entry.text?.includes(subtitleText),
    "final P8 title and subtitle",
  );
  const finalHeading = requireEntry(afterP8, (entry) => entry.name === "p8-next-heading", "final P8 next-step heading");
  const finalFlow = requireEntry(afterP8, (entry) => entry.name === "p8-next-flow", "final P8 next-step flow");
  const finalTransition = requireEntry(afterP8, (entry) => entry.name === "p8-transition", "final P8 transition");
  const finalReconstruction = requireEntry(afterP8, (entry) => entry.name === "p8-reconstruction", "final P8 reconstruction relation");
  const finalExplanation = requireEntry(afterP8, (entry) => entry.name === "p8-explanation", "final P8 explanation");
  const finalSynthesis = requireEntry(afterP8, (entry) => entry.text?.includes(unifiedText), "final P8 synthesis");
  if (finalTitle.textLines !== 2) throw new Error(`P8 title/subtitle should use exactly two lines: ${JSON.stringify(finalTitle)}`);
  for (const phrase of [
    titleText,
    subtitleText,
    "现在：用物理不变量约束分类",
    "谱 A",
    "谱 B",
    "预测 A  ≈  预测 B",
    "谱可以变，结构不变",
    "从“判断一致”",
    "到“参数可验证”",
    "下一步：用前向物理关系验证参数",
    "输入 XRD",
    "反演物理参数",
    "a、c、零点偏移、FWHM",
    "前向生成 XRD",
    "重建 XRD",
    "重建谱  ≈  输入谱",
    "参数合理，就应该能够重新解释原始实验谱。",
    unifiedText,
  ]) {
    const found = afterP8.some((entry) => typeof entry.text === "string" && entry.text.includes(phrase));
    if (!found) throw new Error(`Missing slide-8 phrase: ${phrase}`);
  }
  if (finalHeading.textLines !== 1) throw new Error(`P8 next-step heading wrapped: ${JSON.stringify(finalHeading)}`);
  if (finalFlow.textLines > 3) throw new Error(`P8 next-step flow wrapped unexpectedly: ${JSON.stringify(finalFlow)}`);
  if (finalTransition.textLines > 3) throw new Error(`P8 transition wrapped unexpectedly: ${JSON.stringify(finalTransition)}`);
  if (finalReconstruction.textLines !== 1) throw new Error(`P8 reconstruction relation wrapped: ${JSON.stringify(finalReconstruction)}`);
  if (finalExplanation.textLines !== 1) throw new Error(`P8 explanation wrapped: ${JSON.stringify(finalExplanation)}`);
  if (afterP8.some((entry) => entry.kind === "table")) throw new Error("Replaced P8 table still present");
  if (finalSynthesis.textLines !== 1) throw new Error(`Bottom synthesis wrapped unexpectedly: ${JSON.stringify(finalSynthesis)}`);

  for (let index = 0; index < presentation.slides.items.length; index += 1) {
    const item = presentation.slides.items[index];
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const layout = await item.export({ format: "layout" });
    await fs.writeFile(path.join(finalLayoutDir, `${stem}.layout.json`), await layout.text(), "utf8");
  }

  await writeBlob(
    path.join(afterDir, "slide-08.png"),
    await presentation.export({ slide, format: "png", scale: 1 }),
  );
  const slide8Layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(afterDir, "slide-08.layout.json"), await slide8Layout.text(), "utf8");

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);
  console.log(JSON.stringify({ outputPath, slideCount: presentation.slides.items.length }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
