import { isAction } from "@genkit-ai/core";
import { execSync } from "child_process";
import { writeFileSync, mkdirSync, statSync, existsSync, unlinkSync } from "fs";
import path from "path";

type ExportedAction = {
  export: string;
  name: string;
};
const registry: Record<string, ExportedAction[]> = {
  flows: [],
};

const foo = await import(`${process.cwd()}/src/index.ts`);

for (const [key, value] of Object.entries(foo)) {
  if (isAction(value) && value.__action.actionType === "flow") {
    registry.flows?.push({
      export: key,
      name: value.__action.name,
    });
  }
}

const bundledCode = `
  import { setGenkitRuntimeConfig } from "@genkit-ai/core";
  import {
  ${registry.flows!.map((flow) => flow.export).join(",\n")}
  } from "${process.cwd()}/src/index.ts";

  setGenkitRuntimeConfig({
    jsonSchemaMode: 'interpret',
    sandboxedRuntime: true,
  });

  export const flows = {
  ${registry
    .flows!.map(
      (flow) => `
    ${flow.name}: ${flow.export},
      `,
    )
    .join("\n")}
  };

  // Wrangler requires a default export to treat this as an ES Module worker (so nodejs_compat
  // is applied). This bundle is consumed via the Worker Loader for its \`flows\` export only;
  // the default export is unused.
  export default { fetch: () => new Response("") };
`;

mkdirSync("./app", { recursive: true });
writeFileSync("./app/index.ts", bundledCode);

const outDir = "./dist/app";
const outPath = path.join(outDir, "index.js");

const wranglerConfig = {
  name: "flows-build",
  main: "app/index.ts",
  compatibility_date: "2025-01-01",
  compatibility_flags: ["nodejs_compat"],
  alias: {},
};
const wranglerConfigPath = path.join(process.cwd(), "wrangler.flows.jsonc");
writeFileSync(wranglerConfigPath, JSON.stringify(wranglerConfig, null, 2));
try {
  execSync(
    `npx wrangler deploy --config "${wranglerConfigPath}" --dry-run --outdir "${path.resolve(process.cwd(), outDir)}"`,
    { cwd: process.cwd(), stdio: "inherit" }
  );
} finally {
  if (existsSync(wranglerConfigPath)) {
    unlinkSync(wranglerConfigPath);
  }
}
if (!existsSync(outPath)) {
  console.error("Wrangler build did not produce index.js at", outPath);
  process.exit(1);
}
console.log("Built successfully, size:", statSync(outPath).size);
