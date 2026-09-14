import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const source = "E:/AI4science/.codex_tmp/scientific_evidence_deck_20260828/round7_add_p4_setup/template-starter.pptx";
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const slide = presentation.slides.items[1];
const chart = slide.charts.items[0];
console.log("chart proto", Object.getOwnPropertyNames(Object.getPrototypeOf(chart)));
console.log("charts proto", Object.getOwnPropertyNames(Object.getPrototypeOf(slide.charts)));
console.log("shape proto", Object.getOwnPropertyNames(Object.getPrototypeOf(slide.shapes.items[0])));
console.log("shapes proto", Object.getOwnPropertyNames(Object.getPrototypeOf(slide.shapes)));
