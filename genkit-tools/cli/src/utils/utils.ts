import path from "path";

/**
 * Detects if the CLI is running from a compiled binary vs npm package.
 * When running from a binary (via bun compile or similar), process.execPath
 * will point to the binary executable rather than node/bun runtime.
 */
export function isRunningFromBinary(): boolean {
  const execPath = process.execPath;
  const execName = path.basename(execPath);
  // If running from npm/yarn/pnpm, execPath typically points to node
  // If running from binary, execPath points to the actual binary
  return !execName.includes('node') && !execName.includes('bun');
}