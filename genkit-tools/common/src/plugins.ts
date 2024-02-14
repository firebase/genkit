export interface ToolPlugin {
  name: string;
  keyword: string;
  actions: ToolPluginAction[];
}

export interface ToolPluginAction {
  name: string;
  hook: () => unknown;
}
