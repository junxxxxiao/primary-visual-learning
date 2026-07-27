# 声音高保真价值 Demo 与研究原型

默认入口是以最新高保真页面为基底的固定声音价值 Demo。它覆盖公开说明、问题输入、词义校准、预测、互动讲解、琴弦实验、语音追问、关联主题、迁移验证、反馈和结果。旧中低保真研究原型保留在 `legacy.html`，仅供逻辑与历史对照，不再作为默认公开入口。

公开地址：<https://junxxxxiao.github.io/primary-visual-learning/>。旧中低保真研究原型地址：<https://junxxxxiao.github.io/primary-visual-learning/legacy.html>。

## 运行

在仓库根目录执行：

```bash
python3 -m http.server 4173 --directory prototype
```

打开 <http://127.0.0.1:4173/>。

默认链路：`公开入口 → 发起提问 → 旁白确认问题 → 词义校准 → 旁白引导预测 → 居中引入 → 三段自动连播讲解 → 发送文字或在当前画布模拟语音转写 → 真空关联讲解 → 连接旁白 → 返回原主题 → 可选动手实验 → 音叉迁移 → 必要时木琴迁移 → 结果 → 问卷`。发起提问页默认填入固定问题但可真实编辑；拍照和语音按钮只展示入口体感，不会申请相机或麦克风权限，也不会上传媒体。讲解播放器在相关页面统一提供播放 / 暂停、真实进度、三段切换与拖动定位；字幕按当前音频逐句同步。主题 Tab 按进度解锁，出现后可自由切换；手机端超出可用宽度时使用横向滑动轨道，不能覆盖品牌或标题。手机端讲解标题右侧固定使用两行工具区：字幕开关在第一行，自动播放进度或当前状态在第二行；平板端字幕仍保留在顶部应用栏，两端复用同一个控件和状态。最后一段动画结束后冻结最终帧，过渡旁白结束才跳转。核心“琴弦振动”讲解播放完即可进入迁移，动手实验不是门禁。

若静态服务的目录是仓库根目录，则改用 <http://127.0.0.1:4173/prototype/>。

## 文件

- `index.html`：默认入口，转到高保真体验；
- `sound-demo.html`：当前高保真 UI 与完整固定交互；
- `legacy.html`、`styles.css`、`app.js`：旧中低保真研究原型，仅供对照；
- `config.js`：公开 Demo 的本地问卷配置；
- `assets/audio/`：预生成固定音频，不依赖浏览器实时朗读；
- `scripts/generate-fixture-audio.mjs`：可复现的音调、响度和拨弦声音生成脚本；
- `scripts/narration-content.json`：千问 TTS 使用的固定讲稿、音色和说话风格；
- `scripts/generate-qwen-narration.py`：使用千问 TTS 预生成并下载固定旁白；
- `scripts/generate-narration-audio.sh`：无 API 时使用 macOS 系统音色的离线回退；
- `artifacts/`：阶段性原型审阅截图，不一定反映最新页面。

## 问卷配置

编辑 `config.js` 中唯一的配置项：

```js
window.SOUND_DEMO_CONFIG = {
  SURVEY_URL: 'https://example.com/survey'
};
```

保持空字符串时，结果页点击问卷按钮会显示“问卷链接尚未开放”。配置为有效 HTTPS 地址后，按钮会在当前浏览器中打开该地址。仓库不保存群二维码、家长联系方式或真实问卷答案。

## 千问 TTS 配置

千问只用于开发时预生成固定旁白，不在浏览器中调用。网页仍播放 `assets/audio/narration-*.wav`，因此体验者不会接触 API Key，也不会在每次打开 Demo 时产生调用。

首次使用：

```bash
python3 -m venv .venv-tts
source .venv-tts/bin/activate
python3 -m pip install -r prototype/scripts/requirements-tts.txt
cp prototype/.env.example prototype/.env
```

然后只在本机编辑 `prototype/.env`：

```dotenv
DASHSCOPE_API_KEY=你的真实Key
```

