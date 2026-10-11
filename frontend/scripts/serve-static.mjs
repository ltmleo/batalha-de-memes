// Preview local do build exportado com o mesmo prefixo do GitHub Pages:
//
//   node scripts/serve-static.mjs out 8138 /batalha-de-memes
//
// Depois abra http://localhost:8138/batalha-de-memes/ — a estrutura de URL
// (todos os links/assets) fica idêntica à publicada no Pages.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.argv[2] || "out");
const port = Number(process.argv[3] || 8138);
const prefix = process.argv[4] || "";

const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript",
  ".css": "text/css",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".json": "application/json",
};

http
  .createServer((req, res) => {
    let p = decodeURIComponent((req.url || "/").split("?")[0]);
    if (prefix && p.startsWith(prefix)) p = p.slice(prefix.length) || "/";
    if (p === "/") p = "/index.html";
    let file = path.join(root, p);
    // Export estático do Next: URL limpa -> arquivo index.html (trailing slash)
    if (!fs.existsSync(file) || !fs.statSync(file).isFile()) {
      if (fs.existsSync(file) && fs.statSync(file).isDirectory()) {
        file = path.join(file, "index.html");
      } else if (fs.existsSync(file + ".html")) {
        file = file + ".html";
      } else if (fs.existsSync(file + "/index.html")) {
        file = path.join(file, "index.html");
      }
    }
    fs.readFile(file, (err, data) => {
      if (err) {
        res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
        return res.end("not found");
      }
      res.writeHead(200, {
        "Content-Type": types[path.extname(file)] || "application/octet-stream",
      });
      res.end(data);
    });
  })
  .listen(port, () => console.log(`servindo ${root} em :${port} (prefixo "${prefix || "/"}")`));