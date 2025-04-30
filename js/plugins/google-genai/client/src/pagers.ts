/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * Pagers for the GenAI List APIs.
 */

export enum PagedItem {
  PAGED_ITEM_BATCH_JOBS = 'batchJobs',
  PAGED_ITEM_MODELS = 'models',
  PAGED_ITEM_TUNING_JOBS = 'tuningJobs',
  PAGED_ITEM_FILES = 'files',
  PAGED_ITEM_CACHED_CONTENTS = 'cachedContents',
}

interface PagedItemConfig {
  config?: {
    pageToken?: string;
    pageSize?: number;
  };
}

interface PagedItemResponse<T> {
  nextPageToken?: string;
  batchJobs?: T[];
  models?: T[];
  tuningJobs?: T[];
  files?: T[];
  cachedContents?: T[];
}

/**
 * Pager class for iterating through paginated results.
 */
export class Pager<T> implements AsyncIterable<T> {
  private nameInternal!: PagedItem;
  private pageInternal: T[] = [];
  private paramsInternal: PagedItemConfig = {};
  private pageInternalSize!: number;
  protected requestInternal!: (
    params: PagedItemConfig
  ) => Promise<PagedItemResponse<T>>;
  protected idxInternal!: number;

  constructor(
    name: PagedItem,
    request: (params: PagedItemConfig) => Promise<PagedItemResponse<T>>,
    response: PagedItemResponse<T>,
    params: PagedItemConfig
  ) {
    this.requestInternal = request;
    this.init(name, response, params);
  }

  private init(
    name: PagedItem,
    response: PagedItemResponse<T>,
    params: PagedItemConfig
  ) {
    this.nameInternal = name;
    this.pageInternal = response[this.nameInternal] || [];
    this.idxInternal = 0;
    let requestParams: PagedItemConfig = { config: {} };
    if (!params) {
      requestParams = { config: {} };
    } else if (typeof params === 'object') {
      requestParams = { ...params };
    } else {
      requestParams = params;
    }
    if (requestParams['config']) {
      requestParams['config']['pageToken'] = response['nextPageToken'];
    }
    this.paramsInternal = requestParams;
    this.pageInternalSize =
      requestParams['config']?.['pageSize'] ?? this.pageInternal.length;
  }

  private initNextPage(response: PagedItemResponse<T>): void {
    this.init(this.nameInternal, response, this.paramsInternal);
  }

  /**
   * Returns the current page, which is a list of items.
   *
   * @remarks
   * The first page is retrieved when the pager is created. The returned list of
   * items could be a subset of the entire list.
   */
  get page(): T[] {
    return this.pageInternal;
  }

  /**
   * Returns the type of paged item (for example, ``batch_jobs``).
   */
  get name(): PagedItem {
    return this.nameInternal;
  }

  /**
   * Returns the length of the page fetched each time by this pager.
   *
   * @remarks
   * The number of items in the page is less than or equal to the page length.
   */
  get pageSize(): number {
    return this.pageInternalSize;
  }

  /**
   * Returns the parameters when making the API request for the next page.
   *
   * @remarks
   * Parameters contain a set of optional configs that can be
   * used to customize the API request. For example, the `pageToken` parameter
   * contains the token to request the next page.
   */
  get params(): PagedItemConfig {
    return this.paramsInternal;
  }

  /**
   * Returns the total number of items in the current page.
   */
  get pageLength(): number {
    return this.pageInternal.length;
  }

  /**
   * Returns the item at the given index.
   */
  getItem(index: number): T {
    return this.pageInternal[index];
  }

  /**
   * Returns an async iterator that support iterating through all items
   * retrieved from the API.
   *
   * @remarks
   * The iterator will automatically fetch the next page if there are more items
   * to fetch from the API.
   *
   * @example
   *
   * ```ts
   * const pager = await ai.files.list({config: {pageSize: 10}});
   * for await (const file of pager) {
   *   console.log(file.name);
   * }
   * ```
   */
  [Symbol.asyncIterator](): AsyncIterator<T> {
    return {
      next: async () => {
        if (this.idxInternal >= this.pageLength) {
          if (this.hasNextPage()) {
            await this.nextPage();
          } else {
            return { value: undefined, done: true };
          }
        }
        const item = this.getItem(this.idxInternal);
        this.idxInternal += 1;
        return { value: item, done: false };
      },
      return: async () => {
        return { value: undefined, done: true };
      },
    };
  }

  /**
   * Fetches the next page of items. This makes a new API request.
   *
   * @throws {Error} If there are no more pages to fetch.
   *
   * @example
   *
   * ```ts
   * const pager = await ai.files.list({config: {pageSize: 10}});
   * let page = pager.page;
   * while (true) {
   *   for (const file of page) {
   *     console.log(file.name);
   *   }
   *   if (!pager.hasNextPage()) {
   *     break;
   *   }
   *   page = await pager.nextPage();
   * }
   * ```
   */
  async nextPage(): Promise<T[]> {
    if (!this.hasNextPage()) {
      throw new Error('No more pages to fetch.');
    }
    const response = await this.requestInternal(this.params);
    this.initNextPage(response);
    return this.page;
  }

  /**
   * Returns true if there are more pages to fetch from the API.
   */
  hasNextPage(): boolean {
    if (this.params['config']?.['pageToken'] !== undefined) {
      return true;
    }
    return false;
  }
}
