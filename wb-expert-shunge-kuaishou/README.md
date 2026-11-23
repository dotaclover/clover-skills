# 快手运营顺哥

`shunge-kuaishou` · Agent 型专家包 · v1.0.0

按老铁语境写快手脚本：选题、钩子、时间轴、口播稿、封面与违禁词体检，并回看数据调整下一条。

## 结构

```
wb-expert-shunge-kuaishou/
├── .codebuddy-plugin/plugin.json
├── agents/shunge-kuaishou.md
├── avatars/
├── skills/
└── README.md
```

## 内置技能

- `wb-skill-kuaishou-copy`
- `copy-proof`

## 边界

- 只做本专家范围内的事，跨领域交给对应专家。
- 不接管账号、不代发布、不承诺流量与排名；账号操作与发布单独授权。
- 不含任何客户资料、账号数据、密钥或个人经历；产物中的事实须来自用户授权资料。
