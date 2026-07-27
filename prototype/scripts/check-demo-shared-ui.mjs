import fs from 'node:fs';

const html = fs.readFileSync(new URL('../sound-demo.html', import.meta.url), 'utf8');
const failures = [];
const requireMatch = (condition, message) => {
  if (!condition) failures.push(message);
};

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
requireMatch(/function playerMarkup\([\s\S]{0,900}class="player-subtitle-toggle" data-subtitle-toggle/.test(html), '字幕开关必须属于共享底部播放器');
requireMatch(!/<div class="lesson-controls"><span>字幕/.test(html), '顶部导航不得包含字幕开关节点');
requireMatch(!/lesson-controls[^\n{]*data-subtitle-toggle|dataset\.subtitleToggle/.test(html), '不得用页面脚本把顶部状态升级为字幕开关');

if (failures.length) {
  console.error(failures.map(failure => `- ${failure}`).join('\n'));
  process.exit(1);
}

console.log('Shared lesson UI checks passed for sound and math presets.');
