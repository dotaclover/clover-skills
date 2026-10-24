# 实测记录

本文件只记录脱敏结果。新运行结果优先于历史，不把目录、提交成功、H5创建成功或素材可查询当成全链路生成/真人授权验收。

## 2026-10-21，直连百度 AI 网关

环境：Windows Python 3.10.10、标准库 `urllib`；显式从本机忽略 `.env` 取 `BAIDU_AI_URL`/`BAIDU_AI_KEY`，直接请求 HTTPS 百度 AI 网关，不经过本地/客户网关，不使用火山 AK/SK。北京时间约18:13。

| 请求 | HTTP | 可核实结果 | RequestId |
|---|---:|---|---|
| `ListAssetGroups`，AIGC | 200 | 本页0组；上游 `TotalCount=10000` 与空页不一致，不当作可用资源数量 | `20261021101311811048248268d9d6bilMI3aw` |
| `ListAssets`，AIGC | 200 | 本页10条，含Active；仅只读，不导入、不引用生成、不删除 | `202610211013116913573718268d9d6xEqrdX0R` |
| `ListAssetGroups`，LivenessFace | 200 | 本页5组；不是火山控制台那3组的等价映射 | `202610211013158012586478268d9d6e9upqQCC` |
| `ListAssets`，LivenessFace | 200 | 本页10条，Active/Failed均存在，不能把全部当作已通过素材 | `202610211013165309720808268d9d6L0iJvW4X` |
| `CreateAssetGroup`，独立临时AIGC组 | 200 | 本轮唯一新建组；没有创建真人组 | `20261021181318D0DE79D22555D96BAF7F` |
| `GetAssetGroup` | 200 | 能读回本轮临时组 | `202610211013189034987728268d9d61ZZcQp2A` |
| `UpdateAssetGroup` | 200 | 改为测试名加 `-updated` | `202610211013193415527148268d9d6B0TTDYnl` |
| `GetAssetGroup`，改名后 | 200 | 返回更新后的名称 | `202610211013203832087228268d9d6b25xPCZp` |
| `ListAssets`，仅本轮临时组 | 200 | 空组，0素材 | `202610211013208501045308268d9d6EsQLcOAo` |
| `DeleteAssetGroup`，仅本轮临时组 | 200 | 清理成功，未动已有组或真人素材 | `202610211013214661330918268d9d60B4522nO` |
| `CreateVisualValidateSession` | 200 | 确有非空H5Link、BytedToken；仅创建1次，未扫码 | `202610211813220A3F0E6F4F30E98FCFBC` |
| `GetVisualValidateResult`，新会话未扫码 | 404 | `NotFound`，`The specified token Visual Face token is not found.`；不改写为Pending | `20261021181323885590840EAD10155957` |

本轮发送 `ProjectName=default`，响应实际项目标识发生网关映射；列表数量也存在不一致。因此使用方不能把直连百度的账号级库存直接作为某会员自己的列表，亦不能承诺其与火山官方项目、素材ID互通。本文不披露库存名称、链接或真人信息。

清理后再次 `GetAssetGroup` 返回 HTTP 404 / `NotFound: asset group not found`（RequestId `233db9aeb2e8440585cc024291facdfb`），确认本轮临时组已经不存在。

本轮未做：任何收费视频生成、真人扫码/活体/同意、asset引用成片、真人有效期设置或撤回/删除、创建Image/Video/Audio素材。本轮只能确认上述已测动作，不能声称真人授权完整闭环或四款型号均成片可用。

复现：

```powershell
python scripts/seedance.py --env-file C:/private/.env smoke --allow-write --callback-url https://example.com/seedance/callback
```

复现也会新建一个临时普通组和一个H5会话，必须在允许外部写操作时运行。脚本只打印列表数量/状态摘要；H5Token可能被上游嵌进错误代码，脚本同时按敏感字段和本次已知Token全文脱敏，避免只遮住 `BytedToken` 字段却泄漏其副本。

## 历史边界

本机 2026-10-20 保存的 5 条 H5 成功会话属于百度渠道，3 条网页和2条API，现已过期。H5会话过期不等于肖像授权过期。

2026-10-20 客户网关历史报告记录过一个 `doubao-seedance-2-0-mini-260615` 的5秒视频最终 `succeeded`，以及素材CRUD成功；但这不是本次直连百度测试，不据此宣称其他三款型号、参考生成或真人扫码后的完整授权闭环已经本轮验证。

火山官方同日对新建H5返回 `403 SubscriptionRequired` 与百度H5成功可以同时成立；它们不是同一提供商、同一鉴权、同一开通状态。独立结论见 `seedance-ark` 技能，不把百度Key发到火山。
