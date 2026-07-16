import { Container } from 'postcss';
import { Declaration } from 'postcss';
import { Document as Document_2 } from 'postcss';
import { Message } from 'postcss';
import { Node as Node_2 } from 'postcss';
import type { Plugin as Plugin_2 } from 'postcss';
import postcss from 'postcss';
import { Root } from 'postcss';

export declare function checkColor(e: string | undefined): number[];

export declare function expand(options: NormalizeOptions): Plugin_2;

export declare function normalize(opts?: NormalizeOptions): Plugin_2;

export declare interface NormalizeOptions {
    logLevel?: 'NOTE' | 'WARNING' | 'ERROR';
    type?: 'nvue' | 'uvue';
    platform?: typeof process.env.UNI_UTS_PLATFOR;
    keepUnitPx?: boolean;
    keepVar?: boolean;
    simpleSelectorOnly?: boolean;
}

export declare function objectifier(node: Root | Document_2 | Container | null, options: ObjectifierOptions): Record<string, unknown>;

export declare interface ObjectifierContext {
    'FONT-FACE': Record<string, unknown>[];
    TRANSITION: Record<string, Record<string, unknown>>;
    messages: Message[];
    warn: (node: Node_2, message: string) => void;
}

declare interface ObjectifierOptions {
    trim: boolean;
    simpleSelectorOnly?: boolean;
    parseMessages: Message[];
    visitor?: (node: Declaration, context: ObjectifierContext) => {
        name: string;
        value: string;
    } | false;
}

export declare function objectifierWithMessages(node: Root | Document_2 | Container | null, options: ObjectifierOptions): {
    obj: Record<string, unknown>;
    messages: Message[];
};

export declare function parse(input: string, options?: ParseOptions): Promise<{
    code: string;
    messages: postcss.Message[];
}>;

declare interface ParseOptions extends NormalizeOptions {
    filename?: string;
    map?: boolean;
    mapOf?: string;
    padStyleMapOf?: string;
    ts?: boolean;
    chunk?: number;
    noCode?: boolean;
    trim?: boolean;
}

export declare function supportedPropertyReason(k: string): string;

export { }
