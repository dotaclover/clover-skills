# 小红书运营顺哥

`shunge-xhs` · Agent 型专家包 · v1.0.0

从小红书选题、标题、正文、封面到发布前体检，按账号卡产出可直接发布的图文笔记，并诊断旧笔记、回复评论。

## 结构

```
wb-expert-shunge-xhs/
├── .codebuddy-plugin/plugin.json
├── agents/shunge-xhs.md
├── avatars/
├── skills/
└── README.md
```

## 内置技能

- `wb-skill-xhs-copy`
- `copy-proof`

## 边界

- 只做本专家范围内的事，跨领域交给对应专家。
- 不接管账号、不代发布、不承诺流量与排名；账号操作与发布单独授权。
- 不含任何客户资料、账号数据、密钥或个人经历；产物中的事实须来自用户授权资料。
