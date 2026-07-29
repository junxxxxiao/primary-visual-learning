# 技术切片工作区

技术切片用于回答单一可行性问题，不直接承担生产架构。

总计划见 [技术验证 v3](../docs/technical/2026-07-28-primary-visual-tutor-technical-validation-v3.md)。

## P0 推荐顺序

1. `TS-00` H5 核心运行时与微信入口；
2. `TS-02` 教材解析、AI 核验与临时知识包；
3. `TS-04A` 生成视觉代码沙箱；
4. `TS-04B` 教学正确性、布局契约与视觉缓存；
5. `TS-03` 双学段渐进讲解与迁移规划；
6. `TS-04C` 真实生成视觉表现与讲解一致性；
7. `TS-07` 统一播放时间轴；
8. `TS-05` 追问、进度拖动与现场恢复；
9. `TS-06` 渐进生成、延迟与硬降级。

`TS-02` 与 `TS-04A` 可并行准备，但正式判定依赖仍按上述顺序。`TS-04C` 同时依赖 `TS-03` 的完整讲解计划、`TS-04A` 的安全执行边界和 `TS-04B` 的教学/布局门禁；`TS-05` 依赖 `TS-07` 的统一真实时间轴。`StageTiming` 最小 trace 能力从所有 P0 切片开始使用，TS-12 再完成负载、成本和故障恢复验证。TS-01、TS-08 至 TS-12 在公开儿童内测前完成。

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

只有实际需要时再创建子目录。结果必须记录环境、夹具版本、指标、失败样例、成本和结论，并使用 `shared/schemas/stage-timing.schema.json` 记录本切片负责的局部 span。

## 数据边界

- 默认使用 `shared/fixtures/` 中的合成夹具；
- 真实儿童样本不得提交 Git；
- 原始媒体只存放在批准的安全位置；
- 仓库中仅记录去标识化结果、哈希和访问说明；
- 密钥通过本地环境变量注入。
