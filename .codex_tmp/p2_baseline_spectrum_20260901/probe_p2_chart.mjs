import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const tmpDir = "E:/AI4science/.codex_tmp/p2_baseline_spectrum_20260901";
const sourcePath = path.join(tmpDir, "source-deck.pptx");

async function main() {
  const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
  const chart = presentation.resolve("ch/mx0n6hwv");
  const series = chart.series.items.map((item) => ({
    name: item.name,
    values: item.values,
    proto: item.toProto?.(),
  }));
  const probe = {
    snapshot: chart.toSnapshot?.(),
    proto: chart.toProto?.(),
    categories: chart.categories,
    series,
    chartKeys: Reflect.ownKeys(chart).filter((key) => typeof key === "string"),
  };
  await fs.writeFile(path.join(tmpDir, "p2-chart-probe.json"), JSON.stringify(probe, null, 2), "utf8");
  console.log(JSON.stringify({ seriesCount: series.length, valueCount: series[0]?.values?.length ?? 0 }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
