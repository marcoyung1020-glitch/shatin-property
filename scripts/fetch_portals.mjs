// 喺 exec 環境執行：用 fetch_url 讀 28Hse / House730 屋苑頁（curl 會被 403 擋）
import fs from 'node:fs';
const DIR = '/home/user/workspace/shatin-property/data/portal';
const H28 = {"蔚景園":4109,"沙田中心":4086,"河畔花園":4107,"好運中心":4082,"偉華中心":4089,"花園城":4118,"希爾頓中心":4095,"富豪花園":4088,"沙田廣場":4099,"翠麗花園":4125,"田園閣":4115,"沙田第一城":4080,"碧濤花園":4085,"翠湖花園":4087,"濱景花園":4090};
const H730 = {"蔚景園":25940,"沙田中心":26026,"河畔花園":25964,"好運中心":26025,"偉華中心":25942,"花園城":25949,"希爾頓中心":25941,"富豪花園":25965,"沙田廣場":25943,"翠麗花園":26029,"田園閣":25947,"沙田第一城":25999,"碧濤花園":25934,"翠湖花園":25931,"濱景花園":25930};
const jobs = [];
for (const [n, id] of Object.entries(H28)) jobs.push([`h28_${n}`, `https://www.28hse.com/buy/a3/dg44/c${id}`]);
for (const [n, id] of Object.entries(H730)) jobs.push([`h730_${n}`, `https://www.house730.com/buy/e${id}/`]);
const res = await Promise.all(jobs.map(async ([f, url]) => {
  for (let i = 0; i < 2; i++) {
    try {
      const r = await tools.fetch_url({ url, cache_enabled: false, max_length: 200000 });
      const c = (r.pages && r.pages[0] && r.pages[0].content) || r.content || '';
      if (c.length > 2000) { fs.writeFileSync(`${DIR}/${f}.md`, c); return [f, c.length]; }
    } catch (e) {}
  }
  return [f, 'FAIL'];
}));
text(res.map(r => r.join(':')).join(' '));
