import fs from 'node:fs';

const html = fs.readFileSync(new URL('../sound-demo.html', import.meta.url), 'utf8');
const failures = [];
const requireMatch = (condition, message) => {
  if (!condition) failures.push(message);
};

requireMatch(!/math-mode[^{}]*tutor-panel[^{]*\{[^}]*display:\s*none/.test(html), '数学预设不得隐藏共享小知面板');
requireMatch(!/math-mode[^{}]*lesson-controls[^{]*\{[^}]*display:\s*none/.test(html), '数学预设不得隐藏共享字幕与播放状态');
requireMatch((html.match(/class="lesson-appbar"/g) || []).length >= 4, '讲解页面必须保留共享顶部导航');
requireMatch((html.match(/class="lesson-controls"/g) || []).length >= 4, '讲解页面必须保留共享字幕开关');
requireMatch((html.match(/class="tutor-panel/g) || []).length >= 4, '讲解页面必须保留共享小知面板');
requireMatch((html.match(/class="followup-box"/g) || []).length >= 4, '讲解页面必须保留共享对话输入外壳');
requireMatch(/function renderMathTutor\(segment\)/.test(html), '数学讲解必须只替换共享对话面板的题目相关文案');
requireMatch(/followupBox\.setAttribute\('aria-disabled', 'true'\)/.test(html), '数学讲解必须保留追问外观但标记为不可操作');
requireMatch(/action\.classList\.add\('disabled'\)/.test(html), '数学追问按钮必须在共享语义同步后仍保持不可操作');
requireMatch(/if \(state\.preset === 'math'\) return;/.test(html), '数学追问入口点击后不得跳转或产生反馈');
requireMatch(/function startPlaybackTicker\(\)/.test(html), '真实旁白播放时必须有逐帧视觉时钟');
requireMatch(/function startPlaybackTicker\(\)[\s\S]{0,500}updatePlayer\(\)/.test(html), '逐帧视觉时钟必须同步更新进度和动画');
requireMatch(/audio\.addEventListener\('error'[\s\S]{0,400}startVisualFallback/.test(html), '音频媒体报错时必须继续视觉时间轴');

if (failures.length) {
  console.error(failures.map(failure => `- ${failure}`).join('\n'));
  process.exit(1);
}

console.log('Shared lesson UI checks passed for sound and math presets.');
