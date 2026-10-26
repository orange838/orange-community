// 导出 glin-profanity 内置词库，供本地 FastAPI 后端（orange-backend/main.py）复用，
// 保证本地与线上 Worker 的敏感词过滤覆盖面一致。
//
// 用法（在 orange-worker 目录下）：
//   node scripts/export-profanity-words.mjs
//
// 升级 glin-profanity 后重跑本脚本即可；不要手改生成的 JSON。
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const workerRoot = path.resolve(here, "..");
const bundle = path.join(workerRoot, "node_modules/glin-profanity/dist/index.js");
const pkgFile = path.join(workerRoot, "node_modules/glin-profanity/package.json");
const target = path.resolve(workerRoot, "../orange-backend/profanity_words.json");

// 线上 Worker 里 ignoreWords 豁免的字，导出时同步剔除，保持两侧误伤范围一致。
const IGNORE = ["逼"];

function grabArray(source, name) {
  const anchor = source.indexOf(`${name} = {`);
  if (anchor < 0) throw new Error(`未找到词库定义：${name}`);
  let index = source.indexOf("[", anchor);
  let depth = 0;
  for (let i = index; i < source.length; i += 1) {
    const char = source[i];
    if (char === '"') {
      i += 1;
      while (i < source.length && source[i] !== '"') {
        if (source[i] === "\\") i += 1;
        i += 1;
      }
      continue;
    }
    if (char === "[") depth += 1;
    else if (char === "]") {
      depth -= 1;
      if (depth === 0) {
        index = i;
        break;
      }
    }
  }
  // 词库里含 \u{1F595} 这类 emoji 转义，JSON.parse 不接受，这里按 JS 字面量求值。
  return new Function(`return ${source.slice(source.indexOf("[", anchor), index + 1)}`)();
}

const source = fs.readFileSync(bundle, "utf8");
const version = JSON.parse(fs.readFileSync(pkgFile, "utf8")).version;
const en = [...new Set(grabArray(source, "english_default").map((w) => String(w).toLowerCase()))].sort();
const zh = [...new Set(grabArray(source, "chinese_default").map((w) => String(w)))].filter(
  (w) => !IGNORE.includes(w)
).sort();

const payload = {
  source: `glin-profanity ${version} defaults`,
  generatedAt: new Date().toISOString().slice(0, 10),
  note: "由 orange-worker/scripts/export-profanity-words.mjs 生成；升级依赖后重跑，不要手改",
  ignore: IGNORE,
  en,
  zh
};

fs.writeFileSync(target, JSON.stringify(payload));
console.log(`已导出 ${path.relative(workerRoot, target)}：english ${en.length} / chinese ${zh.length}`);
