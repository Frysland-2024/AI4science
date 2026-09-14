import { FileBlob, PresentationFile } from "@oai/artifact-tool";
const presentation = await PresentationFile.importPptx(await FileBlob.load("E:/AI4science/outputs/XRD_导师汇报.pptx"));
const snapshot = await presentation.inspect({ kind: "chart", maxChars: 10000 });
const line = snapshot.ndjson.split(/\r?\n/).filter(Boolean).map(JSON.parse).find((entry) => entry.slide === 5);
const chart = presentation.resolve(line.id);
console.log(JSON.stringify({
  chartCategories: chart.categories,
  series0Categories: chart.series.getItemAt(0).categories,
  series1Categories: chart.series.getItemAt(1).categories,
  chartData: chart.data,
  series0Data: chart.series.getItemAt(0).data,
}, null, 2));
