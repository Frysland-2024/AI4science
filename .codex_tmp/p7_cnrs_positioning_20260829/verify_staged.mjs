import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const stagedPath = "E:/AI4science/.codex_tmp/p7_cnrs_positioning_20260829/staged-XRD_导师汇报.pptx";
const baselineExpected = [0.2067, 0.1469, 0.1842, 0.2149, 0.1892];
const methodExpected = [0.2212, 0.1756, 0.1971, 0.2295, 0.2120];

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
  const inspect = await presentation.inspect({ kind: "slide,textbox,chart", maxChars: 40000 });
  const p7 = parseInspect(inspect.ndjson).filter((entry) => entry.slide === 7);
  const title = p7.find((entry) => entry.id === "sh/cbq1sv25");
  const subtitle = p7.find((entry) => entry.id === "sh/kzmdova1");
  const summary = p7.find((entry) => entry.id === "sh/zedcfa9g");
  const bottom = p7.find((entry) => entry.id === "sh/jedkn654");
  const chartEntry = p7.find((entry) => entry.id === "ch/szmd4zyp");
  if (!title || !subtitle || !summary || !bottom || !chartEntry) throw new Error("Missing staged slide 7 elements");
  const chart = presentation.resolve(chartEntry.id);
  const checks = {
    title: title.text === "换到另一套真实实验谱直接测试，5 次重复结果仍全部提升" && title.textLines === 1,
    subtitle: subtitle.text === "CNRS-318：独立真实实验谱｜不使用 CNRS 数据调整模型，直接测试" && subtitle.textLines === 1,
    summary: summary.text === "5 次重复全部提升\n\n平均 +1.87 pp",
    bottom: bottom.text === "不使用 CNRS 数据调整模型，直接测试仍有增益。" && bottom.textLines === 1,
    baselineValues: sameValues(chart.series.getItemAt(0).values, baselineExpected),
    methodValues: sameValues(chart.series.getItemAt(1).values, methodExpected),
  };
  if (Object.values(checks).some((value) => !value)) throw new Error(`Round-trip check failed: ${JSON.stringify(checks)}`);
  console.log(JSON.stringify({ status: "pass", checks }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
