import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const source = "E:/AI4science/.codex_tmp/p4_text_only_edit_20260828/source.pptx";
const ids = [
  "sh/p0batw72",
  "sh/oz29krqh",
  "sh/1wbapc7q",
  "sh/et0reh8f",
  "sh/ilwf69kv",
  "sh/5ony1oj6",
];

const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
for (const id of ids) {
  const shape = presentation.resolve(id);
  console.log(JSON.stringify({
    id,
    position: shape.position,
    text: String(shape.text),
    style: shape.text.style,
    fontSize: shape.text.fontSize,
    color: shape.text.color,
    bold: shape.text.bold,
    alignment: shape.text.alignment,
    verticalAlignment: shape.text.verticalAlignment,
    insets: shape.text.insets,
  }));
}
