# 中低保真可点击原型

当前原型覆盖儿童学习闭环、可打断视觉讲解、主题分支与恢复、儿童探索历史，以及轻量家长工作台。

## 运行

在仓库根目录执行：

```bash
python3 -m http.server 4173 --directory prototype
```

打开 <http://127.0.0.1:4173/>。

若静态服务的目录是仓库根目录，则改用 <http://127.0.0.1:4173/prototype/>。

## 文件

- `index.html`：原型外壳和研究导航；
- `styles.css`：中低保真视觉系统、响应式布局和动画；
- `app.js`：固定夹具、状态和完整交互；
- `artifacts/`：阶段性原型审阅截图，不一定反映最新页面。

## 直达状态

- `?screen=home`
- `?screen=askPhoto`
- `?screen=askVoice`
- `?screen=confirm`
- `?screen=explore`
- `?screen=explore&branch=true`
- `?screen=explore&interrupt=true`
- `?screen=parentRecords`
- `?screen=home&viewport=mobile`

## 研究界面

- 左侧画板导航不属于产品；
- 顶部平板 / 手机切换不属于产品；
- 固定等待时间不代表真实性能；
- 截图标注和研究标记不属于产品。

## 固定教学夹具

- 问题：用力拨琴弦，声音会更高吗？
- 原场景修改：轻拨、用力拨、慢放；
- 关联主题：如果没有空气呢？
- 迁移：更用力敲同一个音叉；
- 家长样例：声音、分数、光影、乘法和植物。

## 修改规则

1. 交互变化应先确认是否影响 PRD；
2. 修改 `app.js` 后至少执行 `node --check prototype/app.js`；
3. 响应式变化应人工检查平板和手机；
4. 更新原型后同步 [原型规范](../docs/design/2026-07-17-low-mid-fidelity-prototype-spec.md)；
5. 不把真实 API、儿童数据或生产密钥接入本目录。

原型是研究工具，不应直接演变为生产应用。真实实现应在 P0 技术切片完成后进入 `apps/` 和 `packages/`。
