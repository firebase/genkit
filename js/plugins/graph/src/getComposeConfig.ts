import { promises as fs, readdirSync, readFileSync } from 'fs';
import Graph from 'graphology';
import path from 'path';
import { parse, stringify } from 'yaml';
import {
  FlowGraph,
  SerializedFlowGraph,
  SerializedFlowGraphSchema,
} from './types';
// Helper type for the supported extensions

type FileExtension = 'yaml' | 'yml' | 'json';

export async function findGenkitComposeFile(
  startDir: string = __dirname
): Promise<string | null> {
  try {
    // Read all entries in the current directory
    const entries = await fs.readdir(startDir, { withFileTypes: true });

    const targetFileNames = [
      'genkit-compose.yaml',
      'genkit-compose.yml',
      'genkit-compose.json',
    ];

    // First, search for the target files in the current directory
    for (const fileName of targetFileNames) {
      if (entries.some((entry) => entry.isFile() && entry.name === fileName)) {
        return path.join(startDir, fileName); // Return the full path of the found file
      }
    }

    // If not found, search in subdirectories
    for (const entry of entries) {
      if (entry.isDirectory()) {
        const subdirPath = path.join(startDir, entry.name);
        const found = await findGenkitComposeFile(subdirPath);
        if (found) return found; // Return as soon as a file is found in any subdirectory
      }
    }
  } catch (error) {
    console.error(`Error reading directory ${startDir}:`, error);
    // Optionally return null or rethrow the error depending on your error handling strategy
    return null;
  }

  return null; // Return null if the file is not found in the directory tree
}

export function findGenkitComposeFileSync(
  startDir: string = __dirname
): string | null {
  try {
    // Read all entries in the current directory
    const entries = readdirSync(startDir, { withFileTypes: true });

    const targetFileNames = [
      'genkit-compose.yaml',
      'genkit-compose.yml',
      'genkit-compose.json',
    ];

    // First, search for the target files in the current directory
    for (const fileName of targetFileNames) {
      if (entries.some((entry) => entry.isFile() && entry.name === fileName)) {
        return path.join(startDir, fileName); // Return the full path of the found file
      }
    }

    // If not found, search in subdirectories
    for (const entry of entries) {
      if (entry.isDirectory()) {
        const subdirPath = path.join(startDir, entry.name);
        const found = findGenkitComposeFileSync(subdirPath);
        if (found) return found; // Return as soon as a file is found in any subdirectory
      }
    }
  } catch (error) {
    console.error(`Error reading directory ${startDir}:`, error);
    // Optionally return null or rethrow the error depending on your error handling strategy
    return null;
  }

  return null; // Return null if the file is not found in the directory tree
}

// Function to determine the file extension
export function getFileExtension(filePath: string): FileExtension | null {
  const ext = path.extname(filePath).substring(1);
  if (ext === 'yaml' || ext === 'yml' || ext === 'json') {
    return ext as FileExtension;
  }
  return null;
}

// Function to read and parse the file based on its extension
export async function readAndParseConfigFile(
  filePath: string
): Promise<SerializedFlowGraph> {
  // Determine the file extension
  const extension = getFileExtension(filePath);
  if (!extension) {
    throw new Error(`Unsupported file extension for file: ${filePath}`);
  }

  // Read the file content
  const fileContent = await fs.readFile(filePath, 'utf8');

  // Parse the file content based on its extension
  switch (extension) {
    case 'yaml':
    case 'yml':
      return SerializedFlowGraphSchema.parse(
        parse(fileContent)
      ) as SerializedFlowGraph;
    case 'json':
      return SerializedFlowGraphSchema.parse(
        JSON.parse(fileContent)
      ) as SerializedFlowGraph;
    default:
      throw new Error(`Unsupported file extension: ${extension}`);
  }
}

export function readAndParseConfigFileSync(
  filePath: string
): SerializedFlowGraph {
  // Determine the file extension
  const extension = getFileExtension(filePath);
  if (!extension) {
    throw new Error(`Unsupported file extension for file: ${filePath}`);
  }

  // Read the file content
  const fileContent = readFileSync(filePath, 'utf8');

  // Parse the file content based on its extension
  switch (extension) {
    case 'yaml':
    case 'yml':
      return SerializedFlowGraphSchema.parse(
        stringify(fileContent)
      ) as SerializedFlowGraph;
    case 'json':
      return SerializedFlowGraphSchema.parse(
        JSON.parse(fileContent)
      ) as SerializedFlowGraph;
    default:
      throw new Error(`Unsupported file extension: ${extension}`);
  }
}

export const parseAsGraph = (serializedGraph: SerializedFlowGraph) =>
  Graph.from(serializedGraph) as FlowGraph;
