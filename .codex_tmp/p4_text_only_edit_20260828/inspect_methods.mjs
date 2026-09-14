import { FileBlob, PresentationFile } from "@oai/artifact-tool";
const presentation = await PresentationFile.importPptx(await FileBlob.load("E:/AI4science/.codex_tmp/p4_text_only_edit_20260828/template-starter.pptx"));
for (const id of ["ch/etsjm14b", "sh/2xkrih8b"]) {
  const target = presentation.resolve(id);
  const methods = new Set();
  let proto = target;
  while (proto && proto !== Object.prototype) {
    for (const name of Object.getOwnPropertyNames(proto)) methods.add(name);
    proto = Object.getPrototypeOf(proto);
  }
  console.log(id, [...methods].sort().join(","));
}
const slide = presentation.resolve("sl/jyx0ra1s");
for (const [name, target] of [["charts", slide.charts], ["shapes", slide.shapes]]) {
  const methods = new Set();
  let proto = target;
  while (proto && proto !== Object.prototype) {
    for (const key of Object.getOwnPropertyNames(proto)) methods.add(key);
    proto = Object.getPrototypeOf(proto);
  }
  console.log(name, [...methods].sort().join(","));
}
