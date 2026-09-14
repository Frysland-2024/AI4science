import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tempDir = "E:/AI4science/.codex_tmp/p5_wording_20260828";
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(tempDir, "staged-XRD_导师汇报.pptx");
const beforeDir = path.join(tempDir, "before-render");
const afterDir = path.join(tempDir, "after-render");
const finalLayoutDir = path.join(tempDir, "final-layout");
const replacement = "在相同数据和训练设置下重复训练 5 次，结果都更好。";

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(beforeDir, { recursive: true });
  await fs.mkdir(afterDir, { recursive: true });
  await fs.mkdir(finalLayoutDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 7) throw new Error("Expected seven slides");

  const before = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 100000,
  });
  await fs.writeFile(path.join(tempDir, "before-inspect.ndjson"), before.ndjson, "utf8");
  const entries = parseInspect(before.ndjson);
  const p5Entries = entries.filter((entry) => entry.slide === 5);
  const slideEntry = p5Entries.find((entry) => entry.kind === "slide");
  const targetEntry = p5Entries.find((entry) => entry.name === "p5-repeat-explanation");
  if (!slideEntry || !targetEntry) throw new Error("Could not locate P5 target textbox");
  if (targetEntry.text !== "重复训练 5 次：数据、模型和训练设置相同，每次只改变随机初始化等随机因素。") {
    throw new Error(`Unexpected source text: ${targetEntry.text}`);
  }

  const slide = presentation.resolve(slideEntry.id);
  const target = presentation.resolve(targetEntry.id);
  const originalPosition = { ...target.position };

  await writeBlob(path.join(beforeDir, "slide-05.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const beforeLayout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(beforeDir, "slide-05.layout.json"), await beforeLayout.text(), "utf8");

  target.text = replacement;
  target.position = originalPosition;

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  await writeBlob(path.join(afterDir, "slide-05.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const afterLayout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(afterDir, "slide-05.layout.json"), await afterLayout.text(), "utf8");

  for (let index = 0; index < presentation.slides.items.length; index += 1) {
    const layout = await presentation.slides.items[index].export({ format: "layout" });
    await fs.writeFile(
      path.join(finalLayoutDir, `slide-${String(index + 1).padStart(2, "0")}.layout.json`),
      await layout.text(),
      "utf8",
    );
  }

  const after = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 100000,
  });
  await fs.writeFile(path.join(tempDir, "after-inspect.ndjson"), after.ndjson, "utf8");
  const afterTarget = parseInspect(after.ndjson).find(
    (entry) => entry.slide === 5 && entry.name === "p5-repeat-explanation",
  );
  if (!afterTarget || afterTarget.text !== replacement || afterTarget.textLines !== 1) {
    throw new Error(`P5 replacement verification failed: ${JSON.stringify(afterTarget)}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
