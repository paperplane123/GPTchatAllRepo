import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(scriptDir, "..");
const pluginName = "WPS_MAC_READER";
const pluginVersion = "0.1.0";
const pluginFolder = `${pluginName}_${pluginVersion}`;
const pluginRoot = join(projectRoot, "package", pluginFolder);

const requiredFiles = [
  "README.md",
  "install.sh",
  "uninstall.sh",
  "package.json",
  "package/publish.xml",
  `package/${pluginFolder}/ribbon.xml`,
  `package/${pluginFolder}/main.js`,
  `package/${pluginFolder}/reader.html`,
  `package/${pluginFolder}/reader.css`,
  `package/${pluginFolder}/reader.js`
];

const failures = [];

function fail(message) {
  failures.push(message);
}

function read(relativePath) {
  const path = join(projectRoot, relativePath);
  if (!existsSync(path)) {
    fail(`缺少文件：${relativePath}`);
    return "";
  }
  return readFileSync(path, "utf8");
}

for (const relativePath of requiredFiles) {
  if (!existsSync(join(projectRoot, relativePath))) {
    fail(`缺少文件：${relativePath}`);
  }
}

if (existsSync(join(pluginRoot, "index.html"))) {
  fail("插件目录不应包含 index.html；WPS 会自动生成并加载 main.js。")
}

const publishXml = read("package/publish.xml");
const ribbonXml = read(`package/${pluginFolder}/ribbon.xml`);
const mainJs = read(`package/${pluginFolder}/main.js`);
const readerHtml = read(`package/${pluginFolder}/reader.html`);

const expectedManifestFragments = [
  `name="${pluginName}"`,
  `version="${pluginVersion}"`,
  'type="wps"',
  'url="file://"'
];
for (const fragment of expectedManifestFragments) {
  if (!publishXml.includes(fragment)) {
    fail(`publish.xml 缺少：${fragment}`);
  }
}

if (!publishXml.includes("<jsplugins>") || !publishXml.includes("</jsplugins>")) {
  fail("publish.xml 缺少 jsplugins 根节点。")
}

if (!ribbonXml.includes("ViewFullScreenReadingView")) {
  fail("ribbon.xml 未引用原生阅读命令 ViewFullScreenReadingView。")
}

const callbackNames = [...ribbonXml.matchAll(/onAction="([A-Za-z_$][\w$]*)"/g)].map((match) => match[1]);
const onLoadMatch = ribbonXml.match(/onLoad="([A-Za-z_$][\w$]*)"/);
if (onLoadMatch) {
  callbackNames.push(onLoadMatch[1]);
}
for (const callbackName of new Set(callbackNames)) {
  const functionPattern = new RegExp(`function\\s+${callbackName}\\s*\\(`);
  const windowPattern = new RegExp(`window\\.${callbackName}\\s*=`);
  if (!functionPattern.test(mainJs) && !windowPattern.test(mainJs)) {
    fail(`ribbon.xml 回调 ${callbackName} 未在 main.js 中实现。`);
  }
}

for (const asset of ["reader.css", "reader.js"]) {
  if (!readerHtml.includes(asset)) {
    fail(`reader.html 未引用 ${asset}。`);
  }
}

function run(command, args, description) {
  const result = spawnSync(command, args, {
    cwd: projectRoot,
    encoding: "utf8"
  });
  if (result.status !== 0) {
    fail(`${description}失败：${(result.stderr || result.stdout || "未知错误").trim()}`);
  }
}

run(process.execPath, ["--check", join(pluginRoot, "main.js")], "main.js 语法校验");
run(process.execPath, ["--check", join(pluginRoot, "reader.js")], "reader.js 语法校验");
run("bash", ["-n", join(projectRoot, "install.sh")], "install.sh 语法校验");
run("bash", ["-n", join(projectRoot, "uninstall.sh")], "uninstall.sh 语法校验");

if (failures.length > 0) {
  console.error("WPS Mac 纯阅读加载项校验失败：");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log("WPS Mac 纯阅读加载项静态校验通过。")
