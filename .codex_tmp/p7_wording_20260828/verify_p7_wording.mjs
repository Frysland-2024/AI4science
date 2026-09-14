import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const filePath = "E:/AI4science/.codex_tmp/p7_wording_20260828/staged-XRD_导师汇报.pptx";
const expectedSummary = "平均 +1.87 pp\n在相同数据和训练设置下\n重复训练 5 次，结果都更好。";
const expectedBottom = "在另一套真实实验谱上直接测试，我的方法仍然表现出稳定增益。";

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(filePath));
const snapshot = await presentation.inspect({
  kind: "slide,textbox,shape,chart,notes,layout",
  maxChars: 100000,
});
const p7 = parseInspect(snapshot.ndjson).filter((entry) => entry.slide === 7);
const summary = p7.find((entry) => entry.text === expectedSummary);
const bottom = p7.find((entry) => entry.text === expectedBottom);
if (!summary || !bottom) {
  throw new Error(`Round-trip wording check failed: ${JSON.stringify({ summary, bottom })}`);
}
console.log(JSON.stringify({
  summary: { id: summary.id, text: summary.text, textLines: summary.textLines, bbox: summary.bbox },
  bottom: { id: bottom.id, text: bottom.text, textLines: bottom.textLines, bbox: bottom.bbox },
}, null, 2));
