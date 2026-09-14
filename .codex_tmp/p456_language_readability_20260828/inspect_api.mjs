import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const presentation = await PresentationFile.importPptx(await FileBlob.load("E:/AI4science/.codex_tmp/p456_language_readability_20260828/source.pptx"));
const table = presentation.resolve("tb/8jqxsf29");
const chart = presentation.resolve("ch/lwvi1grm");
for (const [label, object] of [["table", table], ["chart", chart], ["tables", presentation.slides.items[3].tables]]) {
  const names = new Set();
  let current = object;
  for (let i = 0; current && i < 6; i += 1, current = Object.getPrototypeOf(current)) {
    for (const name of Object.getOwnPropertyNames(current)) names.add(name);
  }
  console.log(label, [...names].sort().join(","));
}
