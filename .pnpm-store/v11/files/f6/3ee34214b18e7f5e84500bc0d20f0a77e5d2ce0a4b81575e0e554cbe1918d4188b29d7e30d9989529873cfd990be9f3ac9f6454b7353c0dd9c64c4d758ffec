import type { Plugin, ResolvedConfig, ServerOptions } from 'vite';
export interface ManifestBasicSslOptions {
    name?: string;
    domains?: string[];
    certDir?: string;
}
type ManifestServerOptions = ServerOptions & {
    https?: ServerOptions['https'] | true;
    basicSsl?: ManifestBasicSslOptions;
};
export declare function createConfig(options: {
    resolvedConfig: ResolvedConfig | null;
}): Plugin['config'];
export declare function resolveManifestServerOptions(inputDir: string): {
    server: ManifestServerOptions;
    basicSslOptions: ManifestBasicSslOptions | undefined;
    enableBasicSsl: boolean;
};
export {};
