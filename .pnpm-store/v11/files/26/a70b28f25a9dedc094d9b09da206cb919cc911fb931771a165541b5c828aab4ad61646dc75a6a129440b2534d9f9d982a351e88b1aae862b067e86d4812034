export * from './manifest';
export interface UniXPageOptions {
    disableScroll?: boolean;
    enablePullDownRefresh?: boolean;
    scrollIndicator?: 'none';
}
export declare function normalizeUniAppXAppPagesJson(jsonStr: string): UniApp.PagesJson;
export declare function parseUniXPageOptions(filename: string): UniXPageOptions | undefined;
/**
 * TODO 应该闭包，通过globalThis赋值？
 * @param pagesJson
 * @param manifestJson
 * @returns
 */
export declare function normalizeUniAppXAppConfig(pagesJson: UniApp.PagesJson, manifestJson: Record<string, any>): string;
export declare function isUniXPageFile(source: string, importer: string, inputDir?: string): any;
export declare function getUniXPagePaths(): any;
