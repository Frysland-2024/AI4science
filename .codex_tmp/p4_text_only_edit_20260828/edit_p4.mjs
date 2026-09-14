import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p4_text_only_edit_20260828";
const sourcePptx = path.join(tmpDir, "template-starter.pptx");
const finalPptx = "E:/AI4science/outputs/XRD_导师汇报.pptx";
const renderDir = path.join(tmpDir, "final-render");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePptx));
  if (presentation.slides.items.length !== 4) {
    throw new Error(`Expected 4 slides, found ${presentation.slides.items.length}`);
  }

  const slide4 = presentation.resolve("sl/jyx0ra1s");

  for (const anchorId of [
    "ch/etsjm14b",
    "ch/fe10f6lw",
    "ch/gfu1obm1",
    "ch/1g3ihw3m",
    "ch/6psjih4z",
  ]) {
    const chart = presentation.resolve(anchorId);
    slide4.charts.deleteById(chart.id);
  }

  for (const anchorId of [
    "sh/p0batw72",
    "sh/2xkrih8b",
    "sh/fu9sn2p0",
    "sh/sri9s7q9",
    "sh/knex8j21",
  ]) {
    presentation.resolve(anchorId).delete();
  }

  const rows = [
    {
      id: "sh/oz29krqh",
      name: "峰位偏移",
      suffix: "　　峰整体左右移动",
      top: 164,
    },
    {
      id: "sh/1wbapc7q",
      name: "峰展宽",
      suffix: "　　　峰变宽、相邻峰可能重叠",
      top: 261,
    },
    {
      id: "sh/et0reh8f",
      name: "背景变化",
      suffix: "　　基线及背景形状发生变化",
      top: 358,
    },
    {
      id: "sh/ilwf69kv",
      name: "计数噪声",
      suffix: "　　谱线上出现随机波动",
      top: 455,
    },
    {
      id: "sh/5ony1oj6",
      name: "择优取向",
      suffix: "　　各衍射峰的相对强度改变",
      top: 552,
    },
  ];

  for (const row of rows) {
    const shape = presentation.resolve(row.id);
    shape.position = { left: 545, top: row.top, width: 655, height: 32 };
    shape.text.set([
      [
        {
          run: row.name,
          textStyle: { bold: true, color: "#153E6A" },
        },
        {
          run: row.suffix,
          textStyle: { bold: false, color: "#6B7B8D" },
        },
      ],
    ]);
    shape.text.fontSize = 20;
    shape.text.bold = true;
    shape.text.alignment = "left";
    shape.text.verticalAlignment = "middle";
    shape.text.autoFit = "none";
    shape.text.wrap = "none";
    shape.text.insets = { top: 0, right: 0, bottom: 0, left: 0 };
  }

  const notes = presentation.resolve("nt/jyx0ra1s");
  notes.setText([
    "本页只回答两个问题：使用多少独立晶体结构，以及模拟了哪些常见测量扰动。",
    "右侧用五行中文说明每类扰动对谱图最直接的影响。",
    "",
    "[Sources]",
    "- E:/AI4science/xrd_robustness/configs/experiment.public.json",
    "- E:/AI4science/xrd_robustness/configs/data.method_transfer.structure_split.json",
    "- E:/AI4science/xrd_robustness/data/formal_14060/manifests/split_manifest.json",
    "- E:/AI4science/xrd_robustness/configs/simulation.method_transfer.frozen.json",
  ].join("\n"));

  const finalInspect = await presentation.inspect({
    kind: "slide,textbox,shape,image,table,chart,notes,layout",
    maxChars: 30000,
  });
  await fs.writeFile(path.join(tmpDir, "final-inspect.ndjson"), finalInspect.ndjson, "utf8");

  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(
      path.join(renderDir, `${stem}.png`),
      await presentation.export({ slide, format: "png", scale: 1 }),
    );
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(renderDir, `${stem}.layout.json`), await layout.text(), "utf8");
  }
  await writeBlob(
    path.join(renderDir, "montage.webp"),
    await presentation.export({ format: "webp", montage: true, scale: 1 }),
  );

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(finalPptx);
  console.log(`Updated ${finalPptx}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
