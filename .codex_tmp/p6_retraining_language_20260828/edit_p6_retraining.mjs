import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p6_retraining_language_20260828");
const starterPath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "after-render");
const layoutDir = path.join(tempDir, "final-layout");

const oldTitle = "RRUFF-301 真实谱少样本适配：仅用 7 条真实谱适配，也能提升 +4.33 pp";
const oldSubtitle = "RRUFF-301：301 条真实实验 PXRD 谱｜每类仅用 1 / 2 / 5 条进行少样本适配";
const newTitle = "RRUFF-301 真实谱验证：仅用 7 条真实谱再训练，也能提升 +4.33 pp";
const newSubtitle = "先用模拟谱训练模型，再分别用每类 1 / 2 / 5 条真实谱进行少量再训练";

const expectedBaseline = [0.284718979578149, 0.3026150816434789, 0.35546430676138274];
const expectedMethod = [0.3280396420899909, 0.3486411093591271, 0.40993113162853434];

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

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  await fs.mkdir(layoutDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(starterPath));
  if (presentation.slides.items.length !== 6) {
    throw new Error(`Expected 6 slides, found ${presentation.slides.items.length}`);
  }

  const inspected = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 80000,
  });
  const entries = parseInspect(inspected.ndjson);
  const p6Entries = entries.filter((entry) => entry.slide === 6);

  const titleEntry = requireEntry(p6Entries, (entry) => entry.id === "sh/u1kbu1ov", "P6 title");
  const subtitleEntry = requireEntry(p6Entries, (entry) => entry.id === "sh/47mt0b6x", "P6 subtitle");
  if (titleEntry.text !== oldTitle) throw new Error(`Unexpected P6 title: ${titleEntry.text}`);
  if (subtitleEntry.text !== oldSubtitle) throw new Error(`Unexpected P6 subtitle: ${subtitleEntry.text}`);

  const chartEntry = requireEntry(p6Entries, (entry) => entry.id === "ch/8va107ql", "P6 chart");
  const chart = presentation.resolve(chartEntry.id);
  if (!sameValues(chart.series.getItemAt(0).values, expectedBaseline)) throw new Error("P6 baseline data changed before edit");
  if (!sameValues(chart.series.getItemAt(1).values, expectedMethod)) throw new Error("P6 method data changed before edit");

  const title = presentation.resolve(titleEntry.id);
  title.text = newTitle;
  title.text.wrap = "none";
  title.text.autoFit = "shrinkText";

  const subtitle = presentation.resolve(subtitleEntry.id);
  subtitle.text.set([
    [
      {
        run: "先用模拟谱训练模型",
        textStyle: {
          bold: true,
          color: "#234B73",
          fontSize: "19px",
          typeface: "Microsoft YaHei",
        },
      },
      {
        run: "，再分别用每类 1 / 2 / 5 条真实谱进行少量再训练",
        textStyle: {
          bold: false,
          color: "#3F5368",
          fontSize: "19px",
          typeface: "Microsoft YaHei",
        },
      },
    ],
  ]);
  subtitle.text.alignment = "left";
  subtitle.text.verticalAlignment = "middle";
  subtitle.text.wrap = "none";
  subtitle.text.autoFit = "shrinkText";
  subtitle.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  const slide6 = presentation.slides.items[5];
  await writeBlob(
    path.join(renderDir, "slide-06.png"),
    await presentation.export({ slide: slide6, format: "png", scale: 1 }),
  );
  const layout = await slide6.export({ format: "layout" });
  const layoutText = await layout.text();
  await fs.writeFile(path.join(renderDir, "slide-06.layout.json"), layoutText, "utf8");
  await fs.writeFile(path.join(layoutDir, "slide-06.layout.json"), layoutText, "utf8");

  const finalInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 80000,
  });
  const p6Lines = parseInspect(finalInspect.ndjson)
    .filter((entry) => entry.slide === 6)
    .map((entry) => JSON.stringify(entry))
    .join("\n");
  await fs.writeFile(path.join(tempDir, "final-p6-inspect.ndjson"), `${p6Lines}\n`, "utf8");

  console.log(JSON.stringify({ outputPath, newTitle, newSubtitle }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
