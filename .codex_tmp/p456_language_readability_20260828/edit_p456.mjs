import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p456_language_readability_20260828");
const starterPath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "after-render");
const layoutDir = path.join(tempDir, "final-layout");

const p5Baseline = [0.6390, 0.6553, 0.6577, 0.6517, 0.6500];
const p5Method = [0.6939, 0.7167, 0.7075, 0.6967, 0.7118];
const p6Baseline = [0.284718979578149, 0.3026150816434789, 0.35546430676138274];
const p6Method = [0.3280396420899909, 0.3486411093591271, 0.40993113162853434];

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function requireEntry(entries, predicate, label) {
  const entry = entries.find(predicate);
  if (!entry) throw new Error(`Could not locate ${label}`);
  return entry;
}

function sameValues(actual, expected) {
  return Array.isArray(actual)
    && actual.length === expected.length
    && actual.every((value, index) => Math.abs(Number(value) - expected[index]) < 1e-9);
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function setBaseTextFrame(shape, { alignment = "left", verticalAlignment = "top", wrap = "square", autoFit = "none" } = {}) {
  shape.text.alignment = alignment;
  shape.text.verticalAlignment = verticalAlignment;
  shape.text.wrap = wrap;
  shape.text.autoFit = autoFit;
  shape.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  await fs.mkdir(layoutDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(starterPath));
  if (presentation.slides.items.length !== 6) {
    throw new Error(`Expected 6 slides, found ${presentation.slides.items.length}`);
  }

  const sourceInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 80000,
  });
  const entries = parseInspect(sourceInspect.ndjson);

  // Slide 4: make the existing experiment-configuration frame easier to read.
  const p4Entries = entries.filter((entry) => entry.slide === 4);
  const p4 = presentation.slides.items[3];

  const materials = presentation.resolve(requireEntry(
    p4Entries,
    (entry) => entry.id === "sh/x8vaxsfe" && entry.text === "Materials Project 晶体结构",
    "P4 Materials Project label",
  ).id);
  materials.text = "来自 Materials Project 的晶体结构";
  materials.position = { left: 72, top: 242, width: 420, height: 34 };
  materials.text.fontSize = 22;
  materials.text.typeface = "Microsoft YaHei";
  materials.text.color = "#27384A";
  setBaseTextFrame(materials, { alignment: "left", verticalAlignment: "middle", wrap: "none", autoFit: "shrinkText" });

  const lowerLeft = presentation.resolve(requireEntry(
    p4Entries,
    (entry) => entry.id === "sh/g36tgryd" && (entry.text ?? "").startsWith("按晶体结构划分"),
    "P4 lower-left explanation",
  ).id);
  lowerLeft.position = { left: 72, top: 446, width: 420, height: 190 };
  lowerLeft.text.set([
    [
      {
        run: "按晶体结构划分",
        textStyle: { bold: true, color: "#153E6A", fontSize: "23px", typeface: "Microsoft YaHei" },
      },
    ],
    [
      {
        run: "同一晶体的不同谱始终留在同一数据集",
        textStyle: { bold: false, color: "#657384", fontSize: "19px", typeface: "Microsoft YaHei" },
      },
    ],
    [{ run: "", textStyle: { fontSize: "10px", typeface: "Microsoft YaHei" } }],
    [
      {
        run: "训练时实时生成谱",
        textStyle: { bold: true, color: "#153E6A", fontSize: "23px", typeface: "Microsoft YaHei" },
      },
    ],
    [
      {
        run: "同一晶体 → ",
        textStyle: { bold: false, color: "#657384", fontSize: "19px", typeface: "Microsoft YaHei" },
      },
      {
        run: "随机“换测量条件”",
        textStyle: { bold: true, color: "#E07A2A", fontSize: "19px", typeface: "Microsoft YaHei" },
      },
      {
        run: " → 不同训练谱",
        textStyle: { bold: false, color: "#657384", fontSize: "19px", typeface: "Microsoft YaHei" },
      },
    ],
  ]);
  setBaseTextFrame(lowerLeft, { alignment: "left", verticalAlignment: "top", wrap: "square", autoFit: "none" });

  presentation.resolve(requireEntry(
    p4Entries,
    (entry) => entry.id === "sh/oz29krqh" && entry.text === "5 类扰动及其对谱图的影响",
    "P4 redundant table heading",
  ).id).delete();

  const disturbanceTable = presentation.resolve(requireEntry(
    p4Entries,
    (entry) => entry.id === "tb/8jqxsf29" && entry.preview === "扰动类型 | 对谱图的影响",
    "P4 disturbance table",
  ).id);
  disturbanceTable.position = { left: 545, top: 142, width: 655, height: 470 };
  disturbanceTable.rows[0].height = 50;
  for (let row = 1; row < 6; row += 1) disturbanceTable.rows[row].height = 84;
  for (let row = 0; row < 6; row += 1) {
    for (let column = 0; column < 2; column += 1) {
      const cell = disturbanceTable.getCell(row, column);
      cell.text.style = {
        fontSize: row === 0 ? 19 : 20,
        bold: row === 0 || column === 0,
        color: row === 0 || column === 0 ? "#153E6A" : "#66788A",
        typeface: "Microsoft YaHei",
        alignment: "left",
        verticalAlignment: "middle",
        wrap: "square",
        autoFit: "none",
        insets: { top: 6, right: 14, bottom: 6, left: 14 },
      };
    }
  }

  // Slide 5: translate seed terminology into audience-facing repeated-training language.
  const p5Entries = entries.filter((entry) => entry.slide === 5);
  const p5 = presentation.slides.items[4];
  const p5Title = presentation.resolve(requireEntry(p5Entries, (entry) => entry.id === "sh/v2twb6dw", "P5 title").id);
  p5Title.text = "5 次重复训练全部提升，平均 Macro-F1 +5.46 个百分点";
  p5Title.text.wrap = "none";
  p5Title.text.autoFit = "shrinkText";

  const p5Summary = presentation.resolve(requireEntry(p5Entries, (entry) => entry.id === "sh/yhkbe1o7", "P5 summary sentence").id);
  p5Summary.text = "5 次重复训练均提升";
  p5Summary.text.wrap = "none";
  p5Summary.text.autoFit = "shrinkText";

  const p5Chart = presentation.resolve(requireEntry(p5Entries, (entry) => entry.id === "ch/lwvi1grm", "P5 chart").id);
  if (!sameValues(p5Chart.series.getItemAt(0).values, p5Baseline)) throw new Error("P5 baseline values changed");
  if (!sameValues(p5Chart.series.getItemAt(1).values, p5Method)) throw new Error("P5 consistency values changed");
  const repeatedTrainingCategories = ["重复 1", "重复 2", "重复 3", "重复 4", "重复 5"];
  p5Chart.categories = repeatedTrainingCategories;
  p5Chart.series.getItemAt(0).categories = repeatedTrainingCategories;
  p5Chart.series.getItemAt(1).categories = repeatedTrainingCategories;

  const repeatNote = p5.shapes.add({
    geometry: "textbox",
    position: { left: 62, top: 652, width: 880, height: 32 },
    fill: "none",
    line: { style: "solid", fill: "#FFFFFF", width: 0 },
  });
  repeatNote.name = "p5-repeat-explanation";
  repeatNote.text = "重复训练 5 次：数据、模型和训练设置相同，每次只改变随机初始化等随机因素。";
  repeatNote.text.style = {
    typeface: "Microsoft YaHei",
    fontSize: 16,
    bold: false,
    color: "#657384",
    alignment: "center",
    verticalAlignment: "middle",
    wrap: "none",
    autoFit: "shrinkText",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };

  p5.speakerNotes.textFrame.setText([
    "本页只展示冻结模拟扰动 Test 的 Macro-F1。",
    "重复训练 5 次：数据、模型和训练设置相同，每次只改变随机初始化等随机因素。",
    "5 次重复训练中，一致性训练均优于基线。",
    "重复 1: 0.6390 → 0.6939 (+5.48 pp)",
    "重复 2: 0.6553 → 0.7167 (+6.14 pp)",
    "重复 3: 0.6577 → 0.7075 (+4.99 pp)",
    "重复 4: 0.6517 → 0.6967 (+4.51 pp)",
    "重复 5: 0.6500 → 0.7118 (+6.18 pp)",
    "平均: 0.6507 → 0.7053 (+5.46 pp)",
    "[Sources]",
    "- E:/AI4science/xrd_robustness/reports/simulated_test_results.json",
  ].join("\n"));

  // Slide 6: wording-only refinement; preserve the chart and all geometry.
  const p6Entries = entries.filter((entry) => entry.slide === 6);
  const p6 = presentation.slides.items[5];
  const p6Chart = presentation.resolve(requireEntry(p6Entries, (entry) => entry.id === "ch/8va107ql", "P6 chart").id);
  if (!sameValues(p6Chart.series.getItemAt(0).values, p6Baseline)) throw new Error("P6 baseline values changed");
  if (!sameValues(p6Chart.series.getItemAt(1).values, p6Method)) throw new Error("P6 consistency values changed");

  const p6Title = presentation.resolve(requireEntry(p6Entries, (entry) => entry.id === "sh/u1kbu1ov", "P6 title").id);
  p6Title.text = "RRUFF-301 真实谱少样本适配：仅用 7 条真实谱适配，也能提升 +4.33 pp";
  p6Title.text.wrap = "none";
  p6Title.text.autoFit = "shrinkText";

  const p6Context = presentation.resolve(requireEntry(p6Entries, (entry) => entry.id === "sh/47mt0b6x", "P6 dataset context").id);
  p6Context.text.set([
    [
      {
        run: "RRUFF-301：301 条真实实验 PXRD 谱",
        textStyle: { bold: true, color: "#234B73", fontSize: "19px", typeface: "Microsoft YaHei" },
      },
      {
        run: "｜每类仅用 1 / 2 / 5 条进行少样本适配",
        textStyle: { bold: false, color: "#3F5368", fontSize: "19px", typeface: "Microsoft YaHei" },
      },
    ],
  ]);
  setBaseTextFrame(p6Context, { alignment: "left", verticalAlignment: "middle", wrap: "none", autoFit: "none" });

  const p6FirstBudget = presentation.resolve(requireEntry(p6Entries, (entry) => entry.id === "sh/5svutgni", "P6 first-budget annotation").id);
  p6FirstBudget.text = "仅 7 条真实谱";
  p6FirstBudget.text.wrap = "none";
  p6FirstBudget.text.autoFit = "none";

  const p6NotesEntry = requireEntry(p6Entries, (entry) => entry.kind === "notes", "P6 notes");
  const updatedP6Notes = p6NotesEntry.text.replace(
    /^本页核心结论：.*$/m,
    "本页核心结论：RRUFF-301 真实谱少样本适配中，仅用 7 条真实谱适配仍提升 +4.33 pp。",
  );
  p6.speakerNotes.textFrame.setText(updatedP6Notes);

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  for (const slideNumber of [4, 5, 6]) {
    const slide = presentation.slides.items[slideNumber - 1];
    const stem = `slide-${String(slideNumber).padStart(2, "0")}`;
    await writeBlob(path.join(renderDir, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
    const layout = await slide.export({ format: "layout" });
    const layoutText = await layout.text();
    await fs.writeFile(path.join(renderDir, `${stem}.layout.json`), layoutText, "utf8");
    await fs.writeFile(path.join(layoutDir, `${stem}.layout.json`), layoutText, "utf8");
  }

  const finalInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 80000,
  });
  const finalEntries = parseInspect(finalInspect.ndjson).filter((entry) => [4, 5, 6].includes(entry.slide));
  await fs.writeFile(
    path.join(tempDir, "final-p456-inspect.ndjson"),
    `${finalEntries.map((entry) => JSON.stringify(entry)).join("\n")}\n`,
    "utf8",
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
