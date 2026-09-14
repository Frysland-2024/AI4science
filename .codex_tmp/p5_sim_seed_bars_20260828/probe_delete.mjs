import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const p = await PresentationFile.importPptx(await FileBlob.load("E:/AI4science/.codex_tmp/p5_sim_seed_bars_20260828/template-starter.pptx"));
const inspect = await p.inspect({ kind: "chart,shape,textbox", maxChars: 30000 });
const entries = inspect.ndjson.split(/\r?\n/).filter(Boolean).map(JSON.parse).filter((e) => e.slide === 5);
const chartEntry = entries.find((e) => e.kind === "chart");
const shapeEntry = entries.find((e) => e.kind === "shape" && e.bbox?.[1] > 150);
const chart = p.resolve(chartEntry.id);
const shape = p.resolve(shapeEntry.id);
const slide = p.slides.items[4];

function methods(value) {
  const names = new Set();
  let cursor = value;
  while (cursor && cursor !== Object.prototype) {
    for (const name of Object.getOwnPropertyNames(cursor)) names.add(name);
    cursor = Object.getPrototypeOf(cursor);
  }
  return [...names].sort();
}

console.log(JSON.stringify({
  chartEntry,
  shapeEntry,
  chartKeys: Object.keys(chart),
  chartMethods: methods(chart),
  shapeKeys: Object.keys(shape),
  shapeMethods: methods(shape),
  chartCollectionKeys: Object.keys(slide.charts),
  chartCollectionMethods: methods(slide.charts),
  chartItemCount: slide.charts.items.length,
  chartItems: slide.charts.items.map((item) => ({ id: item.id, name: item.name, keys: Object.keys(item), methods: methods(item) })),
}, null, 2));
