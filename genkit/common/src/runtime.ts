let projectIdOverride: string;
let locationOverride: string;
/**
 *
 */
export function getProjectId() {
  if (projectIdOverride !== undefined) {
    return projectIdOverride;
  }
  return process.env['GCLOUD_PROJECT'] || '';
}

/**
 *
 */
export function getLocation() {
  if (locationOverride !== undefined) {
    return locationOverride;
  }
  return process.env['GCLOUD_LOCATION'] || '';
}
