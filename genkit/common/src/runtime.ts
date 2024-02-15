let projectIdOverride: string;
/**
 *
 */
export function getProjectId() {
  if (projectIdOverride !== undefined) {
    return projectIdOverride;
  }
  return process.env['GCLOUD_PROJECT'] || '';
}
