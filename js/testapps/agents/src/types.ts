export interface AgentState {
  parentId: number;
  parentName: string;
  students: {
    id: number;
    name: string;
    grade: number;
    activities: string[];
  }[];
}