import { execSync } from "child_process";

/**
 * Detects if the CLI is running from a local npm package vs global npm package.
 * When running from a local npm package, process.execPath
 * will point to the node runtime rather than the global node_modules location.
 */
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
