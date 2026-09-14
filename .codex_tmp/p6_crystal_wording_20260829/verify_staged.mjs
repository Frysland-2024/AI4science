import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const stagedPath = "E:/AI4science/.codex_tmp/p6_crystal_wording_20260829/staged-XRD_导师汇报.pptx";
const expectedCategories = [
  "每个晶系 1 条\n（共 7 条）",
  "每个晶系 2 条\n（共 14 条）",
  "每个晶系 5 条\n（共 35 条）",
];
const baselineExpected = [0.284718979578149, 0.3026150816434789, 0.35546430676138274];
const methodExpected = [0.3280396420899909, 0.3486411093591271, 0.40993113162853434];

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function sameValues(actual, expected) {
  return Array.isArray(actual)
    && actual.length === expected.length
    && actual.every((value, index) => Math.abs(Number(value) - expected[index]) < 1e-9);
}

async function main() {
  const presentation = await PresentationFile.importPptx(await FileBlob.load(stagedPath));
  const inspect = await presentation.inspect({
    kind: "slide,textbox,chart",
    maxChars: 40000,
  });
  const p6 = parseInspect(inspect.ndjson).filter((entry) => entry.slide === 6);
  const chartEntry = p6.find((entry) => entry.name === "p6-rruff-fewshot-bars");
  const subtitle = p6.find((entry) => entry.name === "p6-dataset-context");
  const summary = p6.find((entry) => entry.name === "p6-summary-caption");
  if (!chartEntry || !subtitle || !summary) throw new Error("Missing staged slide 6 elements");
  const chart = presentation.resolve(chartEntry.id);

  const checks = {
    series0Categories: JSON.stringify(chart.series.getItemAt(0).categories) === JSON.stringify(expectedCategories),
    series1Categories: JSON.stringify(chart.series.getItemAt(1).categories) === JSON.stringify(expectedCategories),
    baselineValues: sameValues(chart.series.getItemAt(0).values, baselineExpected),
    methodValues: sameValues(chart.series.getItemAt(1).values, methodExpected),
    subtitle: subtitle.text === "RRUFF-301：301 条真实实验 PXRD 谱｜每个晶系各取 1 / 2 / 5 条真实谱进行少量再训练",
    summarySubject1: summary.text.includes("本方法 14 条 ≈ 基线 35 条"),
    summarySubject2: summary.text.includes("本方法 7 条 > 基线 14 条"),
  };
  if (Object.values(checks).some((value) => !value)) {
    throw new Error(`Round-trip check failed: ${JSON.stringify(checks)}`);
  }
  console.log(JSON.stringify({ status: "pass", checks }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
