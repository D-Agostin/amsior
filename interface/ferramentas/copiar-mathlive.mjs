// Copia as fontes e os sons do MathLive para public/, de onde o aplicativo os
// serve sem internet (o MathLive buscaria em CDN por padrão).
import { cpSync, mkdirSync } from "node:fs";
const origem = "node_modules/mathlive";
mkdirSync("public/mathlive", { recursive: true });
cpSync(`${origem}/fonts`, "public/mathlive/fonts", { recursive: true });
cpSync(`${origem}/sounds`, "public/mathlive/sounds", { recursive: true });
console.log("MathLive: fontes e sons copiados para public/mathlive");
