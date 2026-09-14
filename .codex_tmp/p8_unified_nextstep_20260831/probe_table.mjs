import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const presentation = await PresentationFile.importPptx(
  await FileBlob.load("E:/AI4science/.codex_tmp/p8_unified_nextstep_20260831/source.pptx"),
);
const table = presentation.resolve("tb/mhovq5k3");
const cell = table.getCell(0, 0);
const slide = presentation.slides.items[3];
console.log(JSON.stringify({
  keys: Object.keys(table),
  prototypeKeys: Object.getOwnPropertyNames(Object.getPrototypeOf(table)),
  rowKeys: Object.keys(table.rows ?? {}),
  row0Keys: Object.keys(table.rows?.[0] ?? {}),
  colKeys: Object.keys(table.columns ?? {}),
  col0Keys: Object.keys(table.columns?.[0] ?? {}),
  position: table.position,
  tableCollectionKeys: Object.keys(slide.tables ?? {}),
  tableCollectionPrototypeKeys: Object.getOwnPropertyNames(Object.getPrototypeOf(slide.tables)),
  cellKeys: Object.keys(cell),
  cellPrototypeKeys: Object.getOwnPropertyNames(Object.getPrototypeOf(cell)),
  cellBorderKeys: Object.keys(cell.borders ?? {}),
  cellBorders: cell.borders,
  cellBorderTopKeys: Object.keys(cell.borders?.top ?? {}),
  cellBorderTopPrototypeKeys: cell.borders?.top ? Object.getOwnPropertyNames(Object.getPrototypeOf(cell.borders.top)) : [],
  cellBorderTopConfig: cell.borders?.top?.toConfig?.(),
  cellBorderPrototypeKeys: cell.borders ? Object.getOwnPropertyNames(Object.getPrototypeOf(cell.borders)) : [],
}, null, 2));
const help = presentation.help("*", { search: "table column width row height cell border fill", include: ["index", "notes"], maxChars: 12000 });
console.log(help);
