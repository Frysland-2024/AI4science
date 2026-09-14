import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p2_shift_down_20260901";
const source = `${tmpDir}/source-current.pptx`;
const staged = `${tmpDir}/staged-XRD_导师汇报.pptx`;
const afterDir = `${tmpDir}/after-p2`;
const deltaY = 18;

await fs.mkdir(afterDir, { recursive: true });
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
if (presentation.slides.items.length !== 8) {
  throw new Error(`Unexpected slide count: ${presentation.slides.items.length}`);
}

const slide = presentation.slides.items[1];
const targetIds = [
  "sh/a10jqpsj", // 根据晶体结构 / 计算XRD谱
  "ch/3y5kjydw", // 基准计算谱图
  "sh/r65knqtk", // 基准计算谱
  "sh/nmpcj6ls", // 未加入测量扰动
];

const beforePositions = {};
for (const id of targetIds) {
  const target = presentation.resolve(id);
  if (!target?.position) throw new Error(`Target has no position: ${id}`);
  beforePositions[id] = { ...target.position };
  target.position = {
    ...target.position,
    top: target.position.top + deltaY,
  };
}

const png = await presentation.export({ slide, format: "png", scale: 1 });
await fs.writeFile(`${afterDir}/slide-02.png`, new Uint8Array(await png.arrayBuffer()));
const layout = await slide.export({ format: "layout" });
await fs.writeFile(`${afterDir}/slide-02.layout.json`, await layout.text());

const snapshot = await presentation.inspect({
  kind: "slide,textbox,shape,chart",
  include: "id,slide,name,bbox,textPreview,chartType",
  exclude: "preview,comments",
  maxChars: 30000,
});
await fs.writeFile(`${afterDir}/inspect.ndjson`, snapshot.ndjson);

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(staged);

const afterPositions = {};
for (const id of targetIds) {
  const target = presentation.resolve(id);
  afterPositions[id] = { ...target.position };
  const moved = target.position.top - beforePositions[id].top;
  if (Math.abs(moved - deltaY) > 0.01) {
    throw new Error(`Unexpected vertical movement for ${id}: ${moved}`);
  }
}

await fs.writeFile(
  `${afterDir}/movement-audit.json`,
  JSON.stringify({ slide: 2, deltaY, beforePositions, afterPositions }, null, 2),
);

console.log(JSON.stringify({
  slideCount: presentation.slides.items.length,
  modifiedSlide: 2,
  deltaY,
  targetIds,
  staged,
}, null, 2));
