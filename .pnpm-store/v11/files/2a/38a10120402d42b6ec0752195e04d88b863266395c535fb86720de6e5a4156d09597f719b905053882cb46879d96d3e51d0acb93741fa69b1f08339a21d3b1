import type { SourceLocation } from '@vue/compiler-core';
export { formatErrMsg, formatInfoMsg, formatWarnMsg } from './format';
type LogType = 'error' | 'warn' | 'info' | 'log';
export declare function resetOutput(type: LogType): void;
export declare function output(type: LogType, msg: string): void;
export interface CompileLogError extends Error {
    loc?: Omit<SourceLocation, 'source'>;
    customPrint?: () => void;
}
export interface CompileLogOptions {
    plugin?: string;
    line?: number;
    column?: number;
}
export declare function onCompileLog(type: 'warn' | 'error', error: CompileLogError, code: string, relativeFileName: string, options?: CompileLogOptions): void;
