import MagicString from 'magic-string';
import type { Plugin } from 'vite';
export declare function rewriteImportVuePlugin(): Plugin;
/**
 * import { xx as yy, zz } from 'vue' =>
 * const { xx: yy, zz } = globalThis.Vue
 */
export declare function rewriteImportVue(input: string): MagicString;
