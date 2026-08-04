# TS-04C 脚本

候选对象、调用方式和预算确认后补充校准轮及正式轮入口。脚本不得读取未记录的本机状态，也不得把密钥写入仓库。

单道完整题校准使用 `run_full_question.py` 发起一次已授权 DeepSeek Flash 请求，再运行 `node scripts/gate_full_question.js`。原始响应与候选结果分开保存；语义失败不得由本地渲染器静默修正。
