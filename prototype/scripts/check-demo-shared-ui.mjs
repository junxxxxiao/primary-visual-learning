import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(new URL('../sound-demo.html', import.meta.url), 'utf8');
const designHtml = fs.readFileSync(new URL('../../design/high-fidelity/sound-demo-screen-concepts.html', import.meta.url), 'utf8');
const failures = [];
const requireMatch = (condition, message) => {
  if (!condition) failures.push(message);
};

requireMatch(/function redirectFilePreviewToHttp\(\)/.test(html), '直接打开 file:// Demo 时必须尝试切换到可检查的 HTTP 入口');
requireMatch(/if \(window\.location\.protocol !== 'file:'\) return;/.test(html), '本地预览切换不得影响 HTTP 或公开部署入口');
requireMatch(/probe\.onload = \(\) => window\.location\.replace\(`\$\{httpDemoUrl\}\$\{window\.location\.search\}\$\{window\.location\.hash\}`\)/.test(html), 'HTTP 服务可用后必须保留当前查询参数和锚点');
requireMatch(/probe\.onerror = \(\) => \{\};/.test(html), 'HTTP 服务未启动时必须保留当前 file:// 页面');

const redirectScript = html.match(/<script>\s*(function redirectFilePreviewToHttp\(\)[\s\S]*?redirectFilePreviewToHttp\(\);)\s*<\/script>/)?.[1];
const runRedirectScenario = ({ protocol, probeLoads }) => {
  let replacement = null;
  let probeRequest = null;
  const location = {
    protocol,
    search: '?screen=lesson&preset=math&viewport=phone',
    hash: '#segment-3',
    replace(url) { replacement = url; }
  };
  class PreviewProbe {
    set src(url) {
      probeRequest = url;
      if (probeLoads) this.onload();
      else this.onerror();
    }
  }
  if (redirectScript) vm.runInNewContext(redirectScript, { window: { location }, Image: PreviewProbe, Date });
  return { replacement, probeRequest };
};

const availableFilePreview = runRedirectScenario({ protocol: 'file:', probeLoads: true });
requireMatch(
  availableFilePreview.replacement === 'http://127.0.0.1:4173/sound-demo.html?screen=lesson&preset=math&viewport=phone#segment-3',
  '标准服务可用时 file:// Demo 必须自动切换到 HTTP 并保留完整状态'
);
const unavailableFilePreview = runRedirectScenario({ protocol: 'file:', probeLoads: false });
requireMatch(unavailableFilePreview.replacement === null, '标准服务不可用时 file:// Demo 不得跳到错误页');
const httpPreview = runRedirectScenario({ protocol: 'http:', probeLoads: true });
requireMatch(httpPreview.probeRequest === null && httpPreview.replacement === null, 'HTTP Demo 不得重复执行本地入口切换');

