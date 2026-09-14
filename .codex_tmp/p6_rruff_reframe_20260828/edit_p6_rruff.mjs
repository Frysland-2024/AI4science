import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p6_rruff_reframe_20260828");
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const beforeDir = path.join(tempDir, "before-render");
const afterDir = path.join(tempDir, "after-render");
const finalLayoutDir = path.join(tempDir, "final-layout");

const baseline = [0.284718979578149, 0.3026150816434789, 0.35546430676138274];
const consistency = [0.3280396420899909, 0.3486411093591271, 0.40993113162853434];
const categories = ["每类 1 条\n（共 7 条）", "每类 2 条\n（共 14 条）", "每类 5 条\n（共 35 条）"];
const gains = ["+4.33 pp", "+4.60 pp", "+5.45 pp"];
const groupCenters = [322, 676, 1030];

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

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
  if (presentation.slides.items.length !== 6) {
    throw new Error(`Expected 6 slides, found ${presentation.slides.items.length}`);
  }

  const sourceInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 80000,
  });
  await fs.writeFile(path.join(tempDir, "source-inspect.ndjson"), sourceInspect.ndjson, "utf8");
  const entries = parseInspect(sourceInspect.ndjson);
  const p6Entries = entries.filter((entry) => entry.slide === 6);
  const p6SlideEntry = requireEntry(p6Entries, (entry) => entry.kind === "slide", "slide 6");
  const p6 = presentation.resolve(p6SlideEntry.id);

  await writeBlob(
    path.join(beforeDir, "slide-06.png"),
    await presentation.export({ slide: p6, format: "png", scale: 1 }),
  );
  const beforeLayout = await p6.export({ format: "layout" });
  await fs.writeFile(path.join(beforeDir, "slide-06.layout.json"), await beforeLayout.text(), "utf8");

  const title = presentation.resolve(requireEntry(p6Entries, (entry) => entry.id === "sh/u1kbu1ov", "P6 title").id);
  setTextBox(
    title,
    "RRUFF-301 真实谱少样本适配：仅 7 条标注谱也能提升 +4.33 pp",
    { left: 58, top: 28, width: 1096, height: 62 },
    { fontSize: 34, bold: true, color: "#153E6A", alignment: "left" },
  );
  title.text.wrap = "none";

  const context = presentation.resolve(requireEntry(p6Entries, (entry) => entry.id === "sh/47mt0b6x", "P6 dataset context").id);
  context.position = { left: 64, top: 108, width: 1158, height: 32 };
  context.text.set([
    [
      {
        run: "真实谱数据集：RRUFF-301，共 301 条实验 PXRD 谱",
        textStyle: {
          bold: true,
          color: "#234B73",
          fontSize: "19px",
          typeface: "Microsoft YaHei",
        },
      },
      {
        run: "；7 个晶系中每类取 1 / 2 / 5 条作为标注谱",
        textStyle: {
          bold: false,
          color: "#3F5368",
          fontSize: "19px",
          typeface: "Microsoft YaHei",
        },
      },
    ],
  ]);
  context.text.fontSize = 19;
  context.text.typeface = "Microsoft YaHei";
  context.text.color = "#3F5368";
  context.text.alignment = "left";
  context.text.verticalAlignment = "middle";
  context.text.wrap = "none";
  context.text.autoFit = "shrinkText";
  context.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  for (const id of ["sh/87ipkzal", "sh/98rqt4r6", "sh/ml07i9sv"]) {
    presentation.resolve(requireEntry(p6Entries, (entry) => entry.id === id, `P6 removable summary ${id}`).id).delete();
  }

  const firstBudget = presentation.resolve(requireEntry(p6Entries, (entry) => entry.id === "sh/5svutgni", "P6 inherited summary caption").id);
  setTextBox(
    firstBudget,
    "仅 7 条真实标注谱",
    { left: groupCenters[0] - 132, top: 142, width: 264, height: 24 },
    { fontSize: 18, bold: true, color: "#153E6A", alignment: "center" },
  );

  const gainIds = ["sh/j6dcr65c", "sh/i54bylor", "sh/twfux0ne"];
  gainIds.forEach((id, index) => {
    const gain = presentation.resolve(requireEntry(p6Entries, (entry) => entry.id === id, `P6 gain ${index + 1}`).id);
    setTextBox(
      gain,
      gains[index],
      { left: groupCenters[index] - 80, top: 168, width: 160, height: 25 },
      { fontSize: 20, bold: true, color: "#153E6A", alignment: "center" },
    );
  });

  const oldChartEntry = requireEntry(p6Entries, (entry) => entry.id === "ch/8va107ql", "P6 chart");
  p6.charts.deleteById(presentation.resolve(oldChartEntry.id).id);

  const chart = p6.charts.add("bar", {
    position: { left: 58, top: 196, width: 1166, height: 456 },
    categories,
    series: [
      {
        name: "基线",
        values: baseline,
        fill: "#B9C0C7",
        line: { style: "solid", fill: "#9FA8B2", width: 0.6 },
        dataLabelOverrides: baseline.map((value, idx) => ({
          idx,
          text: value.toFixed(3),
          position: "outEnd",
          showValue: false,
          textStyle: { fontSize: 18, fill: "#4F5B66", bold: true, alignment: "center" },
          fill: { color: "#FFFFFF", transparency: 100000 },
          line: { style: "solid", fill: "#FFFFFF", width: 0 },
        })),
      },
      {
        name: "一致性训练",
        values: consistency,
        fill: "#0B5EAA",
        line: { style: "solid", fill: "#084B87", width: 0.6 },
        dataLabelOverrides: consistency.map((value, idx) => ({
          idx,
          text: value.toFixed(3),
          position: "outEnd",
          showValue: false,
          textStyle: { fontSize: 18, fill: "#07579D", bold: true, alignment: "center" },
          fill: { color: "#FFFFFF", transparency: 100000 },
          line: { style: "solid", fill: "#FFFFFF", width: 0 },
        })),
      },
    ],
    barOptions: {
      direction: "column",
      grouping: "clustered",
      varyColors: false,
      gapWidth: 90,
      overlap: 0,
    },
    hasLegend: true,
    legend: {
      position: "bottom",
      overlay: false,
      fill: { color: "#FFFFFF", transparency: 100000 },
      line: { style: "solid", fill: "#FFFFFF", width: 0 },
      textStyle: { fontSize: 20, fill: "#34495E" },
    },
    xAxis: {
      visible: true,
      position: "bottom",
      tickLabelPosition: "nextTo",
      textStyle: { fontSize: 19, fill: "#34495E" },
      line: { style: "solid", fill: "#9EABB8", width: 1 },
      majorGridlines: null,
      minorGridlines: null,
    },
    yAxis: {
      visible: true,
      position: "left",
      title: {
        text: "Macro-F1",
        textStyle: { fontSize: 19, fill: "#34495E", bold: false },
      },
      numberFormatCode: "0.0",
      min: 0,
      max: 0.5,
      majorUnit: 0.1,
      tickLabelPosition: "nextTo",
      textStyle: { fontSize: 17, fill: "#536779" },
      line: { style: "solid", fill: "#9EABB8", width: 1 },
      majorGridlines: { style: "solid", fill: "#E9EEF2", width: 1 },
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
  chart.name = "p6-rruff-fewshot-bars";

  p6.speakerNotes.textFrame.setText([
    "本页核心结论：RRUFF-301 真实谱少样本适配中，每类仅 1 条标注谱（共 7 条）仍提升 +4.33 pp。",
    "RRUFF-301 包含 301 个唯一 RRUFF 实测样本，每个样本对应一条规范化 PXRD 谱；301 不代表 301 种不同矿物。",
    "数据覆盖 7 个晶系，每类 43 条：10 条进入 adaptation pool，33 条进入 locked test。",
    "K=1/2/5 是 labels per class；每个 episode 的支持集因此共有 7/14/35 条真实标注谱。",
    "图中数值为 5 个 pretraining seeds × 5 个 episode seeds 共 25 组配对运行的平均 Macro-F1。",
    "K=1: 0.2847 → 0.3280 (+4.33 pp)",
    "K=2: 0.3026 → 0.3486 (+4.60 pp)",
    "K=5: 0.3555 → 0.4099 (+5.45 pp)",
    "该证据为 retrospectively verified locked-test few-shot 结果，不表述为 provenance-complete prospective confirmatory run。",
    "[Sources]",
    "- E:/AI4science/xrd_robustness/reports/rruff301_fewshot_results.json",
    "- E:/AI4science/xrd_robustness/data/real_xrd/rruff371/contracts/dataset_contract.json",
    "- E:/AI4science/xrd_robustness/data/real_xrd/rruff371/splits/rruff301_manifest.json",
    "- E:/AI4science/xrd_robustness/data/real_xrd/rruff371/manifests/rruff371_master_manifest.csv",
  ].join("\n"));

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  await writeBlob(
    path.join(afterDir, "slide-06.png"),
    await presentation.export({ slide: p6, format: "png", scale: 1 }),
  );
  const layout = await p6.export({ format: "layout" });
  const layoutText = await layout.text();
  await fs.writeFile(path.join(afterDir, "slide-06.layout.json"), layoutText, "utf8");
  await fs.writeFile(path.join(finalLayoutDir, "slide-06.layout.json"), layoutText, "utf8");

  const finalInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 80000,
  });
  const p6Lines = parseInspect(finalInspect.ndjson)
    .filter((entry) => entry.slide === 6)
    .map((entry) => JSON.stringify(entry))
    .join("\n");
  await fs.writeFile(path.join(tempDir, "final-p6-inspect.ndjson"), `${p6Lines}\n`, "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
