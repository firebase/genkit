import path from "path";
import { execSync } from "child_process";
import { name } from "./version";

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

export function runningFromNpmLocally(): boolean {
    // Check if running from a global node_modules location
    const globalNodeModules = execSync('npm root -g').toString().trim();
    const execPath = process.execPath;
    // If the execPath is inside the global node_modules directory, it's global
    if (execPath.startsWith(globalNodeModules)) {
      return false; // running globally, not locally
    }
    // Otherwise, assume it's local (e.g., npx, local install, or dev)
    return true;
}
