import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/cnrs_slide7_20260828";
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(tempDir, "staged-XRD_导师汇报.pptx");
const beforeDir = path.join(tempDir, "before-render");
const afterDir = path.join(tempDir, "after-render");
const finalLayoutDir = path.join(tempDir, "final-layout");

const baseline = [0.2067, 0.1469, 0.1842, 0.2149, 0.1892];
const consistency = [0.2212, 0.1756, 0.1971, 0.2295, 0.2120];
const categories = ["重复 1", "重复 2", "重复 3", "重复 4", "重复 5"];
const gains = ["+1.45 pp", "+2.87 pp", "+1.29 pp", "+1.46 pp", "+2.28 pp"];
const groupCenters = [212, 371, 530, 689, 848];

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function requireEntry(entries, predicate, label) {
  const entry = entries.find(predicate);
  if (!entry) throw new Error(`Could not locate ${label}`);
  return entry;
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function setTextBox(shape, text, position, style) {
  shape.text = text;
  shape.position = position;
  shape.text.style = {
    typeface: "Microsoft YaHei",
    ...style,
    wrap: "square",
    autoFit: "shrinkText",
    verticalAlignment: "middle",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
}

async function main() {
  await fs.mkdir(beforeDir, { recursive: true });
  await fs.mkdir(afterDir, { recursive: true });
  await fs.mkdir(finalLayoutDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 7) {
    throw new Error(`Expected 7 starter slides, found ${presentation.slides.items.length}`);
  }

  const beforeInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 100000,
  });
  await fs.writeFile(path.join(tempDir, "before-inspect.ndjson"), beforeInspect.ndjson, "utf8");
  const entries = parseInspect(beforeInspect.ndjson);
  const p7Entries = entries.filter((entry) => entry.slide === 7);
  const p7SlideEntry = requireEntry(p7Entries, (entry) => entry.kind === "slide", "slide 7");
  const p7 = presentation.resolve(p7SlideEntry.id);

  await writeBlob(
    path.join(beforeDir, "slide-07.png"),
    await presentation.export({ slide: p7, format: "png", scale: 1 }),
  );
  const beforeLayout = await p7.export({ format: "layout" });
  await fs.writeFile(path.join(beforeDir, "slide-07.layout.json"), await beforeLayout.text(), "utf8");

  const titleEntry = requireEntry(p7Entries, (entry) => entry.name === "slide-2-title", "P7 title");
  const title = presentation.resolve(titleEntry.id);
  setTextBox(
    title,
    "完全不用 CNRS 标注数据再训练，5 次重复结果仍全部提升",
    { left: 58, top: 28, width: 1096, height: 62 },
    { fontSize: 34, bold: true, color: "#153E6A", alignment: "left" },
  );
  title.text.wrap = "none";

  const pageEntry = requireEntry(p7Entries, (entry) => entry.text === "05 / 06", "P7 page marker");
  presentation.resolve(pageEntry.id).text = "07 / 07";

  const conditionEntry = requireEntry(p7Entries, (entry) => entry.text === "平均 +5.46 pp", "P7 inherited condition line");
  setTextBox(
    presentation.resolve(conditionEntry.id),
    "CNRS-318｜独立真实实验谱来源｜不使用 CNRS 标注数据再训练，直接测试",
    { left: 64, top: 108, width: 1158, height: 32 },
    { fontSize: 19, bold: false, color: "#3F5368", alignment: "left" },
  );

  const summaryMainEntry = requireEntry(p7Entries, (entry) => entry.text === "5 / 5 ↑", "P7 5/5 summary");
  setTextBox(
    presentation.resolve(summaryMainEntry.id),
    "5 / 5 ↑",
    { left: 978, top: 198, width: 225, height: 68 },
    { fontSize: 42, bold: true, color: "#153E6A", alignment: "left" },
  );

  const summaryDetailEntry = requireEntry(p7Entries, (entry) => entry.text === "5 次重复训练均提升", "P7 summary details");
  const summaryDetails = presentation.resolve(summaryDetailEntry.id);
  summaryDetails.position = { left: 978, top: 272, width: 238, height: 104 };
  summaryDetails.text.set([
    [
      {
        run: "平均 +1.87 pp",
        textStyle: {
          fontSize: "27px",
          typeface: "Microsoft YaHei",
          color: "#153E6A",
          bold: true,
        },
      },
    ],
    [
      {
        run: "直接测试，结果全部提升",
        textStyle: {
          fontSize: "18px",
          typeface: "Microsoft YaHei",
          color: "#6B7B8D",
          bold: false,
        },
      },
    ],
  ]);
  summaryDetails.text.typeface = "Microsoft YaHei";
  summaryDetails.text.alignment = "left";
  summaryDetails.text.verticalAlignment = "middle";
  summaryDetails.text.wrap = "square";
  summaryDetails.text.autoFit = "shrinkText";
  summaryDetails.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  const gainEntries = p7Entries
    .filter((entry) => entry.kind === "textbox" && /^p5-gain-/.test(entry.name ?? ""))
    .sort((a, b) => String(a.name).localeCompare(String(b.name)));
  if (gainEntries.length !== 5) throw new Error(`Expected five P7 gain labels, found ${gainEntries.length}`);
  gainEntries.forEach((entry, index) => {
    setTextBox(
      presentation.resolve(entry.id),
      gains[index],
      { left: groupCenters[index] - 54, top: 143, width: 108, height: 24 },
      { fontSize: 18, bold: true, color: "#153E6A", alignment: "center" },
    );
  });

  const bottomEntry = requireEntry(p7Entries, (entry) => entry.name === "p5-repeat-explanation", "P7 boundary note");
  setTextBox(
    presentation.resolve(bottomEntry.id),
    "绝对性能仍较低，因此这里把 CNRS 作为独立真实谱来源上的直接迁移证据。",
    { left: 62, top: 652, width: 880, height: 32 },
    { fontSize: 16, bold: false, color: "#6B7B8D", alignment: "center" },
  );

  const oldChartEntry = requireEntry(p7Entries, (entry) => entry.kind === "chart", "P7 inherited chart");
  p7.charts.deleteById(presentation.resolve(oldChartEntry.id).id);

  const chart = p7.charts.add("bar", {
    position: { left: 62, top: 172, width: 880, height: 468 },
    categories,
    series: [
      {
        name: "基线",
        values: baseline,
        fill: "#CDD2D7",
        line: { style: "solid", fill: "#BFC4C9", width: 0.5 },
        dataLabelOverrides: baseline.map((value, idx) => ({
          idx,
          text: value.toFixed(3),
          position: "outEnd",
          showValue: false,
          textStyle: { fontSize: 16, fill: "#69727C", bold: true, alignment: "center" },
          fill: { color: "#FFFFFF", transparency: 100000 },
          line: { style: "solid", fill: "#FFFFFF", width: 0 },
        })),
      },
      {
        name: "一致性训练",
        values: consistency,
        fill: "#0B5EAA",
        line: { style: "solid", fill: "#084B87", width: 0.5 },
        dataLabelOverrides: consistency.map((value, idx) => ({
          idx,
          text: value.toFixed(3),
          position: "outEnd",
          showValue: false,
          textStyle: { fontSize: 16, fill: "#0B5EAA", bold: true, alignment: "center" },
          fill: { color: "#FFFFFF", transparency: 100000 },
          line: { style: "solid", fill: "#FFFFFF", width: 0 },
        })),
      },
    ],
    barOptions: {
      direction: "column",
      grouping: "clustered",
      varyColors: false,
      gapWidth: 65,
      overlap: 0,
    },
    hasLegend: true,
    legend: {
      position: "bottom",
      overlay: false,
      fill: { color: "#FFFFFF", transparency: 100000 },
      line: { style: "solid", fill: "#FFFFFF", width: 0 },
      textStyle: { fontSize: 18, fill: "#536273" },
    },
    xAxis: {
      visible: true,
      position: "bottom",
      tickLabelPosition: "nextTo",
      textStyle: { fontSize: 17, fill: "#4D5D6E" },
      line: { style: "solid", fill: "#AAB4BF", width: 1 },
      majorGridlines: null,
      minorGridlines: null,
    },
    yAxis: {
      visible: true,
      position: "left",
      title: {
        text: "Macro-F1",
        textStyle: { fontSize: 17, fill: "#4D5D6E", bold: false },
      },
      numberFormatCode: "0.0",
      min: 0,
      max: 0.3,
      majorUnit: 0.1,
      tickLabelPosition: "nextTo",
      textStyle: { fontSize: 15, fill: "#718091" },
      line: { style: "solid", fill: "#AAB4BF", width: 1 },
      majorGridlines: { style: "solid", fill: "#EEF1F4", width: 1 },
      minorGridlines: null,
    },
    dataLabels: {
      showValue: false,
      showSeriesName: false,
      showCategoryName: false,
      showPercent: false,
      showLeaderLines: false,
    },
    chartFill: "#FFFFFF",
    chartLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    plotAreaFill: "#FFFFFF",
    plotAreaLine: { style: "solid", fill: "#FFFFFF", width: 0 },
  });
  chart.name = "p7-cnrs-direct-bars";

  p7.speakerNotes.textFrame.setText([
    "本页核心结论：模型不使用任何 CNRS 标注数据再训练，直接在 CNRS-318 独立真实实验谱上测试，5 次重复结果全部提升。",
    "重复 1：0.2067 → 0.2212（+1.45 pp）",
    "重复 2：0.1469 → 0.1756（+2.87 pp）",
    "重复 3：0.1842 → 0.1971（+1.29 pp）",
    "重复 4：0.2149 → 0.2295（+1.46 pp）",
    "重复 5：0.1892 → 0.2120（+2.28 pp）",
    "平均：0.1884 → 0.2071（+1.87 pp）",
    "绝对性能仍较低，因此将该结果解释为独立真实谱来源上的直接迁移证据。",
    "[Sources]",
    "- User-provided CNRS-318 five-repeat Macro-F1 values in the current task.",
  ].join("\n"));

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  await writeBlob(
    path.join(afterDir, "slide-07.png"),
    await presentation.export({ slide: p7, format: "png", scale: 1 }),
  );
  const afterLayout = await p7.export({ format: "layout" });
  const afterLayoutText = await afterLayout.text();
  await fs.writeFile(path.join(afterDir, "slide-07.layout.json"), afterLayoutText, "utf8");
  await fs.writeFile(path.join(finalLayoutDir, "slide-07.layout.json"), afterLayoutText, "utf8");

  for (let index = 0; index < presentation.slides.items.length; index += 1) {
    if (index === 6) continue;
    const layout = await presentation.slides.items[index].export({ format: "layout" });
    await fs.writeFile(
      path.join(finalLayoutDir, `slide-${String(index + 1).padStart(2, "0")}.layout.json`),
      await layout.text(),
      "utf8",
    );
  }

  const afterInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 100000,
  });
  await fs.writeFile(path.join(tempDir, "after-inspect.ndjson"), afterInspect.ndjson, "utf8");
  const p7Lines = parseInspect(afterInspect.ndjson)
    .filter((entry) => entry.slide === 7)
    .map((entry) => JSON.stringify(entry))
    .join("\n");
  await fs.writeFile(path.join(tempDir, "after-p7-inspect.ndjson"), `${p7Lines}\n`, "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
