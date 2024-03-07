/**
 * Deletes any properties with `undefined` values in the provided object.
 * Modifies the provided object.
 */
export function deleteUndefinedProps(obj: any) {
  for (const prop in obj) {
    if (obj[prop] === undefined) {
      delete obj[prop];
    } else {
      if (typeof obj[prop] === 'object') {
        deleteUndefinedProps(obj[prop]);
      }
    }
  }
}