`.env` 已被仓库忽略，不要把 Key 写入 `app.js`、`config.js`、README、命令参数或提交记录。配置完成后先检查清单，再生成全部旁白：

```bash
python3 prototype/scripts/generate-qwen-narration.py --dry-run
python3 prototype/scripts/generate-qwen-narration.py
```

调试时可以只生成一段，避免重复费用：

```bash
python3 prototype/scripts/generate-qwen-narration.py --only main-2
```

同一配置需要比较多个随机韵律版本时，使用独立后缀，避免覆盖当前 Demo 音频：

```bash
python3 prototype/scripts/generate-qwen-narration.py --only main-1 --include-approved --output-suffix candidate-2
```

批量更新时先生成独立版本，全部验证通过后再提升为 Demo 当前音频。清单中已有 `approved_file` 的片段默认跳过，避免覆盖已确认版本：

```bash
python3 prototype/scripts/generate-qwen-narration.py --output-suffix qwen-standard-1
python3 prototype/scripts/generate-qwen-narration.py --promote-suffix qwen-standard-1
```

脚本默认使用 `qwen3-tts-instruct-flash`、`Cherry` 和面向小学三四年级的自然年轻女老师风格。返回的临时音频会立即下载并统一转换为 44.1 kHz、16-bit、单声道 WAV；脚本只输出片段名和本地路径，不打印 API Key、完整响应或带签名的音频 URL。

## 直达状态

- `?screen=entry`
- `?screen=ask`
- `?screen=confirm`
- `?screen=calibration`
- `?screen=prediction`
- `?screen=loading`
- `?screen=intro`
- `?screen=lesson`
- `?screen=experiment`
- `?screen=vacuum`
- `?screen=fork`
- `?screen=xylophone`
- `?screen=feedback`
- `?screen=result`
- 在任意直达参数后增加 `&viewport=phone`，使用固定 `390 × 844` 手机审阅画布；
- 增加 `&viewport=tablet`，使用固定平板审阅画布；
- 不传 `viewport` 时按真实浏览器窗口自适应。

## 研究边界

- `viewport` 参数只用于稳定审阅，不是面向体验者的设备开关；
- 固定等待时间不代表真实性能；
- 截图标注和研究标记不属于产品。

## 固定教学夹具

- 问题：更用力拨同一根弦，音调会更高吗？
- 提问入口：文字、拍照、语音三种入口共享同一个固定问题；点击只产生明确的演示反馈；
- 问题确认：根据文字、照片、语音入口播放对应的固定确认旁白，不用语音话术代替文字或照片反馈；
- 词义校准：响度是听起来有多响，音调是听起来有多高；响度示例使用一轻一响的明显对比；
- 语音引导：进入词义校准和讲解问题引入页时自动播放固定旁白，并可手动重听；
- 讲解准备：进度条单次完成后自动进入问题引入页，不需要点击“进入讲解”；
- 原场景修改：讲解结束后可选轻拨、用力拨和慢放；
- 关联主题：如果没有空气呢？
- 追问输入框：琴弦主题预置“如果没有空气呢？”并允许修改，发送箭头提交输入框当前内容，在当前对话中进入第二个延伸主题；麦克风是独立的模拟语音转写路径，叉号取消，对勾直接提交当前转写；
- 对话连续性：追问提交后进入真空主题时抽屉保持收起；已发送的问题和小知回答同步保存在 S07–S11 的对话记录中，切换主题、进入实验或返回原子片段后仍可重新打开查看；
- 打断恢复：提交追问时内部只保存被打断的子片段，不记录具体时间；真空主题三段播放完先播放主题连接语，再从原子片段开头继续。儿童端不显示锚点、恢复位置或内部保存状态；
- 子片段节奏：自动连播、手动点选、上一段/下一段、进入真空主题和返回琴弦主题时，新画面均先停留 1 秒再自动播放旁白；
- 进度拖动：松开当前子片段的进度条后，从新位置自动继续播放，并同步恢复文字、图解和场景状态；
- 手机小知挂件：S07–S11 共用同一收起挂件、抽屉外壳与蒙层；收起时头像、提示气泡和点击区域完全一致。抽屉左右贴边、右上角可关闭，展开时以黑色半透明蒙层覆盖背景且不重排画布，录音卡下方始终保留可编辑输入框；
- 音画同步：讲解节点按逐句旁白时间点出现，不按元素数量平均分配；概念因果箭头在结论出现前完成，字幕与当前播放语句同步；
- 动画响应式构图：讲解动画在平板采用适合横向因果关系的构图，在手机重新组织为纵向信息流；主体需合理占用画布，不得过空、拥挤、遮挡或裁切；
- 手机浏览器宿主：普通浏览器 / WebView 已经处理状态栏和顶部工具栏，Demo 页面内不再重复预留顶部安全区；底部仍保留触控安全距离；
- 讲解视觉：振幅/响度使用绿色，频率/音调使用蓝色，条件变化使用黄色；文字和图解分区呈现，不互相覆盖；
- 手机一屏与小屏降级：常规手机上核心讲解、实验区、三段导航和播放控制在单屏内完整显示；小知挂件与实验页迁移按钮始终锚定在可视区域且不参与画布内容排版，迁移按钮水平居中。可视高度不足时只允许演示画布内部纵向滚动，页面标题、固定操作和挂件不得被带走；画布内容不得横向溢出或越过画布边界；
- Demo 边界：讲解页返回公开体验入口，不进入旧儿童主页；加载页不展示研究用失败状态入口；
- 迁移：更用力敲同一个音叉，结论与原因拆成两个独立单选问题；两题均选择后才可提交；
- 提示后迁移：同一块木琴音条分别判断响度、音调和原因；
- 家长样例：声音、分数、光影、乘法和植物。

