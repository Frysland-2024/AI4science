import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p5_test_context_20260829";
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(tempDir, "staged-XRD_导师汇报.pptx");
const beforeDir = path.join(tempDir, "before-render");
const afterDir = path.join(tempDir, "after-render");
const finalLayoutDir = path.join(tempDir, "final-layout");

const oldTitle = "5 次重复训练全部提升，平均 Macro-F1 +5.46 个百分点";
const newTitle = "模拟谱测试：5 次重复训练全部提升，平均 Macro-F1 +5.46 个百分点";
const oldSummaryLine = "5 次重复训练均提升";
const subtitle = "测试数据：Materials Project 留出的 2,109 个晶体结构，在训练范围之外的固定测量扰动条件下生成测试谱";
const bottomText = "在相同数据和训练设置下重复训练 5 次，结果都更好。";
const gainNames = ["p5-gain-1", "p5-gain-2", "p5-gain-3", "p5-gain-4", "p5-gain-5"];

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function requireEntry(entries, predicate, label) {
  const entry = entries.find(predicate);
  if (!entry) throw new Error(`Could not locate ${label}`);
  return entry;
}

function setTextBox(shape, text, position, style) {
  shape.text = text;
  shape.position = position;
  shape.text.style = {
    typeface: "Microsoft YaHei",
    ...style,
    wrap: "none",
    autoFit: "shrinkText",
    verticalAlignment: "middle",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(beforeDir, { recursive: true });
  await fs.mkdir(afterDir, { recursive: true });
  await fs.mkdir(finalLayoutDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 7) throw new Error("Expected seven slides");

  const before = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 100000,
  });
  await fs.writeFile(path.join(tempDir, "before-inspect.ndjson"), before.ndjson, "utf8");
  const entries = parseInspect(before.ndjson);
  const p5Entries = entries.filter((entry) => entry.slide === 5);
  const p5SlideEntry = requireEntry(p5Entries, (entry) => entry.kind === "slide", "slide 5");
  const p5 = presentation.resolve(p5SlideEntry.id);

  const titleEntry = requireEntry(p5Entries, (entry) => entry.name === "slide-2-title" && entry.text === oldTitle, "P5 title");
  const subtitleEntry = requireEntry(p5Entries, (entry) => entry.text === oldSummaryLine, "P5 reusable summary line");
  const chartEntry = requireEntry(p5Entries, (entry) => entry.kind === "chart", "P5 chart");
  const bottomEntry = requireEntry(p5Entries, (entry) => entry.name === "p5-repeat-explanation" && entry.text === bottomText, "P5 bottom sentence");

  await writeBlob(path.join(beforeDir, "slide-05.png"), await presentation.export({ slide: p5, format: "png", scale: 1 }));
  const beforeLayout = await p5.export({ format: "layout" });
  await fs.writeFile(path.join(beforeDir, "slide-05.layout.json"), await beforeLayout.text(), "utf8");

  for (let slideNumber = 2; slideNumber <= 6; slideNumber += 1) {
    const oldPageNumber = `${String(slideNumber).padStart(2, "0")} / 06`;
    const newPageNumber = `${String(slideNumber).padStart(2, "0")} / 07`;
    const pageNumberEntry = requireEntry(
      entries,
      (entry) => entry.slide === slideNumber && entry.text === oldPageNumber,
      `page number on slide ${slideNumber}`,
    );
    const pageNumber = presentation.resolve(pageNumberEntry.id);
    pageNumber.text = newPageNumber;
    pageNumber.position = {
      left: pageNumberEntry.bbox[0],
      top: pageNumberEntry.bbox[1],
      width: pageNumberEntry.bbox[2],
      height: pageNumberEntry.bbox[3],
    };
  }

  const title = presentation.resolve(titleEntry.id);
  setTextBox(
    title,
    newTitle,
    { left: 58, top: 28, width: 1096, height: 62 },
    { fontSize: 34, bold: true, color: "#153E6A", alignment: "left" },
  );

  const subtitleShape = presentation.resolve(subtitleEntry.id);
  subtitleShape.position = { left: 64, top: 108, width: 1158, height: 30 };
  subtitleShape.text.set([
    [
      {
        run: "测试数据：",
        textStyle: { bold: true, color: "#234B73", fontSize: "18px", typeface: "Microsoft YaHei" },
      },
      {
        run: "Materials Project 留出的 2,109 个晶体结构，在训练范围之外的固定测量扰动条件下生成测试谱",
        textStyle: { bold: false, color: "#3F5368", fontSize: "18px", typeface: "Microsoft YaHei" },
      },
    ],
  ]);
  subtitleShape.text.fontSize = 18;
  subtitleShape.text.typeface = "Microsoft YaHei";
  subtitleShape.text.color = "#3F5368";
  subtitleShape.text.alignment = "left";
  subtitleShape.text.verticalAlignment = "middle";
  subtitleShape.text.wrap = "none";
  subtitleShape.text.autoFit = "shrinkText";
  subtitleShape.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  for (const name of gainNames) {
    const gainEntry = requireEntry(p5Entries, (entry) => entry.name === name, name);
    const gain = presentation.resolve(gainEntry.id);
    gain.position = {
      left: gainEntry.bbox[0],
      top: gainEntry.bbox[1] + 35,
      width: gainEntry.bbox[2],
      height: gainEntry.bbox[3],
    };
  }

  const chart = presentation.resolve(chartEntry.id);
  chart.position = { left: 62, top: 170, width: 880, height: 470 };

  const bottom = presentation.resolve(bottomEntry.id);
  bottom.text = bottomText;
  bottom.position = { left: 62, top: 652, width: 880, height: 32 };

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  await writeBlob(path.join(afterDir, "slide-05.png"), await presentation.export({ slide: p5, format: "png", scale: 1 }));
  const afterLayout = await p5.export({ format: "layout" });
  await fs.writeFile(path.join(afterDir, "slide-05.layout.json"), await afterLayout.text(), "utf8");

  for (let index = 0; index < presentation.slides.items.length; index += 1) {
    const layout = await presentation.slides.items[index].export({ format: "layout" });
    await fs.writeFile(
      path.join(finalLayoutDir, `slide-${String(index + 1).padStart(2, "0")}.layout.json`),
      await layout.text(),
      "utf8",
    );
  }

  const after = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 100000,
  });
  await fs.writeFile(path.join(tempDir, "after-inspect.ndjson"), after.ndjson, "utf8");
  const afterEntries = parseInspect(after.ndjson);
  const afterP5 = afterEntries.filter((entry) => entry.slide === 5);
  const afterTitle = requireEntry(afterP5, (entry) => entry.text === newTitle, "updated P5 title");
  const afterSubtitle = requireEntry(afterP5, (entry) => entry.text === subtitle, "updated P5 subtitle");
  const afterChart = requireEntry(afterP5, (entry) => entry.kind === "chart", "updated P5 chart");
  const afterBottom = requireEntry(afterP5, (entry) => entry.text === bottomText, "unchanged P5 bottom sentence");
  if (afterTitle.textLines !== 1 || afterSubtitle.textLines !== 1) {
    throw new Error(`Unexpected P5 line wrapping: ${JSON.stringify({ afterTitle, afterSubtitle })}`);
  }
  if (JSON.stringify(afterChart.bbox) !== JSON.stringify([62, 170, 880, 470])) {
    throw new Error(`Unexpected chart geometry: ${JSON.stringify(afterChart.bbox)}`);
  }
  if (JSON.stringify(afterBottom.bbox) !== JSON.stringify([62, 652, 880, 32])) {
    throw new Error(`Unexpected bottom geometry: ${JSON.stringify(afterBottom.bbox)}`);
  }

  for (let slideNumber = 2; slideNumber <= 7; slideNumber += 1) {
    const expectedPageNumber = `${String(slideNumber).padStart(2, "0")} / 07`;
    requireEntry(
      afterEntries,
      (entry) => entry.slide === slideNumber && entry.text === expectedPageNumber,
      `correct page number on slide ${slideNumber}`,
    );
  }

  const p7Text = afterEntries.filter((entry) => entry.slide === 7).map((entry) => entry.text).filter(Boolean).join("\n");
  for (const phrase of [
    "在相同数据和训练设置下\n重复训练 5 次，结果都更好。",
    "在另一套真实实验谱上直接测试，我的方法仍然表现出稳定增益。",
  ]) {
    if (!p7Text.includes(phrase)) throw new Error(`Approved P7 wording was not preserved: ${phrase}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
