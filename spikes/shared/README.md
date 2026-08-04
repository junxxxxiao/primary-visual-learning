# 技术切片共享合同

`evidence_provenance.py` 提供跨切片知识来源门禁。上游用 `seal_knowledge_package` 为发布知识生成内容哈希；下游用 `validate_knowledge_provenance` 重新检查：

- 知识包必须存在于上游导出，且内容与包哈希完全一致；
- 来源清单哈希和来源文件哈希必须与当前文件一致；
- claim 的来源、页码和证据摘录必须能在声明的来源中定位；
- 任一失败必须发生在模型调用、展示、缓存或正式评测之前。

该门禁验证可追溯性和防篡改，不自动证明证据在学科语义上充分。`synthetic_fixture` 必须保持 `exploratory_only`；非 synthetic 包必须携带独立语义审核通过产物。真实产品知识仍需按来源等级和人工审核规则处理。

`candidate_evidence_gate.py` 提供跨切片候选授权与状态顺序门禁：

- `preflight`：manifest 的对象、版本、参数、预算、数据边界及输入哈希必须与当前仓库一致，且授权必须绑定当前 manifest 哈希；
- `candidate`：运行必须晚于授权，结果路径、结果哈希、时间和候选输入哈希必须与 manifest 一致；
- `release`：人工评审必须晚于候选完成，并绑定当前 manifest 与结果哈希；
- `discover`：扫描所有 `candidate_output`，缺少 manifest 的切片同样失败，不能通过不建清单绕过。

常用命令：

```bash
python3 spikes/shared/candidate_evidence_gate.py discover --repo-root . --stage preflight
python3 spikes/shared/candidate_evidence_gate.py discover --repo-root . --stage release
```

运行共享回归：

```bash
python3 -m unittest discover -s spikes/shared/tests -v
```
