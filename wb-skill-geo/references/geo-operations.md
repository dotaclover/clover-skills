# GEO操作参考：可达性、可抽取改造与索引提交

> 所有平台对应关系与权重说法标注证据级别（A官方/B自测/C第三方/D传闻）。**D级不得写入交付报告**。

## 1. AI爬虫与UA清单

放行判断需核对实际来源、官方当前UA说明和用户的训练/索引政策。下表仅为待核对的候选清单；UA归属、用途及平台召回对应关系的来源待核实，不作为决策/效果承诺依据，表中“必须放行”等建议不能替代用户授权。仅伪装UA的curl探测不能证明真实爬虫可达，不得据此放宽安全防护。

| 爬虫UA | 归属 | 用途 | 处理建议 |
|---|---|---|---|
| `Baiduspider` | 百度 | 网页索引（文心/百度AI搜索的召回基础） | 必须放行 |
| `Bytespider` | 字节 | 头条搜索与字节内容池（豆包联网的召回来源之一） | 必须放行 |
| `Sogou web spider` | 搜狗 | 搜狗索引 | 放行（部分腾讯系产品复用） |
| `bingbot` | 微软 | Bing索引 | 放行 |
| `Googlebot` | Google | 网页索引（AI概览的召回基础） | 放行 |
| `OAI-SearchBot` | OpenAI | ChatGPT搜索的索引抓取 | 放行（客户要求海外可见时） |
| `ChatGPT-User` | OpenAI | 用户触发式即时访问 | 放行 |
| `GPTBot` | OpenAI | 训练用途 | 客户决策，可单独封 |
| `ClaudeBot` | Anthropic | 抓取（含训练） | 放行或按客户决策 |
| `Claude-SearchBot` / `Claude-User` | Anthropic | 搜索与用户触发 | 放行 |
| `PerplexityBot` | Perplexity | 索引抓取 | 放行（客户要求时） |
| `Google-Extended` | Google | Gemini训练/grounding控制开关，**不控制Googlebot抓取** | 客户决策，不影响AI概览 |
| `DeepSeekBot` | 深度求索 | 联网检索抓取 | 放行（客户要求时） |
| `MoonshotAI` / `Kimi` 类UA | 月之暗面 | 联网检索 | 以官方文档为准，先观察日志再决定 |

两条必须讲清的判断：

1. **封训练不等于封搜索，封搜索也不等于保护内容**。训练型（`GPTBot`、`Google-Extended`）与检索型（`OAI-SearchBot`、`Baiduspider`、`Bytespider`）是不同开关，客户要“不让AI白用我的内容”时先问清是要退出训练还是退出答案。
2. **中文场景里最有确定性的两个入口是百度与字节**：前者有站长平台可提交、有后台可验证；后者有头条搜索站长平台可提交。其余国内AI产品多为复用索引或自建池，无可提交入口，只能靠robots放行、内容结构和站外提及。

## 2. robots.txt 写法

```txt
# 检索型：放行
User-agent: Baiduspider
Allow: /

User-agent: Bytespider
Allow: /

User-agent: bingbot
Allow: /

User-agent: Googlebot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: DeepSeekBot
Allow: /

# 训练型：客户明确要求退出训练时启用（不影响检索型）
User-agent: GPTBot
Disallow: /

User-agent: Google-Extended
Disallow: /

Sitemap: https://<域名>/sitemap.xml
```

写完后必须实测：`curl -A "<UA>"` 看返回是否为200而非403，且页面正文可取。**robots只管守规矩的爬虫，被WAF拦在TCP层时robots无效。**

## 3. 拦截排查（宝塔/nginx/CDN）

按顺序查，不要猜：

```bash
# 1. 服务器是否直接拒绝该UA（403/444/521）
curl -sS -o /dev/null -w "%{http_code}\n" -A "Bytespider" https://<域名>/

# 2. nginx 是否命中UA规则
grep -rn "Bytespider\|Baiduspider\|user_agent\|deny" /www/server/panel/vhost/nginx/<域名>.conf /www/server/nginx/conf/ 2>/dev/null

# 3. 访问日志里AI爬虫到底来没来
grep -iE "baiduspider|bytespider|bingbot|googlebot|oai-searchbot|claudebot|deepseekbot" \
  /www/wwwlogs/<域名>.log | tail -20

# 4. 是否被频率限制/防火墙拦（宝塔：安全→防火墙 / nginx限速模块）
grep -rn "limit_req\|limit_conn" /www/server/panel/vhost/nginx/<域名>.conf 2>/dev/null
```

