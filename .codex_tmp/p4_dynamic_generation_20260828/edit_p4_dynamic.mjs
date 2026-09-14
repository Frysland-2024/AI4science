import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const rootDir = "E:/AI4science";
const tempDir = path.join(rootDir, ".codex_tmp/p4_dynamic_generation_20260828");
const sourcePath = path.join(tempDir, "template-starter.pptx");
const outputPath = path.join(rootDir, "outputs/XRD_导师汇报.pptx");
const renderDir = path.join(tempDir, "after-render");
const layoutDir = path.join(tempDir, "final-layout");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function parseInspect(ndjson) {
  return ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function requireEntry(entries, predicate, label) {
  const entry = entries.find(predicate);
  if (!entry) throw new Error(`Could not locate ${label}`);
  return entry;
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  await fs.mkdir(layoutDir, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 6) {
    throw new Error(`Expected 6 slides, found ${presentation.slides.items.length}`);
  }

  const snapshot = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes",
    maxChars: 60000,
  });
  const entries = parseInspect(snapshot.ndjson);
  const targetEntry = requireEntry(
    entries,
    (entry) => entry.slide === 4 && entry.id === "sh/g36tgryd" &&
      (entry.text ?? "").startsWith("按晶体结构划分"),
    "slide 4 lower-left explanatory textbox",
  );
  const rightTable = requireEntry(
    entries,
    (entry) => entry.slide === 4 && entry.kind === "table" && entry.id === "tb/8jqxsf29",
    "slide 4 right-side disturbance table",
  );
  if (rightTable.preview !== "扰动类型 | 对谱图的影响" || rightTable.rows !== 6 || rightTable.cols !== 2) {
    throw new Error("Slide 4 right-side table is not the expected inherited table");
  }

  const target = presentation.resolve(targetEntry.id);
  target.position = { left: 72, top: 458, width: 405, height: 168 };
  target.text.set([
    [
      {
        run: "按晶体结构划分",
        textStyle: {
          bold: true,
          color: "#153E6A",
          fontSize: "19px",
          typeface: "Microsoft YaHei",
        },
      },
    ],
    [
      {
        run: "同一晶体的不同谱始终留在同一数据集",
        textStyle: {
          bold: false,
          color: "#657384",
          fontSize: "16px",
          typeface: "Microsoft YaHei",
        },
      },
    ],
    [{ run: "", textStyle: { fontSize: "10px", typeface: "Microsoft YaHei" } }],
    [
      {
        run: "训练时实时生成谱",
        textStyle: {
          bold: true,
          color: "#153E6A",
          fontSize: "19px",
          typeface: "Microsoft YaHei",
        },
      },
    ],
    [
      {
        run: "同一晶体 → ",
        textStyle: {
          bold: false,
          color: "#657384",
          fontSize: "16px",
          typeface: "Microsoft YaHei",
        },
      },
      {
        run: "随机“换测量条件”",
        textStyle: {
          bold: true,
          color: "#E07A2A",
          fontSize: "16px",
          typeface: "Microsoft YaHei",
        },
      },
      {
        run: " → 不同训练谱",
        textStyle: {
          bold: false,
          color: "#657384",
          fontSize: "16px",
          typeface: "Microsoft YaHei",
        },
      },
    ],
  ]);
  target.text.fontSize = 16;
  target.text.typeface = "Microsoft YaHei";
  target.text.color = "#657384";
  target.text.alignment = "left";
  target.text.verticalAlignment = "top";
  target.text.wrap = "square";
  target.text.autoFit = "none";
  target.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };

  const slide4 = presentation.slides.items[3];
  slide4.speakerNotes.textFrame.setText([
    "本页回答三个问题：使用多少独立晶体结构、模拟哪些测量扰动、训练谱如何生成。",
    "训练时，从同一晶体结构的理想峰表出发，在每个优化步在线采样两组测量条件并即时生成两条扰动谱；随机性由结构、训练轮次、训练步和视图编号共同控制，因此可复现。",
    "验证和测试时冻结每个样本的扰动参数与随机种子，确保不同模型在完全相同的固定谱上比较。",
    "",
    "[Sources]",
    "- E:/AI4science/xrd_robustness/configs/experiment.public.json",
    "- E:/AI4science/xrd_robustness/configs/data.method_transfer.structure_split.json",
    "- E:/AI4science/xrd_robustness/data/formal_14060/manifests/split_manifest.json",
    "- E:/AI4science/xrd_robustness/configs/simulation.method_transfer.frozen.json",
    "- E:/AI4science/xrd_robustness/src/xrd_robustness/training/runner.py",
    "- E:/AI4science/xrd_robustness/src/xrd_robustness/online_views.py",
    "- E:/AI4science/xrd_robustness/src/xrd_robustness/view_manifest.py",
    "- E:/AI4science/xrd_robustness/scripts/run_simulated_test.py",
  ].join("\n"));

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  await writeBlob(
    path.join(renderDir, "slide-04.png"),
    await presentation.export({ slide: slide4, format: "png", scale: 1 }),
  );
  const layout = await slide4.export({ format: "layout" });
  const layoutText = await layout.text();
  await fs.writeFile(path.join(renderDir, "slide-04.layout.json"), layoutText, "utf8");
  await fs.writeFile(path.join(layoutDir, "slide-04.layout.json"), layoutText, "utf8");

  const finalInspect = await presentation.inspect({
    kind: "slide,textbox,shape,chart,table,notes,layout",
    maxChars: 60000,
  });
  const p4Lines = parseInspect(finalInspect.ndjson)
    .filter((entry) => entry.slide === 4)
    .map((entry) => JSON.stringify(entry))
    .join("\n");
  await fs.writeFile(path.join(tempDir, "final-p4-inspect.ndjson"), `${p4Lines}\n`, "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
