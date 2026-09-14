import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p2_baseline_spectrum_20260901";
const sourcePath = path.join(tmpDir, "source-deck.pptx");
const outputPath = path.join(tmpDir, "staged-XRD_导师汇报.pptx");
const renderDir = path.join(tmpDir, "after-p2");

const FONT = "Microsoft YaHei";
const NAVY = "#143A63";
const BLUE = "#285F97";
const INK = "#27384A";
const MUTED = "#657384";
const ORANGE = "#E77A25";
const ORANGE_FILL = "#FFF3E8";

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function configureText(shape, position, style = {}) {
  shape.position = position;
  shape.text.typeface = FONT;
  shape.text.color = style.color ?? INK;
  shape.text.fontSize = style.fontSize ?? 20;
  shape.text.bold = style.bold ?? false;
  shape.text.alignment = style.alignment ?? "left";
  shape.text.verticalAlignment = style.verticalAlignment ?? "middle";
  shape.text.wrap = style.wrap ?? "square";
  shape.text.autoFit = style.autoFit ?? "none";
  shape.text.insets = style.insets ?? { top: 0, right: 0, bottom: 0, left: 0 };
}

function addTextBox(slide, name, position, text, style = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position,
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  configureText(shape, position, style);
  return shape;
}

function requireElement(layoutElements, aid, label) {
  const element = layoutElements.find((entry) => entry.aid === aid);
  if (!element) throw new Error(`Could not locate ${label}: ${aid}`);
  return element;
}

