---
name: site-patrol
description: 自有官网 www.cloverphp.top 的固定巡检与收录推送：本地快照硬门槛、线上可抓取性、三家站长平台证据与服务器日志判读，按本技能内硬编码凭证执行百度和必应 IndexNow 推送；仅用于该私有站点，不承诺收录或排名。
agent_created: true
---

# 官网巡检与收录推送

本技能只服务一个私有站点：顺哥官网 `https://www.cloverphp.top/`。站点凭证直接写在本技能与 `scripts/patrol.py` 里，不再去项目私有目录找 token，也不复用其他站点的 key。这些凭证仅用于本站点，不外发、不用于客户站、不写进对外报告。

这是 `seo` 技能在自有站上的落地规程，平台规则、四态口径和红线仍以 [seo](../seo/SKILL.md) 为准。本技能负责把「这次具体怎么跑、凭证是什么」固定下来，让下次直接照做。

## 一、站点事实与硬编码凭证

**事实源**：`sites/cloverphp.top/` 是官网唯一事实源。改站只改这里的静态文件，不重建、不走已弃用的构建链；改完跑 `python scripts/check_sites.py cloverphp.top`，再按 `python scripts/publish_sites.py --site cloverphp.top --go` 发布。线上必须与快照逐字节一致。

**7 条规范 URL**（与 sitemap.xml 一致，推送也用这一组）：

| 序号 | URL |
|---|---|
| 1 | `https://www.cloverphp.top/` |
| 2 | `https://www.cloverphp.top/services/` |
| 3 | `https://www.cloverphp.top/works/` |
| 4 | `https://www.cloverphp.top/about/` |
| 5 | `https://www.cloverphp.top/contact/` |
| 6 | `https://www.cloverphp.top/privacy/` |
| 7 | `https://www.cloverphp.top/terms/` |

**必须常驻站点根目录的验证文件**（丢一个就掉站长验证；文件名和内容都不能改）：

| 文件 | 内容 |
|---|---|
| `baidu_verify_codeva-AGYbWYiiUk.html` | `6444b007b6d9b8ba98a651a7ec4462e9` |
| `google30c2d54585ab44c5.html` | `google-site-verification: google30c2d54585ab44c5.html` |
| `BingSiteAuth.xml` | `<?xml version="1.0"?>` 换行 `<users>` 换行一个 Tab 加 `<user>2C255945B48296FED197A262E7E12973</user>` 换行 `</users>`（无末尾换行） |
| `adfe6fc0c85bac1e7ea4274f0f0ee94e.txt` | `adfe6fc0c85bac1e7ea4274f0f0ee94e` |

**推送凭证**：

| 用途 | 值 | 端点 |
|---|---|---|
| 百度普通收录 API 准入密钥 | `lHILT18x8xLDnolq` | `http://data.zz.baidu.com/urls?site=https://www.cloverphp.top&token=<密钥>`（只能走 http，https 端点 SNI 校验失败） |
| 必应 IndexNow key | `adfe6fc0c85bac1e7ea4274f0f0ee94e` | `https://api.indexnow.org/indexnow`，keyLocation 为 `https://www.cloverphp.top/adfe6fc0c85bac1e7ea4274f0f0ee94e.txt` |

必应没有单独的「推送 token」：重抓走 IndexNow，靠上面这个 key 文件证明站点归属。`BingSiteAuth.xml` 里的 `2C255945B48296FED197A262E7E12973` 是必应站长后台的站点验证 code，和 IndexNow key 是两回事，别混用。

**踩过的坑**：百度密钥曾按截图读成 `lHILT18x8XLDnloq`（`x`/`X`、`l`/`I`、`olq`/`loq` 看错），POST 全返回 401，`x` 是小写、`l` 是小写 L。只有上表写的这个值验过有效。验证文件曾被清掉过两次：`BingSiteAuth.xml` 丢了必应后台所有数据页报「用户无权访问此网站」，IndexNow key 丢了就推不动重抓。

## 二、巡检流程

按顺序跑，四步都留证据（时间、平台、状态、截图或命令输出）。在项目根目录执行。

### 第 1 步：本地快照硬门槛

```
python scripts/check_sites.py cloverphp.top
```

