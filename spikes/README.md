# 技术切片工作区

技术切片用于回答单一可行性问题，不直接承担生产架构。

总计划见 [技术可行性验证与切片准备](../docs/technical/2026-07-17-primary-visual-tutor-technical-validation.md)。

## P0 推荐顺序

1. `TS-00` 微信 / H5 运行时能力；
2. `TS-03` 受控讲解规划；
3. `TS-04` 视觉场景 DSL 与安全运行时；
4. `TS-05` 追问、快照和主题恢复；
5. `TS-01` 输入管线；
6. `TS-02` 知识与诊断；
7. `TS-06` 渐进生成和降级；
8. `TS-07` 统一播放与同步；
9. `TS-08` 事件流和回放。

## 创建新切片

复制 `_template/`，目录命名示例：

```text
spikes/ts-04-scene-runtime/
```

切片至少包含：

- `README.md`
- `fixtures/`
- `schemas/`
- `src/` 或 `scripts/`
- `results/summary.json`
- `decisions.md`

只有实际需要时再创建子目录。结果必须记录环境、夹具版本、指标、失败样例、成本和结论。

## 数据边界

- 默认使用 `shared/fixtures/` 中的合成夹具；
- 真实儿童样本不得提交 Git；
- 原始媒体只存放在批准的安全位置；
- 仓库中仅记录去标识化结果、哈希和访问说明；
- 密钥通过本地环境变量注入。