async function main() {
  await fs.mkdir(renderDir, { recursive: true });
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  if (presentation.slides.items.length !== 8) {
    throw new Error(`Expected 8 slides, found ${presentation.slides.items.length}`);
  }

  const slide = presentation.slides.items[1];
  if (!slide) throw new Error("Could not locate slide 2");
  const beforeLayout = JSON.parse(await (await slide.export({ format: "layout" })).text());
  const inherited = beforeLayout.elements ?? [];

  for (const [aid, label] of [
    ["sh/nu58f2hs", "title"],
    ["sh/9072xkry", "slide number"],
    ["sh/ozy1ofad", "divider"],
    ["sh/b29kza94", "crystal structure"],
    ["sh/a10jqpsj", "old computation node"],
    ["sh/x4r21kru", "perturbation box"],
    ["sh/cnupgny5", "first arrow"],
    ["sh/do3q9szq", "second arrow"],
    ["sh/t8byxkn2", "third arrow"],
    ["sh/s72xofmh", "perturbation examples"],
    ["sh/76twva5c", "training-spectrum heading"],
    ["sh/65kfmpor", "training spectrum A label"],
    ["sh/hcvy14ne", "training spectrum B label"],
    ["sh/gbmxszmt", "training spectrum C label"],
    ["sh/mtwrmxg7", "bottom transition"],
    ["sh/bip8jmho", "subtitle"],
    ["sh/fadgzu58", "literature footer"],
    ["ch/mx0n6hwv", "training spectrum A chart"],
    ["ch/xob6lwfi", "training spectrum B chart"],
    ["ch/wn25crex", "training spectrum C chart"],
  ]) requireElement(inherited, aid, label);

  const title = presentation.resolve("sh/nu58f2hs");
  title.text = "前人工作：随机采样扰动参数，生成多样化训练谱";
  configureText(title, { left: 58, top: 26, width: 1096, height: 56 }, {
    fontSize: 38,
    bold: true,
    color: NAVY,
    alignment: "left",
    wrap: "none",
  });

  const pageNumber = presentation.resolve("sh/9072xkry");
  pageNumber.text = "02 / 08";
  configureText(pageNumber, { left: 1176, top: 40, width: 48, height: 24 }, {
    fontSize: 14,
    color: MUTED,
    alignment: "right",
    wrap: "none",
  });

  const subtitle = presentation.resolve("sh/bip8jmho");
  subtitle.text = "已有工作通过随机采样峰移、展宽、背景/噪声、择优取向等扰动参数，生成更多样的训练谱。";
  configureText(subtitle, { left: 58, top: 91, width: 1146, height: 34 }, {
    fontSize: 18,
    color: MUTED,
    alignment: "left",
    wrap: "none",
  });

  const crystal = presentation.resolve("sh/b29kza94");
  crystal.text = "晶体结构";
  configureText(crystal, { left: 54, top: 263, width: 140, height: 58 }, {
    fontSize: 26,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  const baselineLabel = presentation.resolve("sh/a10jqpsj");
  baselineLabel.text = "基准计算谱";
  baselineLabel.fill = "none";
  baselineLabel.line = { style: "solid", fill: "none", width: 0 };
  configureText(baselineLabel, { left: 226, top: 208, width: 216, height: 30 }, {
    fontSize: 20,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  const perturb = presentation.resolve("sh/x4r21kru");
  perturb.text = "随机采样\n扰动参数";
  perturb.fill = ORANGE_FILL;
  perturb.line = { style: "solid", fill: ORANGE, width: 1.8 };
  configureText(perturb, { left: 484, top: 239, width: 222, height: 104 }, {
    fontSize: 26,
    bold: true,
    color: ORANGE,
    alignment: "center",
    wrap: "square",
    insets: { top: 8, right: 8, bottom: 8, left: 8 },
  });

  const arrow1 = presentation.resolve("sh/cnupgny5");
  arrow1.text = "→";
  configureText(arrow1, { left: 192, top: 256, width: 34, height: 68 }, {
    fontSize: 34,
    bold: true,
    color: BLUE,
    alignment: "center",
    wrap: "none",
  });
  const arrow2 = presentation.resolve("sh/do3q9szq");
  arrow2.text = "→";
  configureText(arrow2, { left: 442, top: 256, width: 38, height: 68 }, {
    fontSize: 34,
    bold: true,
    color: BLUE,
    alignment: "center",
    wrap: "none",
  });
  const arrow3 = presentation.resolve("sh/t8byxkn2");
  arrow3.text = "→";
  configureText(arrow3, { left: 710, top: 256, width: 58, height: 68 }, {
    fontSize: 34,
    bold: true,
    color: ORANGE,
    alignment: "center",
    wrap: "none",
  });

  const trainingA = presentation.resolve("ch/mx0n6hwv");
  const trainingSeriesProto = trainingA.series.getItemAt(0).toProto();
  const xValues = [...(trainingSeriesProto.xValues ?? [])];
  const values = [...(trainingSeriesProto.values ?? [])];
  if (!xValues.length || xValues.length !== values.length) {
    throw new Error(`Could not derive baseline spectrum from the embedded slide-2 chart: x=${xValues.length}, y=${values.length}`);
  }

  slide.charts.add("scatter", {
    name: "p2-baseline-computation-spectrum",
    position: { left: 229, top: 242, width: 210, height: 56 },
    series: [{
      name: "基准计算谱",
      xValues,
      values,
      line: { style: "solid", fill: BLUE, width: 2.1 },
      marker: { symbol: "none" },
    }],
    scatterOptions: { style: "line", varyColors: false },
    hasLegend: false,
    xAxis: {
      visible: false,
      min: Math.min(...xValues),
      max: Math.max(...xValues),
      tickLabelPosition: "none",
      majorGridlines: null,
      minorGridlines: null,
      line: { style: "solid", fill: "#FFFFFF", width: 0 },
    },
    yAxis: {
      visible: false,
      min: 0,
      max: 1.04,
      tickLabelPosition: "none",
      majorGridlines: null,
      minorGridlines: null,
      line: { style: "solid", fill: "#FFFFFF", width: 0 },
    },
    chartFill: "#FFFFFF",
    chartLine: { style: "solid", fill: "#FFFFFF", width: 0 },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", fill: "#FFFFFF", width: 0 },
  });

  addTextBox(slide, "p2-baseline-note", { left: 226, top: 306, width: 216, height: 24 }, "未加入测量扰动", {
    fontSize: 14.5,
    color: MUTED,
    alignment: "center",
    wrap: "none",
  });

  const examples = presentation.resolve("sh/s72xofmh");
  examples.text = "峰移 · 展宽 · 背景/噪声 · 择优取向";
  configureText(examples, { left: 444, top: 358, width: 300, height: 28 }, {
    fontSize: 16,
    color: MUTED,
    alignment: "center",
    wrap: "none",
  });

  const heading = presentation.resolve("sh/76twva5c");
  heading.text = "生成多种训练谱";
  configureText(heading, { left: 804, top: 168, width: 398, height: 38 }, {
    fontSize: 25,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  for (const [aid, text, top] of [
    ["sh/65kfmpor", "训练谱 A", 227],
    ["sh/hcvy14ne", "训练谱 B", 322],
    ["sh/gbmxszmt", "训练谱 C", 417],
  ]) {
    const label = presentation.resolve(aid);
    label.text = text;
    configureText(label, { left: 772, top, width: 86, height: 32 }, {
      fontSize: 17,
      bold: true,
      color: INK,
      alignment: "right",
      wrap: "none",
    });
  }

  const transition = presentation.resolve("sh/mtwrmxg7");
  transition.text = "但这些同源生成谱，通常仍被当作彼此独立的训练样本使用。";
  configureText(transition, { left: 150, top: 526, width: 980, height: 42 }, {
    fontSize: 27,
    bold: true,
    color: NAVY,
    alignment: "center",
    wrap: "none",
  });

  const layoutBlob = await slide.export({ format: "layout" });
  const layoutText = await layoutBlob.text();
  await fs.writeFile(path.join(renderDir, "slide-02.layout.json"), layoutText, "utf8");
  const layout = JSON.parse(layoutText);
  const elements = layout.elements ?? [];

  for (const required of [
    "前人工作：随机采样扰动参数，生成多样化训练谱",
    "已有工作通过随机采样峰移、展宽、背景/噪声、择优取向等扰动参数，生成更多样的训练谱。",
    "晶体结构",
    "基准计算谱",
    "未加入测量扰动",
    "随机采样",
    "扰动参数",
    "生成多种训练谱",
    "训练谱 A",
    "训练谱 B",
    "训练谱 C",
    "峰移 · 展宽 · 背景/噪声 · 择优取向",
    "但这些同源生成谱，通常仍被当作彼此独立的训练样本使用。",
  ]) {
    const found = elements.some((entry) => typeof entry.text === "string" && entry.text.includes(required));
    if (!found) throw new Error(`Missing slide-2 phrase: ${required}`);
  }

  for (const forbidden of [
    "根据晶体结构\n计算 XRD 谱",
    "根据晶体结构计算 XRD 谱",
    "干净谱",
    "但是这些生成谱仍然作为彼此独立的训练样本使用。",
  ]) {
    if (elements.some((entry) => typeof entry.text === "string" && entry.text.includes(forbidden))) {
      throw new Error(`Slide 2 still contains forbidden wording: ${forbidden}`);
    }
  }

  const titleEntry = elements.find((entry) => entry.text === "前人工作：随机采样扰动参数，生成多样化训练谱");
  const subtitleEntry = elements.find((entry) => entry.text === "已有工作通过随机采样峰移、展宽、背景/噪声、择优取向等扰动参数，生成更多样的训练谱。");
  const transitionEntry = elements.find((entry) => entry.text === "但这些同源生成谱，通常仍被当作彼此独立的训练样本使用。");
  if (!titleEntry || titleEntry.textLayout?.lineCount !== 1) throw new Error(`Slide-2 title wrapped: ${JSON.stringify(titleEntry)}`);
  if (!subtitleEntry || subtitleEntry.textLayout?.lineCount !== 1) throw new Error(`Slide-2 subtitle wrapped: ${JSON.stringify(subtitleEntry)}`);
  if (!transitionEntry || transitionEntry.textLayout?.lineCount !== 1) throw new Error(`Slide-2 transition wrapped: ${JSON.stringify(transitionEntry)}`);

  const charts = elements.filter((entry) => entry.kind === "chart");
  if (charts.length !== 4) throw new Error(`Expected four charts on slide 2, found ${charts.length}`);
  const baselineChart = charts.find((entry) => {
    const [left, top, width, height] = entry.bbox ?? [];
    return Math.abs(left - 229) < 1 && Math.abs(top - 242) < 1 && Math.abs(width - 210) < 1 && Math.abs(height - 56) < 1;
  });
  if (!baselineChart) throw new Error("Could not identify the baseline-computation spectrum chart");
  const [, , baselineWidth, baselineHeight] = baselineChart.bbox ?? [];
  if (baselineWidth < 200 || baselineWidth > 230 || baselineHeight < 50 || baselineHeight > 62) {
    throw new Error(`Unexpected baseline chart size: ${JSON.stringify(baselineChart.bbox)}`);
  }

  const overflow = elements.filter((entry) => {
    const [left, top, width, height] = entry.bbox ?? [];
    if (![left, top, width, height].every(Number.isFinite)) return false;
    return left < -0.5 || top < -0.5 || left + width > 1280.5 || top + height > 720.5;
  });
  if (overflow.length) throw new Error(`Slide-2 canvas overflow: ${JSON.stringify(overflow)}`);

  await writeBlob(path.join(renderDir, "slide-02.png"), await presentation.export({ slide, format: "png", scale: 1 }));
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);
  console.log(JSON.stringify({
    outputPath,
    renderedSlides: [2],
    slide2OverflowCount: 0,
    chartCount: charts.length,
    baselineChartBBox: baselineChart.bbox,
  }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