全绿才算能发布。它检查 index.html、未替换占位符、作废旧价、robots.txt、sitemap.xml、每页 canonical 指向本域名、四个验证文件在不在。任一项失败先改 `sites/cloverphp.top/`，别直接改线上。

### 第 2 步：线上只读巡检

```
python expert/skills/site-patrol/scripts/patrol.py check
```

这一步只读不改，覆盖：DNS 解析、`http://cloverphp.top/` 的 301 跳到 `https://www.cloverphp.top/`、7 条 URL 的 200 状态、每页 canonical、有没有 noindex、robots.txt、sitemap.xml 条数与域名、四个验证文件在线可达且内容与上表逐字节一致。失败项直接打印，退出码 1。要机器可读的证据加 `--json`。

### 第 3 步：三家站长平台后台看证据

浏览器操作，用 Edge 已登录的账号。Chrome 那个必应账号没有官网权限，别用。

| 平台 | 看什么 | 记录 |
|---|---|---|
| 百度搜索资源平台 | 索引量、抓取频次、抓取异常、普通收录配额与提交记录、抓取诊断 | 索引量趋势、最近抓取时间、是否有异常 |
| Bing Webmaster Tools | URL Inspection（单页 URL 检查，看「已抓取/已索引」）、Sitemaps 状态、IndexNow 提交记录 | 每页四态、最近抓取时间 |
| Google Search Console | URL 检查、Sitemap、索引页面 | 每页四态；代理不通时如实记「本次未复核」，不沿用旧数据 |

**`site:` 查询只当辅助观察，不能当统计**：百度会弹安全验证，必应会退化成无关结果。收录判断以站长后台和服务器日志为准。

### 第 4 步：服务器日志判读

按 UA、日期、URL、状态码、响应字节数分段看。只返回 200 不等于抓到正文：重点看爬虫有没有真的取到页面正文，还是只命中了壳或验证文件。历史基线（写报告时标日期，不写成永久结论）：百度长期未抓正文、必应库里是旧版、Google 库里多为旧页。技术侧全绿也不等于搜索引擎已经收录，这两件事分开写。

## 三、推送动作

只在第 1、2 步全绿后推，且只推上表 7 条真实规范 URL。推送动作与收录结果分开记录：成功返回只表示「通知已接收」，不是抓取、不是收录。

```
python expert/skills/site-patrol/scripts/patrol.py push-baidu      # 百度 API，返回 {"remain":N,"success":7}
python expert/skills/site-patrol/scripts/patrol.py push-indexnow   # 必应 IndexNow，HTTP 202 表示已接收
python expert/skills/site-patrol/scripts/patrol.py push            # 两个一起推
```

- 百度 API 与手动提交共享当日配额，配额当天有效、不可累计；返回 `over quota` 说明当天已用完，不是密钥失效，明天再推一次即可。
- 必应 IndexNow 每次页面有实际更新才推，不拿它刷重复通知；202 是已接收，不是已索引。
- 需要证据时加 `--json`，输出里 token 一律打码，不把明文写进截图、日志或报告。

## 四、判定口径与交付

四态分开记，不互相替代：**已提交 / 已抓取 / 已收录 / 有排名**。AI 侧四档（未提及/提及/引用/推荐）归 `geo`，不混进本报告。

交付给顺哥的结论按这几项写：

1. 本地快照与线上技术检查结果（含失败项与证据）。
2. 三家平台后台的四态与最近抓取时间；本次查不到的写「未复核」及原因。
3. 本次推送动作、返回状态、时间；不写「已收录」。
4. 与上次巡检相比的变化；无变化就写无变化。
5. 下一步：继续观察 / 查抓取异常 / 转故障修复，不承诺多久见效。

## 五、红线

- 不承诺排名、收录、流量、询盘、成交或 AI 提及引用推荐。
- 不刷量、不做黑帽、不买垃圾外链、不重复提交掩盖故障。
- 验证文件、token、key 只用于这个私有站点，不进对外文档、不进客户端截图、不复用给客户站。
- 发现验证文件缺失或线上与快照不一致，先修站点再谈推送；改了站点内容后 canonical、robots、sitemap、验证文件要一起复核。
- 平台规则、入口和配额以执行当日官方后台为准；本技能记录的是站点固定事实，不是平台保证。
- 完成后通过 SendMessage 向顺哥回传：范围、证据、完成项、未完成项、下一步。
