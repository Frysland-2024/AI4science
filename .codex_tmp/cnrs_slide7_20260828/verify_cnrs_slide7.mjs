import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const pptxPath = "E:/AI4science/.codex_tmp/cnrs_slide7_20260828/staged-XRD_导师汇报.pptx";
const expectedBaseline = [0.2067, 0.1469, 0.1842, 0.2149, 0.1892];
const expectedMethod = [0.2212, 0.1756, 0.1971, 0.2295, 0.2120];
const expectedGains = ["+1.45 pp", "+2.87 pp", "+1.29 pp", "+1.46 pp", "+2.28 pp"];

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function sameValues(actual, expected) {
  return Array.isArray(actual)
    && actual.length === expected.length
    && actual.every((value, index) => Math.abs(Number(value) - expected[index]) < 1e-9);
}

async function main() {
  const presentation = await PresentationFile.importPptx(await FileBlob.load(pptxPath));
  assert(presentation.slides.items.length === 7, "Deck must contain exactly 7 slides");

  const snapshot = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes",
    maxChars: 100000,
  });
  const p7Entries = parseInspect(snapshot.ndjson).filter((entry) => entry.slide === 7);
  const visibleTexts = new Set(p7Entries.filter((entry) => entry.kind === "textbox").map((entry) => entry.text));

  const requiredTexts = [
    "完全不用 CNRS 标注数据再训练，5 次重复结果仍全部提升",
    "CNRS-318｜独立真实实验谱来源｜不使用 CNRS 标注数据再训练，直接测试",
    "07 / 07",
    "5 / 5 ↑",
    "平均 +1.87 pp\n直接测试，结果全部提升",
    "绝对性能仍较低，因此这里把 CNRS 作为独立真实谱来源上的直接迁移证据。",
    ...expectedGains,
  ];
  for (const text of requiredTexts) assert(visibleTexts.has(text), `Missing exact P7 text: ${text}`);

  const chartEntry = p7Entries.find((entry) => entry.kind === "chart" && entry.name === "p7-cnrs-direct-bars");
  assert(chartEntry, "CNRS chart not found");
  const chart = presentation.resolve(chartEntry.id);
  assert(chart.series.items.length === 2, "CNRS chart must have two series");
  assert(chart.series.getItemAt(0).name === "基线", "Baseline series label mismatch");
  assert(chart.series.getItemAt(1).name === "一致性训练", "Consistency series label mismatch");
  assert(sameValues(chart.series.getItemAt(0).values, expectedBaseline), "Baseline values mismatch");
  assert(sameValues(chart.series.getItemAt(1).values, expectedMethod), "Consistency values mismatch");

  const noteEntry = p7Entries.find((entry) => entry.kind === "notes");
  assert(noteEntry?.text?.includes("不使用任何 CNRS 标注数据再训练"), "CNRS condition missing from notes");
  assert(noteEntry?.text?.includes("[Sources]"), "Sources block missing from notes");

  console.log(JSON.stringify({
    status: "pass",
    slideCount: presentation.slides.items.length,
    chartSeries: [chart.series.getItemAt(0).values, chart.series.getItemAt(1).values],
    gains: expectedGains,
  }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