常见误判：

- **日志没有记录≠没被抓**：可能被CDN前置节点挡掉，要看CDN日志。
- **403不等于robots封禁**：403是服务器拒绝，robots封禁的表现为抓取但不索引。
- **错误页跳转依赖实际配置**：`error_page`内部跳转本身不必然变301/302，还需检查重写与HTTPS规则；测试可达性使用真实路径。
- **验证文件跳转**：先按平台要求实测真实验证URL；仅当需要且获准时增加精确HTTP例外，不默认让`llms.txt`或整类路径绕过HTTPS（见`ops-deploy/references/hosts.md`）。

## 4. 只读可达性基线命令

```bash
SITE="https://<域名>"

# 状态与跳转
curl -sS -o /dev/null -w "%{http_code} %{redirect_url}\n" -L "$SITE/"

# 正文是否在源码里（GEO第一道门槛）
curl -sS -L --max-time 20 "$SITE/" | grep -oE "<h1[^>]*>[^<]{2,80}" | head -3
curl -sS -L --max-time 20 "$SITE/" | sed -e 's/<[^>]*>//g' | tr -s ' \n' ' \n' | head -40

# robots 与 sitemap
curl -sS -L "$SITE/robots.txt" | head -40
curl -sS -o /dev/null -w "%{http_code}\n" "$SITE/sitemap.xml"

# 结构化数据是否存在且与正文一致
curl -sS -L "$SITE/" | grep -o 'application/ld+json' | wc -l

# 各AI UA实测（用真实路径，不要用随机文件）
for ua in Baiduspider Bytespider bingbot Googlebot OAI-SearchBot Claude-SearchBot DeepSeekBot; do
  printf "%-18s %s\n" "$ua" "$(curl -sS -o /dev/null -w '%{http_code}' -A "$ua" -L "$SITE/")"
done
```

Windows下用`curl.exe`。以上全部只读，不写文件、不改配置。

## 5. 内容可抽取改造规范

### 段落级写法（RAG切片后仍要能读懂）

> 下面仅为结构示范，方括号字段必须来自用户确认的事实卡，缺项不编写；范围、报价和响应口径不从技能内置。

```markdown
## [真实服务区域]WordPress网站出现故障如何处理？

[主体全称]在[实际服务区域]提供[已确认的诊断与修复范围]，费用按[当前合同口径]，
首次响应按[双方确认的服务窗口]；超范围工作先评估并取得确认。
（[实际更新日期]更新）

- 包含：[合同列明的检查和修复动作]
- 不含：[合同列明的排除项]
- 适用：[已确认的客户与站点类型]
```

要点：

1. H2写成用户会问的原话，不是“服务优势”。
2. 首段一句话给全结论：**主体+地点+价格+时间+范围**。
3. 列表把“含什么/不含什么/适用谁”拆开，方便被整段摘走。
4. 段落内出现品牌名要写全称，不用“我们”指代（切片后“我们”没有指代对象）。
5. 结尾一行为更新时间，且在页面可见；`lastmod`只写真实更新日。

### 事实卡模板（页面改造的唯一事实来源）

```markdown
# 事实卡（客户确认版）

- 主体全称：
- 品牌简称（对外统一写法）：
- 一句话介绍（30字内，可被直接引用）：
- 服务区域（精确到区/街道，不写“全国”）：
- 价格口径（含单位与起价条件）：
- 服务时长与响应时效：
- 联系方式（对外唯一号码/邮箱）：
- 营业/服务时间：
- 不做什么（明确排除项）：
- 客户确认日期与方式：
```

官网页面与JSON-LD只允许使用事实卡字段。**事实卡没有的，不写。**

### 结构化数据

允许标记：`Organization`/`LocalBusiness`、`Service`、`FAQPage`、`BreadcrumbList`、`Article`。

三条硬约束：

- 只标页面可见内容，FAQ的问答必须在正文里能看到。
- 价格、地址、电话与事实卡逐字一致，不写区间套话。
- 不用`AggregateRating`编造评分，不用`Review`写自评。

## 6. llms.txt 的正确定位

**结论：可选、低成本、不承诺。** 下表保留历史研究线索供后续核对；精确时间、样本量、百分比和平台支持结论均为**来源待核实，不作为决策/效果承诺依据**。本轮未联网验证，不将其标为已证实研究结论。