requireMatch(!/math-mode[^{}]*tutor-panel[^{]*\{[^}]*display:\s*none/.test(html), '数学预设不得隐藏共享小知面板');
requireMatch(!/math-mode[^{}]*lesson-controls[^{]*\{[^}]*display:\s*none/.test(html), '数学预设不得隐藏共享顶部状态');
requireMatch((html.match(/class="lesson-appbar"/g) || []).length >= 4, '讲解页面必须保留共享顶部导航');
requireMatch((html.match(/class="lesson-controls"/g) || []).length >= 4, '讲解页面必须保留共享顶部状态外壳');
requireMatch((html.match(/class="tutor-panel/g) || []).length >= 4, '讲解页面必须保留共享小知面板');
requireMatch((html.match(/class="followup-box"/g) || []).length >= 4, '讲解页面必须保留共享对话输入外壳');
requireMatch(/function renderMathTutor\(segment\)/.test(html), '数学讲解必须只替换共享对话面板的题目相关文案');
requireMatch(/followupBox\.setAttribute\('aria-disabled', 'true'\)/.test(html), '数学讲解必须保留追问外观但标记为不可操作');
requireMatch(/action\.classList\.add\('disabled'\)/.test(html), '数学追问按钮必须在共享语义同步后仍保持不可操作');
requireMatch(/if \(state\.preset === 'math'\) return;/.test(html), '数学追问入口点击后不得跳转或产生反馈');
requireMatch(/function submitMigration\(\)[\s\S]{0,900}if \(state\.preset === 'math'\)[\s\S]{0,700}showScreen\('feedback'\)[\s\S]{0,700}showScreen\('feedback'\)/.test(html), '数学迁移首次通过、提示后完成或未通过后都必须先进入共享体验反馈页');
requireMatch(/function startPlaybackTicker\(\)/.test(html), '真实旁白播放时必须有逐帧视觉时钟');
requireMatch(/function startPlaybackTicker\(\)[\s\S]{0,500}updatePlayer\(\)/.test(html), '逐帧视觉时钟必须同步更新进度和动画');
requireMatch(!/audio\.addEventListener\('timeupdate',\s*updatePlayer\)/.test(html), 'timeupdate 事件不得把 Event 对象误传为强制播放比例');
requireMatch(/audio\.addEventListener\('error'[\s\S]{0,400}startVisualFallback/.test(html), '音频媒体报错时必须继续视觉时间轴');
requireMatch(/let visualFallbackRatio = 0;/.test(html) && /visualFallbackStartedAt = performance\.now\(\) - visualFallbackRatio \* duration/.test(html), '暂停视觉降级必须保存当前位置并从原位置续播');
requireMatch(/function playAudioWithLeadIn\(source, onEnded = null\)[\s\S]{0,400}setTimeout\([\s\S]{0,220}, 1000\)/.test(html), '所有讲解子片段必须先静置 1 秒再播放');
requireMatch(/playAudioWithLeadIn\(audioPath\(`narration-math-\$\{segment\}`\)/.test(html), '数学讲解不得绕过共享 1 秒静置时序');
requireMatch(/playAudioWithLeadIn\(audioPath\(`narration-main-\$\{segment\}`\)/.test(html), '声音主讲解不得绕过共享 1 秒静置时序');
requireMatch(/playAudioWithLeadIn\(audioPath\(`narration-vacuum-\$\{segment\}`\)/.test(html), '声音关联讲解不得绕过共享 1 秒静置时序');
requireMatch(/if \(event\.target\.closest\('\[data-record-done\]'\)\) \{\s*if \(state\.preset === 'math'\) return;/.test(html), '数学语音确认不得提交或跳转');
requireMatch(/function mountLessonStatusControls\(\)[\s\S]{0,1200}lesson-status[\s\S]{0,600}data-subtitle-toggle/.test(html), '所有动画讲解页必须通过共享状态组把字幕开关放在段数标签上方');
requireMatch(!/function playerMarkup\([\s\S]{0,900}player-subtitle-toggle/.test(html), '共享底部播放器不得继续包含字幕开关');
requireMatch(/body\.runtime-demo \.unified-player \{[^}]*grid-template-columns:\s*52px minmax\(0, 1fr\) 58px;/.test(html), '移除字幕按钮后底部播放器必须使用三列布局');
requireMatch(!/slide-tag[^>]*>(?:自动播放|关联问题)|tag\.textContent\s*=\s*['`]自动播放|tag\.textContent\s*=\s*`关联讲解/.test(html), '所有动画步骤标签只能显示当前段数，不得带自动播放或关联讲解文案');
requireMatch(/label\.textContent = `\$\{state\.lessonSegment\} \/ \$\{segmentCount\}`/.test(html), '主讲解共享顶部状态必须只显示当前段数');
requireMatch(/label\.textContent = `\$\{state\.vacuumSegment\} \/ 3`/.test(html), '追问讲解共享顶部状态必须只显示当前段数');
requireMatch(/math-stage math-geometry-stage two-column/.test(html), '数学花圃讲解必须使用手机专属响应式构图');
requireMatch(/phone-review \.lesson-canvas > \.math-stage \{ grid-column: 1; grid-row: 1 \/ -1; \}/.test(html), '手机数学动画根节点必须占满整个讲解画布');
requireMatch(/phone-review \.math-stage \.ppt-reveal \{ transform: none; \}/.test(html), '手机数学渐进节点不得通过位移越出卡片边界');
requireMatch(/body\.runtime-demo \.vacuum-block-stage \{[^}]*grid-template-rows:\s*repeat\(2,minmax\(0,1fr\)\);[^}]*align-items:\s*stretch;/.test(html), '手机真空第三段必须为两个容器分配完整且可收缩的纵向空间');
requireMatch(/body\.runtime-demo \.vacuum-chamber > div \{[^}]*width:\s*100%;[^}]*display:\s*grid;[^}]*place-items:\s*center;[^}]*text-align:\s*center;/.test(html), '手机真空容器的文字和弦图必须位于圆弧内部安全内容区中央');
requireMatch(/body\.runtime-demo \.vacuum-chamber \.mini-string \{[^}]*width:\s*min\(220px,72%\);[^}]*height:\s*48px;/.test(html), '手机真空容器的弦图必须按内部安全宽度缩放');
requireMatch(/body\.phone-review \.lesson-appbar \.topic-tabs \{[^}]*overflow-x:\s*auto;[^}]*scroll-snap-type:\s*x proximity;/.test(html), '手机主题标签必须在独立轨道内横向滚动');
requireMatch(/function syncActiveTopicVisibility\(\)/.test(html) && /requestAnimationFrame\(syncActiveTopicVisibility\)/.test(html), '主题切换后必须让当前标签保持可见');
requireMatch(/body\.phone-review \.experiment-canvas \{[^}]*grid-template-rows:\s*minmax\(0,1fr\) 46px;/.test(html), '手机实验画布必须为固定迁移入口保留独立行');
requireMatch(/body\.phone-review \[data-screen="experiment"\] \.prediction-footer \{[^}]*margin:\s*0 !important;[^}]*justify-content:\s*center;/.test(html), '手机实验迁移入口必须清除旧偏移并水平居中');
requireMatch(/body\.runtime-demo,[\s\S]{0,180}height:\s*100dvh;/.test(html), '真实手机短视口必须使用动态视口高度');
requireMatch(/body\.runtime-demo \.relay-stage \{[^}]*grid-template-rows:\s*minmax\(76px,\.8fr\) minmax\(124px,1\.2fr\) minmax\(76px,\.8fr\);/.test(html), '手机真空接力动画必须使用紧凑纵向构图');
requireMatch(/body\.runtime-demo \.relay-caption \{[^}]*box-sizing:\s*border-box;[^}]*width:\s*calc\(100% - 8px\);/.test(html), '手机真空接力标签必须限制在轨道内部安全宽度');
requireMatch(/body\.runtime-demo \.relay-caption small \{[^}]*width:\s*auto;/.test(html), '手机真空接力说明不得使用超过轨道的固定宽度');
requireMatch(/body\.runtime-demo\.phone-review \.relay-stage \{[^}]*grid-template-columns:\s*1fr;[^}]*grid-template-rows:\s*minmax\(76px,\.8fr\) minmax\(124px,1\.2fr\) minmax\(76px,\.8fr\);/.test(html), '固定手机审阅模式不得依赖外层浏览器宽度应用真空纵向构图');
requireMatch(/body\.runtime-demo\.phone-review \.vacuum-chamber > div \{[^}]*width:\s*100%;[^}]*place-items:\s*center;[^}]*text-align:\s*center;/.test(html), '固定手机审阅模式必须复用真空容器内部安全区规则');
requireMatch(/body\.phone-review \.lesson-screen \{ padding: 9px 9px calc\(var\(--phone-safe-bottom\) \+ 9px\); \}/.test(html), '手机讲解页顶部只保留视觉边距，不得叠加顶部安全区空白带');
requireMatch(!/--phone-safe-top\s*:|var\(--phone-safe-top\)/.test(html), '所有手机页面不得定义或消费顶部安全区 Token');
requireMatch(/\[canvas, \.\.\.canvas\.querySelectorAll\('\*'\)\]/.test(html), '画布审计必须检查画布自身及全部后代');
requireMatch(/canvas\.dataset\.boundsAudit = violations\.length \? 'fail' : 'pass'/.test(html), '画布审计必须输出可自动验收的通过或失败状态');
requireMatch(/window\.addEventListener\('resize', scheduleLessonCanvasAudit\)/.test(html), '视口变化后必须重新检查动画画布边界');
requireMatch(/body\.runtime-demo \{[^}]*min-height:\s*100dvh;[^}]*overflow-x:\s*hidden;[^}]*overflow-y:\s*auto;/.test(html), 'ADR-0006 要求页面文档成为主要纵向滚动区');
requireMatch(/body\.runtime-demo \.concept-screen\.active \{[^}]*position:\s*relative;[^}]*overflow:\s*visible;/.test(html), '活动页面必须进入文档流并允许页面自然增高');
requireMatch(/body\.runtime-demo \.static-content,[\s\S]{0,100}body\.runtime-demo \.static-choice-list \{[^}]*overflow-y:\s*visible;/.test(html), '普通静态页面不得保留与页面竞争的纵向滚动区');
requireMatch(/body\.runtime-demo \.lesson-canvas \{[\s\S]{0,500}overflow-y:\s*auto;[\s\S]{0,200}overscroll-behavior-y:\s*auto;/.test(html), '讲解画布必须条件性滚动并在边界后把手势交还页面');
requireMatch(/body\.runtime-demo \.thread \{[^}]*overflow-y:\s*auto;[^}]*overscroll-behavior:\s*contain;/.test(html), '平板常驻对话栏与手机抽屉消息区必须独立滚动且不串滚背景');
requireMatch(/function pageScrollRoot\(\)/.test(html) && /pageScrollPositions/.test(html), '页面切换必须使用共享滚动根并保存页面位置');
requireMatch(/function showScreen\(name, updateUrl = true, scrollMode = 'top'\)/.test(html), '页面切换必须声明回顶部或恢复位置策略');
requireMatch(/document\.body\.classList\.toggle\('tutor-overlay-open', drawerOpen && usesTutorOverlay\(\)\)/.test(html) && /document\.body\.classList\.remove\('tutor-overlay-open'\)/.test(html), '手机小知抽屉必须在打开时锁定背景并在关闭时解除');
requireMatch(/phone-viewport-forced \.screen-scroll \{[^}]*overflow-x:\s*hidden;[^}]*overflow-y:\s*auto;/.test(html), '固定手机审阅画布必须在模拟页面视口内部滚动');
requireMatch(/const contentBounds = \{ left: 0, top: 0, right: canvas\.scrollWidth, bottom: canvas\.scrollHeight \}/.test(html), '画布边界审计必须以完整可滚内容范围为准');
requireMatch(/function auditScrollOwnership\(\)/.test(html) && /window\.__demoAuditScrollOwnership = auditScrollOwnership/.test(html), 'Demo 必须暴露机器可读的分层滚动契约审计入口');
requireMatch(/lessonShellGap < 8[\s\S]{0,100}lesson-shell-gap-missing/.test(html), '共享布局审计必须拦截导航和讲解网格之间缺少间距');
requireMatch(/lessonColumnsBottomDelta > 1[\s\S]{0,100}lesson-columns-bottom-misaligned/.test(html), '共享布局审计必须拦截工作区与对话栏底边不对齐');
requireMatch(/function syncTutorOverlayLock\(\)/.test(html) && /window\.addEventListener\('resize',[\s\S]{0,180}syncTutorOverlayLock\(\)/.test(html), '旋转或断点变化后必须重新同步小知抽屉的背景锁定');
requireMatch(
  /--lesson-shell-gap:\s*clamp\(12px,\s*1\.6vw,\s*20px\);/.test(html)
    && /\.lesson-shell \{[^}]*gap:\s*var\(--lesson-shell-gap\);/.test(html)
    && /--lesson-shell-gap:\s*clamp\(12px,\s*1\.6vw,\s*20px\);/.test(designHtml)
    && /\.lesson-shell \{[^}]*gap:\s*var\(--lesson-shell-gap\);/.test(designHtml),
  '原型和高保真共享讲解外壳必须消费统一间距 Token，不得使用在自适应高度下归零的百分比 gap'
);
requireMatch(/@media \(min-width: 701px\) and \(orientation: landscape\) \{[\s\S]{0,240}body\.runtime-demo \.tutor-panel \{[^}]*height:\s*100%;[^}]*max-height:\s*none;[^}]*align-self:\s*stretch;/.test(html), '平板共享对话栏必须与讲解工作区使用同一网格行并等高到底');
requireMatch(!/math-mode[^{}]*lesson-(?:shell|grid)|math-mode[^{}]*tutor-panel[^{}]*\{[^}]*(?:height|max-height|align-self|gap):/.test(html), '声音和数学不得分别覆盖共享讲解外壳的间距或对齐');
requireMatch(!/data-screen="(?:calibration|prediction)"/.test(html), '主原型不得保留已退出的校准或预测页面 DOM');
requireMatch(/if \(name === 'calibration' \|\| name === 'prediction'\) name = 'loading';/.test(html), '主原型必须把旧校准和预测路由归一到加载页');
requireMatch(!/narration-confirm-text\.wav|playConfirmationNarration/.test(designHtml), '高保真确认页不得播放已废弃的校准或预测旁白');
requireMatch(!/data-screen="(?:calibration|prediction)"/.test(designHtml), '高保真设计不得保留已退出的校准或预测页面 DOM');
requireMatch(/if \(name === 'calibration' \|\| name === 'prediction'\) name = 'loading';/.test(designHtml), '高保真设计必须把旧校准和预测路由归一到加载页');
requireMatch(!/const validScreens = \[[^\]]*(?:calibration|prediction)/.test(designHtml), '高保真有效页面列表不得重新启用退休状态');

if (failures.length) {
  console.error(failures.map(failure => `- ${failure}`).join('\n'));
  process.exit(1);
}

console.log('Shared lesson UI checks passed for sound and math presets.');
