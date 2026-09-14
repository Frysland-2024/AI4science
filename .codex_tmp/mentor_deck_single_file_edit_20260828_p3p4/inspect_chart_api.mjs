import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const presentation = await PresentationFile.importPptx(await FileBlob.load("E:/AI4science/.codex_tmp/mentor_deck_single_file_edit_20260828_p3p4/source.pptx"));
const chart = presentation.resolve("ch/etsjm14b");
console.log("chart", JSON.stringify(chart.toSnapshot(), null, 2));
console.log("series collection proto", Object.getOwnPropertyNames(Object.getPrototypeOf(chart.series)));
for (const series of chart.series.items) {
  console.log("series proto", Object.getOwnPropertyNames(Object.getPrototypeOf(series)));
  console.log("series snapshot", JSON.stringify(series.toSnapshot?.() ?? {}, null, 2));
  console.log("name", series.name, "line.fill", series.line?.fill, "line.width", series.line?.width, "line.style", series.line?.style, "stroke.fill", series.stroke?.fill);
  console.log("proto", JSON.stringify(series.toProto(), null, 2));
}