## 验证

修改后至少执行：

```bash
node --check prototype/app.js
node prototype/scripts/generate-fixture-audio.mjs
python3 prototype/scripts/generate-qwen-narration.py --dry-run
```

`sound-demo.html` 使用内联脚本，发布前还需在浏览器中完成语法、控制台和关键链路检查；`app.js` 的语法检查用于确保保留的旧研究原型仍可访问。

浏览器完整验收覆盖固定 `?viewport=phone` 的 `390x844` 审阅画布、带移动浏览器工具栏的短可视高度、真实响应式 `360x800`、`1180x820` 和 `1366x768`，并检查问题确认与预测旁白、讲解三段自动连播、讲解/操作分离、固定关联追问、讲解后慢放操作、子片段恢复、两次迁移、三类结果、问卷两种状态、点击目标、减少动态效果和控制台错误。每次 UI 或交互审阅都必须同时检查 `?viewport=phone`；该参数不得随桌面窗口伸缩。手机验收需逐状态检查页面与关键容器的滚动尺寸、边界框、裁切和按钮可达性，不能只看首屏截图。

2026-07-22 严格验收还覆盖：校准和预测不可跳过、先轻拨后用力拨、连续两次无效拖动后才显示保底按钮、琴弦跟随拖动、真实音频时长、手机固定播放区和完整滚动空间。2026-07-23 更新后的门禁以核心讲解完成为准；实验和关联追问均为可选体验，不阻塞迁移。

当前 Demo 只验证固定内容的体验闭环。它不证明真实 OCR、ASR、任意问题、动态生成、知识正确率、儿童学习效果、生产稳定性或付费意愿。

## 修改规则

1. 交互变化应先确认是否影响 PRD；
2. 修改 `app.js` 后至少执行 `node --check prototype/app.js`；
3. 响应式变化应人工检查平板和手机；
4. 公开声音 Demo 以 [当前 Demo 规范](../docs/design/2026-07-22-sound-value-demo-spec.md)和[执行 Brief](../docs/design/2026-07-22-sound-value-demo-execution-brief.md)为事实源；
5. 不把真实 API、儿童数据或生产密钥接入本目录。

原型是研究工具，不应直接演变为生产应用。真实实现应在 P0 技术切片完成后进入 `apps/` 和 `packages/`。
