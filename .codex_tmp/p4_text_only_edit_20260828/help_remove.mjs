import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const source = "E:/AI4science/.codex_tmp/p4_text_only_edit_20260828/template-starter.pptx";
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
for (const query of ["chart.delete", "chart remove", "shape.delete", "delete chart"]) {
  const result = presentation.help("*", {
    search: query,
    include: ["index", "notes", "examples"],
    maxChars: 5000,
  });
  console.log(`QUERY ${query}\n${result.ndjson ?? result}`);
}