| 研究 | 样本 | 结论 |
|---|---|---|
| Ahrefs（2026-06） | 约13.7万域名 | 97%的`llms.txt`在观察月内零请求；有请求的多为SEO审计工具 |
| SE Ranking（2025-11） | 约30万域名 | 是否发布`llms.txt`与AI引用无统计相关 |
| Google官方（2025-07） | — | 明确表示不支持，也无计划支持 |

`llms.txt`可作为文档目录供支持它的代理或索引服务使用；具体产品是否读取、搜索是否使用须按官方说明或访问日志核实，不能断言所有AI搜索不读取。因此：

- 有开发者文档、API文档的站，可以顺手加一份，作为“给读文档的代理看的目录”。
- 普通企业站、门店站，**不加也不影响任何GEO动作**，不要把它写进交付清单冒充成果。
- 任何情况下不得对外宣称“加了llms.txt就能被AI引用”。

如需发布，控制在20—50行、只列10—30个高价值页、链接用正式URL：

```markdown
# <品牌名>

> 一句话说明这是什么站、服务谁、覆盖哪里。

## 核心页面
- [服务与价格](https://<域名>/services)：服务项目、价格口径与不包含项
- [服务区域](https://<域名>/areas)：覆盖区域与上门条件
- [关于与资质](https://<域名>/about)：主体信息、联系方式、更新时间

## 常见问题
- [FAQ](https://<域名>/faq)：价格、时效、流程的原话问答
```

## 7. 平台对应关系（C级证据，标注口径）

下表仅用于理解实测中的引用来源，不作为站外内容建设任务或交付项，**不作为权重承诺**。所有关系都可能静默变化，使用前以当期实测为准。

| AI产品 | 主要召回来源（我的判断） | 可提交的官方入口 | 建设重点 |
|---|---|---|---|
| 百度AI搜索 / 文心 | 百度网页索引 | 百度搜索资源平台 | 官网收录 + 百家号/百科同口径 |
| 豆包 | 字节内容池（头条/抖音）+ 网页索引 | 头条搜索站长平台 | 头条号/抖音内容 + 官网可抓 |
| 腾讯元宝 | 搜狗索引 + 微信生态 | 搜狗站长平台（微信侧无提交入口） | 公众号/视频号 + 官网 |
| Kimi | 外部搜索为主，官网权重较高 | 无 | 官网事实页 + 媒体提及 |
| DeepSeek | 外部搜索为主 | 无 | robots放行 + 门户/媒体同口径 |
| 通义 / 夸克 | 夸克搜索索引 | 夸克/阿里站长相关入口（以实际为准） | 官网收录 + 权威媒体 |
| Google AI概览 | Google网页索引 | Search Console | 同SEO，无需额外入口 |
| ChatGPT搜索 | 自有索引（`OAI-SearchBot`） | 无提交入口 | robots放行 + 内容可抽取 |

平台范围、采样量和新增平台费用均以当前project brief、合同及验收清单为准，不默认百度/豆包或免费增加平台。

## 8. 索引提交清单

| 平台 | 动作 | 账号归属 |
|---|---|---|
| 百度搜索资源平台 | Sitemap/单URL提交 | 按客户授权与平台移交规则执行 |
| 头条搜索站长平台 | Sitemap/单URL提交 | 按客户授权与平台移交规则执行 |

执行时复核入口并记录日期；提交网站页面不等于发布平台文章，也不等于收录或AI引用。

## 9. 严重度分级

| 级别 | 判断 | 例子 | 处理 |
|---|---|---|---|
| P0 | 完全不可达 | WAF拦AI UA、全站5xx、robots封`/` | 先修，GEO暂停 |
| P1 | 抓到读不懂 | 空壳HTML、正文全在JS里、段落无主体无地点 | 一次性优先修 |
| P2 | 读了不敢引 | 价格口径矛盾、事实卡字段各页不一致、无更新时间 | 排期修正 |
| P3 | 页面信息不足 | 无FAQ、无问题集覆盖 | 在本次页面范围内补足，超范围交主理人确认 |

## 10. 常见误判清单

- 把“AI答出了官网信息”当成引用——没有来源标注不能确认来源，既不能认定引用也不能断言来自模型旧知识。
- 把“换了浏览器/换了账号答案变了”当成优化有效——先排除个性化。
- 把“平台收录了页面”当成“AI会引用”——中间还隔着切片与选源。
- 把“一次提问里出现品牌”写成“AI推荐我们”——提及≠推荐。
- 拿服务商文章里的权重百分比当优化依据——D级证据。
- 认为`llms.txt`或`schema`能直接换来引用——均不是引用开关，`llms.txt`不是必要条件。
