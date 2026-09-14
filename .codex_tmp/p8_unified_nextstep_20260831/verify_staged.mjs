import fs from "node:fs/promises";
import path from "node:path";
import JSZip from "jszip";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p8_unified_nextstep_20260831";
const stagedPath = path.join(tempDir, "staged-XRD_导师汇报.pptx");
const layoutPath = path.join(tempDir, "after-render", "slide-08.layout.json");
const sourceInspectPath = path.join(tempDir, "template-inspect.ndjson");

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function requireText(entries, phrase) {
  if (!entries.some((entry) => typeof entry.text === "string" && entry.text.includes(phrase))) {
    throw new Error(`Missing final slide-8 text: ${phrase}`);
  }
}

function firstSevenSignature(entries) {
  return entries
    .filter((entry) => Number.isInteger(entry.slide) && entry.slide <= 7)
    .map((entry) => ({
      kind: entry.kind,
      slide: entry.slide,
      name: entry.name ?? "",
      text: entry.text ?? "",
      preview: entry.preview ?? "",
      textLines: entry.textLines ?? null,
      bbox: entry.bbox ?? null,
      rows: entry.rows ?? null,
      cols: entry.cols ?? null,
      chartType: entry.chartType ?? "",
    }));
}

async function checkPlaceholders(pptxPath) {
  const bytes = await fs.readFile(pptxPath);
  const zip = await JSZip.loadAsync(bytes);
  const issues = [];
  const slideNames = Object.keys(zip.files)
    .filter((name) => /^ppt\/slides\/slide\d+\.xml$/.test(name))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  for (const name of slideNames) {
    const xml = await zip.file(name).async("string");
    for (const match of xml.matchAll(/<p:sp\b[\s\S]*?<\/p:sp>/g)) {
      const block = match[0];
      if (!/<p:ph\b/.test(block)) continue;
      const texts = [...block.matchAll(/<a:t>([\s\S]*?)<\/a:t>/g)].map((item) => item[1].replace(/&amp;/g, "&").trim());
      if (texts.join("").trim().length === 0) issues.push(`${name}: empty structural placeholder`);
    }
    if (/Click to add|Slide Number|Date|Footer/.test(xml)) issues.push(`${name}: visible default placeholder prompt`);
  }
  if (issues.length) throw new Error(`Placeholder QA failed: ${issues.join("; ")}`);
  return { slideXmlCount: slideNames.length, emptyPlaceholderCount: 0 };
}

async function main() {
  const presentation = await PresentationFile.importPptx(await FileBlob.load(stagedPath));
  if (presentation.slides.items.length !== 8) throw new Error("Round-trip deck does not contain eight slides");
  const inspect = await presentation.inspect({
    kind: "deck,slide,textbox,shape,chart,table,image,notes,layout",
    maxChars: 220000,
  });
  await fs.writeFile(path.join(tempDir, "roundtrip-inspect.ndjson"), inspect.ndjson, "utf8");
  const entries = parseInspect(inspect.ndjson);
  const sourceEntries = parseInspect(await fs.readFile(sourceInspectPath, "utf8"));
  if (JSON.stringify(firstSevenSignature(sourceEntries)) !== JSON.stringify(firstSevenSignature(entries))) {
    throw new Error("Round-trip structural comparison found a change on slides 1-7");
  }
  const p8 = entries.filter((entry) => entry.slide === 8);
  const title = p8.find((entry) => entry.name === "slide-2-title");
  if (
    !title
    || !title.text?.includes("下一步：从“判断一致”走向“参数可验证”")
    || !title.text?.includes("将物理约束从分类扩展到定量反演")
    || title.textLines !== 2
  ) {
    throw new Error(`Unexpected round-trip slide-8 title: ${JSON.stringify(title)}`);
  }
  for (const phrase of [
    "下一步：从“判断一致”走向“参数可验证”",
    "将物理约束从分类扩展到定量反演",
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
    "统一思路：把测量过程中隐含的物理关系，转化为模型约束。",
  ]) requireText(p8, phrase);
  if (p8.some((entry) => entry.kind === "table")) throw new Error("Slide 8 still contains the replaced source table");

  const layout = JSON.parse(await fs.readFile(layoutPath, "utf8"));
  const overflow = layout.elements.filter((element) => {
    const [left, top, width, height] = element.bbox ?? [];
    if (![left, top, width, height].every(Number.isFinite)) return false;
    return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
  });
  if (overflow.length) throw new Error(`Slide-8 canvas overflow: ${JSON.stringify(overflow)}`);

  const placeholders = await checkPlaceholders(stagedPath);
  const status = {
    status: "pass",
    slideCount: 8,
    modifiedSlides: [8],
    renderedSlides: [8],
    preservedSlides: [1, 2, 3, 4, 5, 6, 7],
    slide8OverflowCount: 0,
    ...placeholders,
  };
  await fs.writeFile(path.join(tempDir, "qa", "roundtrip-check.json"), `${JSON.stringify(status, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(status, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
