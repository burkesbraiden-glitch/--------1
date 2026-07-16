"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.uniStatsPlugin = void 0;
const fs_extra_1 = __importDefault(require("fs-extra"));
const utils_1 = require("../../utils");
const json_1 = require("../../json");
const messages_1 = require("../../messages");
const emittedHashMap = new WeakMap();
function normalizeVaporRenderTarget(target) {
    if (typeof target !== 'string') {
        return;
    }
    if (target.includes('bytecode')) {
        return 'bytecode';
    }
    if (target.includes('nativecode')) {
        return 'nativecode';
    }
}
function formatVaporRenderTarget(target) {
    return messages_1.M[`view.render.compiler.target.${target}`];
}
function getManifestVaporRenderTarget(manifest) {
    return normalizeVaporRenderTarget(manifest['uni-app-x']?.['vapor-render-target']);
}
function appendChangedFile(changedFiles, seenFiles, filename) {
    if (seenFiles.has(filename)) {
        return;
    }
    seenFiles.add(filename);
    changedFiles.push(filename);
}
function appendImporterFiles(changedFiles, seenFiles, bundle) {
    const importerMap = new Map();
    Object.keys(bundle).forEach((filename) => {
        const outputFile = bundle[filename];
        if (outputFile.type !== 'chunk') {
            return;
        }
        const imports = outputFile.imports.concat(outputFile.dynamicImports);
        imports.forEach((file) => {
            const importers = importerMap.get(file);
            if (importers) {
                importers.push(filename);
            }
            else {
                importerMap.set(file, [filename]);
            }
        });
    });
    for (let i = 0; i < changedFiles.length; i++) {
        const importers = importerMap.get(changedFiles[i]);
        if (!importers) {
            continue;
        }
        importers.forEach((filename) => {
            appendChangedFile(changedFiles, seenFiles, filename);
        });
    }
}
function uniStatsPlugin(options = {}) {
    let resolvedConfig;
    let isManifestChanged = false;
    const shouldTrackManifestChange = process.env.UNI_PLATFORM === 'app' ||
        process.env.UNI_PLATFORM === 'app-harmony';
    const shouldAppendImporterFiles = process.env.UNI_PLATFORM === 'app-harmony';
    let isVapor = shouldTrackManifestChange && process.env.UNI_APP_X_DOM2 === 'true';
    return {
        name: 'uni:app-stats',
        enforce: 'post',
        configResolved(config) {
            resolvedConfig = config;
            emittedHashMap.set(resolvedConfig, new Map());
        },
        watchChange(id) {
            if (shouldTrackManifestChange && id.endsWith('manifest.json')) {
                isManifestChanged = true;
                try {
                    const manifest = (0, json_1.parseJson)(fs_extra_1.default.readFileSync(id, 'utf-8'), true, 'manifest.json');
                    const uniAppX = manifest['uni-app-x'] || {};
                    const vaporRenderTarget = getManifestVaporRenderTarget(manifest);
                    const runtimeVaporRenderTarget = normalizeVaporRenderTarget(process.env.UNI_APP_X_VAPOR_RENDER_TARGET);
                    if (vaporRenderTarget &&
                        runtimeVaporRenderTarget &&
                        vaporRenderTarget !== runtimeVaporRenderTarget) {
                        console.warn(messages_1.M['dev.watching.vapor.render.target']
                            .replace('{manifestTarget}', formatVaporRenderTarget(vaporRenderTarget))
                            .replace('{runtimeTarget}', formatVaporRenderTarget(runtimeVaporRenderTarget)));
                    }
                    if (uniAppX.vapor !== isVapor) {
                        isVapor = uniAppX.vapor === true;
                        console.warn(messages_1.M['dev.watching.restart.vapor']);
                        // 主动退出，避免后续会打印正在编译中等日志
                        process.exit(0);
                    }
                }
                catch (e) { }
            }
        },
        writeBundle(_, bundle) {
            if (options.manifestOnly) {
                return;
            }
            if (resolvedConfig.isProduction) {
                // 仅dev生效
                return;
            }
            const emittedHash = emittedHashMap.get(resolvedConfig);
            const changedFiles = [];
            const seenFiles = new Set();
            Object.keys(bundle).forEach((filename) => {
                // 不处理sourcemap
                if (filename.endsWith('.map')) {
                    return;
                }
                const outputFile = bundle[filename];
                let outputFileHash = '';
                if (outputFile.type === 'asset') {
                    outputFileHash = (0, utils_1.hash)(outputFile.source);
                }
                else {
                    outputFileHash = (0, utils_1.hash)(outputFile.code);
                }
                if (emittedHash.get(filename) !== outputFileHash) {
                    emittedHash.set(filename, outputFileHash);
                    appendChangedFile(changedFiles, seenFiles, filename);
                }
            });
            if (shouldAppendImporterFiles) {
                appendImporterFiles(changedFiles, seenFiles, bundle);
            }
            if (isManifestChanged) {
                isManifestChanged = false;
                changedFiles.unshift('manifest.json');
            }
            process.env.UNI_APP_CHANGED_FILES = changedFiles.length
                ? JSON.stringify(changedFiles)
                : '';
        },
    };
}
exports.uniStatsPlugin = uniStatsPlugin;
