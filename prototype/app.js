const app = document.querySelector('#app');
const nav = document.querySelector('#prototype-nav');
const titleEl = document.querySelector('#screen-title');
const descriptionEl = document.querySelector('#screen-description');
const demoAudio = document.querySelector('#demo-audio');
const fixtureQuestion = '更用力拨同一根弦，音调会更高吗？';
const SEGMENT_LEAD_IN_MS = 1000;
const TUTOR_HOLD_DELAY_MS = 280;
const NARRATION_VERSION = 'qwen-standard-1';
const narrationAudio = name => `./assets/audio/narration-${name}.wav?v=${NARRATION_VERSION}`;
const SURVEY_URL = window.SOUND_DEMO_CONFIG?.SURVEY_URL?.trim() || '';
const audioSources = {
  light: './assets/audio/string-light.wav',
  strong: './assets/audio/string-strong.wav',
  lessonIntro: narrationAudio('lesson-intro'),
  practice: narrationAudio('practice'),
  returnMain: narrationAudio('return-main')
};
const estimatedDurations = {
  main: [6, 8, 7],
  vacuum: [7, 7, 7]
};

const screens = {
  publicEntry: ['声音体验入口', '固定声音主题价值 Demo'],
  ask: ['发起提问', '选择一种方式，把问题交给小知'],
  onboarding: ['首次使用', '家长授权与儿童设置'],
  home: ['儿童首页', '选择学习入口'],
  askVoice: ['语音提问', '固定夹具模拟语音输入'],
  askPhoto: ['拍照提问', '固定夹具模拟框选与隐私检查'],
  confirm: ['问题确认', '确认儿童原话与学习目标'],
  loading: ['渐进等待', '5–8 秒固定时序演示'],
  explore: ['核心探索', '操作、打断、分支与场景恢复'],
  migration: ['迁移验证', '使用新情境验证同一概念'],
  feedback: ['讲解反馈', '主观理解与客观结果分开记录'],
  complete: ['儿童完成页', '自动保存与过程反馈'],
  history: ['我的探索', '回放并从节点继续'],
  parentPin: ['家长验证', '四位 PIN 进入工作台'],
  parentToday: ['家长工作台', '今日概览与学习证据'],
  parentRecords: ['探索记录', '单次报告与完整过程'],
  parentInsights: ['近期学习画像', '演示档案与证据强度'],
  parentSettings: ['家长设置', '权限、保存与删除'],
  failure: ['异常与降级', '15 秒失败固定状态']
};

const navGroups = [
  ['公开体验', ['publicEntry', 'ask']],
  ['核心流程', ['home', 'askVoice', 'askPhoto', 'confirm', 'loading', 'explore', 'migration', 'feedback', 'complete']],
  ['历史与家长', ['history', 'parentToday', 'parentRecords', 'parentInsights', 'parentSettings']],
  ['边界状态', ['onboarding', 'failure']]
];

const state = {
  screen: 'publicEntry',
  viewport: window.innerWidth < 760 || window.innerHeight > window.innerWidth ? 'mobile' : 'tablet',
  force: 'light',
  slow: false,
  playing: false,
  segment: 1,
  progress: 0,
  branch: false,
  branchAvailable: false,
  lessonComplete: false,
  conversationQuestion: '',
  mobileTutorOpen: false,
  followupSelected: 'slow',
  savedSnapshot: null,
  pendingSnapshot: null,
  followupRecording: false,
  followupTranscriptReady: false,
  segmentLeadIn: false,
  returningFromVacuum: false,
  tutorWasPlaying: false,
  migrationStage: 'fork',
  migrationConclusion: null,
  migrationReason: null,
  migrationLoudness: null,
  transferResult: null,
  migrationAttempted: false,
  feedback: null,
  historySelected: 0,
  historyDetail: false,
  historyExpanded: null,
  parentFilter: 'all',
  parentRecordSelected: 'sound-string',
  parentRecordExpanded: null,
  settings: { history: true, explore: true, captions: true, reducedMotion: false },
  deleteModal: false,
  recording: false,
  captured: false,
  inputSource: 'voice',
  questionText: fixtureQuestion,
  onboardingStep: 1,
  askMode: 'text',
  operations: { light: false, strong: false },
  dragFailures: 0,
  followupsCompleted: { slow: false, vacuum: false },
  timelineDurations: { main: [...estimatedDurations.main], vacuum: [...estimatedDurations.vacuum] },
  activeAudio: null,
  coreStarted: false,
  followupInputMode: 'text'
};
let loadingTimer = null;
let followupRecordingTimer = null;
let segmentLeadInTimer = null;
let tutorHoldTimer = null;
let tutorHoldActive = false;
let tutorHoldSnapshot = null;
let tutorHoldWasPlaying = false;
let suppressNextTutorClick = false;

const previewParams = new URLSearchParams(location.search);
if (screens[previewParams.get('screen')] || previewParams.get('screen') === 'askPhoto') {
  state.screen = previewParams.get('screen');
}
const researchMode = previewParams.get('research') === 'true';
const viewportOverride = ['tablet', 'mobile'].includes(previewParams.get('viewport'));
if (viewportOverride) {
  state.viewport = previewParams.get('viewport');
}
if (previewParams.get('branch') === 'true') {
  state.branch = true;
  state.branchAvailable = true;
}
if (previewParams.get('interrupt') === 'true') {
  state.screen = 'explore';
  state.mobileTutorOpen = true;
  state.playing = false;
}
if (state.screen === 'explore') state.coreStarted = true;

const records = [
  { title: fixtureQuestion, date: '今天 16:20', topics: 2, questions: 2, result: '已理解' },
  { title: '为什么四分之一比三分之一小？', date: '昨天 19:05', topics: 1, questions: 1, result: '部分理解' },
  { title: '影子为什么会变长？', date: '7 月 15 日', topics: 2, questions: 3, result: '已理解' }
];

const parentRecordsData = [
  { id: 'sound-string', title: fixtureQuestion, date: '今天 16:20', subject: '科学 · 声音', status: 'understood', statusLabel: '已理解', independent: '是', feedback: '讲明白了', misconception: '孩子原本认为“用力越大，音调越高”。', intervention: '保持弦长、松紧和粗细不变，对比轻拨与用力拨，并慢放观察振幅。', transfer: '在音叉情境中独立判断“更用力主要让声音更响”。', advice: '暂不需要介入，可以在生活中继续比较轻敲与重敲。' },
  { id: 'fraction-size', title: '为什么四分之一比三分之一小？', date: '今天 15:40', subject: '数学 · 分数', status: 'partial', statusLabel: '部分理解', independent: '使用提示', feedback: '还有一点不懂', misconception: '孩子会根据分母数字大小直接判断分数大小。', intervention: '用同样大的圆形并排切成三份和四份，只比较其中的一份。', transfer: '换成长方形后判断正确，但仍使用了一次提示。', advice: '可以用同一块饼或同一张纸继续做等整体比较。' },
  { id: 'shadow-length', title: '为什么下午的影子更长？', date: '今天 14:10', subject: '科学 · 光与影', status: 'help', statusLabel: '建议陪一陪', independent: '需要帮助', feedback: '没讲明白', misconception: '孩子把影子长度变化理解成物体本身变高了。', intervention: '固定物体高度，只改变手电筒照射角度并对比影子。', transfer: '更换物体后仍无法判断光源更低时影子如何变化。', advice: '建议家长用台灯和玩具现场陪孩子再做一次。' },
  { id: 'multiply-array', title: '6 × 4 为什么也可以看成 4 × 6？', date: '7 月 16 日', subject: '数学 · 乘法', status: 'understood', statusLabel: '已理解', independent: '是', feedback: '讲明白了', misconception: '孩子认为交换两个数后点阵总数会变化。', intervention: '旋转同一组点阵，比较行数、列数与总数。', transfer: '能用另一组点阵解释乘法交换律。', advice: '无需介入，可继续用生活中的阵列寻找例子。' },
  { id: 'plant-water', title: '植物喝进去的水到哪里去了？', date: '7 月 15 日', subject: '科学 · 植物', status: 'partial', statusLabel: '部分理解', independent: '使用提示', feedback: '基本明白', misconception: '孩子认为水只停留在根部。', intervention: '用染色水示意水沿茎向叶片移动。', transfer: '能说明水会向上运输，但还不能解释叶片散失水分。', advice: '可继续观察透明杯中的芹菜染色实验。' }
];

function showToast(message) {
  const toast = document.querySelector('#toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 1800);
}

function escapeHtml(value) {
  return value.replace(/[&<>"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[char]);
}

function formatTeachingText(value) {
  const tokens = /(振幅基本不变|振幅变大|振幅|响度|声音更响|摆动范围更大|摆动范围较小|频率基本不变|频率|音调基本不变|音调|只改变|拨弦力度|真空|没有空气|仍然振动|仍在振动)/g;
  return escapeHtml(value).replace(tokens, token => {
    const className = /(振幅|响度|声音更响|摆动范围)/.test(token)
      ? 'concept-green'
      : /(频率|音调)/.test(token)
        ? 'concept-blue'
        : 'concept-yellow';
    return `<mark class="${className}">${token}</mark>`;
  });
}

function resetTutorHold() {
  clearTimeout(tutorHoldTimer);
  tutorHoldTimer = null;
  tutorHoldActive = false;
  tutorHoldSnapshot = null;
  tutorHoldWasPlaying = false;
}

function formatClock(seconds) {
  const safe = Math.max(0, Math.round(seconds));
  return `${String(Math.floor(safe / 60)).padStart(2, '0')}:${String(safe % 60).padStart(2, '0')}`;
}

function narrationSource() {
  return narrationAudio(`${state.branch ? 'vacuum' : 'main'}-${state.segment}`);
}

function currentTimelineDuration() {
  const topic = state.branch ? 'vacuum' : 'main';
  return state.timelineDurations[topic][state.segment - 1] || estimatedDurations[topic][state.segment - 1];
}

function operationsComplete() {
  return state.operations.light && state.operations.strong;
}

function migrationReady() {
  return !state.branch && state.lessonComplete;
}

function captureMainSnapshot() {
  return {
    branch: false,
    segment: state.segment,
    force: state.force,
    slow: state.slow,
    lessonComplete: state.lessonComplete,
    wasPlaying: state.playing || state.tutorWasPlaying
  };
}

function clearSegmentLeadIn() {
  clearTimeout(segmentLeadInTimer);
  segmentLeadInTimer = null;
  state.segmentLeadIn = false;
}

function stopCurrentNarration() {
  clearSegmentLeadIn();
  demoAudio.onloadedmetadata = null;
  demoAudio.ontimeupdate = null;
  demoAudio.onended = null;
  demoAudio.pause();
}

function startSegmentPlayback({ fromProgress = 0, withLeadIn = fromProgress === 0 } = {}) {
  stopCurrentNarration();
  state.progress = fromProgress;
  state.playing = true;
  if (!withLeadIn) {
    render();
    playFixedAudio(narrationSource(), { timeline: true, fromProgress });
    return;
  }
  state.segmentLeadIn = true;
  render();
  segmentLeadInTimer = setTimeout(() => {
    segmentLeadInTimer = null;
    state.segmentLeadIn = false;
    render();
    playFixedAudio(narrationSource(), { timeline: true, fromProgress: 0 });
  }, SEGMENT_LEAD_IN_MS);
}

function startVacuumFollowup(snapshot = state.pendingSnapshot || captureMainSnapshot()) {
  stopCurrentNarration();
  state.savedSnapshot = snapshot;
  state.pendingSnapshot = null;
  state.followupRecording = false;
  state.followupTranscriptReady = false;
  state.returningFromVacuum = false;
  state.mobileTutorOpen = false;
  state.tutorWasPlaying = false;
  state.conversationQuestion = '如果没有空气呢？';
  state.branchAvailable = true;
  state.branch = true;
  state.coreStarted = true;
  state.segment = 1;
  state.progress = 0;
  state.lessonComplete = false;
  startSegmentPlayback();
}

function resumeMainFromInterrupt({ autoplay = true } = {}) {
  const snapshot = state.savedSnapshot;
  if (!snapshot) return false;
  stopCurrentNarration();
  state.branch = false;
  state.segment = snapshot.segment;
  state.progress = 0;
  state.force = snapshot.force;
  state.slow = snapshot.slow;
  state.lessonComplete = snapshot.lessonComplete ?? false;
  state.playing = autoplay && !state.lessonComplete;
  state.mobileTutorOpen = false;
  state.conversationQuestion = '';
  state.returningFromVacuum = false;
  if (state.playing) startSegmentPlayback();
  else render();
  return true;
}

function playFixedAudio(source, { timeline = false, fromProgress = 0, onEnded = null } = {}) {
  demoAudio.onloadedmetadata = null;
  demoAudio.ontimeupdate = null;
  demoAudio.onended = null;
  demoAudio.pause();
  state.activeAudio = source;
  demoAudio.playbackRate = state.slow && timeline ? 0.75 : 1;
  demoAudio.onloadedmetadata = () => {
    if (timeline && Number.isFinite(demoAudio.duration)) {
      const topic = state.branch ? 'vacuum' : 'main';
      state.timelineDurations[topic][state.segment - 1] = demoAudio.duration;
      demoAudio.currentTime = demoAudio.duration * fromProgress / 100;
      updateTimelineUi();
    }
    demoAudio.play().catch(() => showToast('点击播放按钮即可听固定音频'));
  };
  demoAudio.ontimeupdate = timeline ? () => {
    if (!demoAudio.duration) return;
    state.progress = Math.min(100, demoAudio.currentTime / demoAudio.duration * 100);
    updateTimelineUi();
  } : null;
  demoAudio.onended = () => {
    if (onEnded) {
      onEnded();
      return;
    }
    if (timeline) {
      state.progress = 100;
      if (state.segment < 3) {
        state.segment += 1;
        startSegmentPlayback();
        return;
      }
      if (state.branch && state.savedSnapshot) {
        state.followupsCompleted.vacuum = true;
        state.returningFromVacuum = true;
        state.playing = true;
        render();
        playFixedAudio(audioSources.returnMain, {
          onEnded: () => resumeMainFromInterrupt({ autoplay: true })
        });
        return;
      }
      state.lessonComplete = true;
      state.playing = false;
      render();
      if (!state.branch) playFixedAudio(audioSources.practice);
      return;
    }
    state.playing = false;
    render();
  };
  demoAudio.src = source;
  demoAudio.load();
}

function playScreenNarration(screen) {
  const source = screen === 'explore' && !state.coreStarted
      ? audioSources.lessonIntro
      : audioSources[screen];
  if (!source) return;
  state.playing = true;
  render();
  playFixedAudio(source);
}

function updateTimelineUi() {
  const slider = document.querySelector('[data-progress]');
  if (slider) slider.value = state.progress;
  const clock = document.querySelector('[data-timeline-clock]');
  const duration = currentTimelineDuration();
  if (clock) clock.textContent = `${formatClock(duration * state.progress / 100)} / ${formatClock(duration)} · ${clock.dataset.segmentTitle}`;
  document.querySelectorAll('[data-reveal-at]').forEach(element => {
    element.classList.toggle('timeline-hidden', state.progress < Number(element.dataset.revealAt));
  });
}

function appHeader({ back, title = '小知', subtitle = '互动视觉家教', parent = false } = {}) {
  return `<header class="app-header">
    <div class="app-brand">
      ${back ? `<button class="back-button" data-action="back" aria-label="返回">‹</button>` : `<span class="brand-symbol">知</span>`}
      <div><strong>${title}</strong><small>${subtitle}</small></div>
    </div>
    ${parent ? '<div class="header-actions"><button class="header-button" data-screen="parentPin">家长工作台</button></div>' : ''}
  </header>`;
}

function renderOnboarding() {
  if (state.onboardingStep === 1) {
    return `<div class="app-screen">${appHeader({ parent: false })}<main class="screen-body centered">
      <div class="content-narrow">
        <div class="eyebrow">首次使用</div><h1>先由家长完成儿童数据说明</h1>
        <p>本次家庭测试使用固定内容模拟录音、拍摄和识别，不申请真实麦克风或相机权限。</p>
        <div class="notice info">原型会保存文字化问题、讲解片段、场景状态、互动操作和迁移结果，用于回看和研究观察。演示记录可随时删除。</div>
        <div class="choice-list">
          <label class="choice selected"><span class="choice-marker">✓</span><span><strong>我已阅读测试说明</strong><small>了解用途、保存期限与撤回方式</small></span></label>
          <label class="choice selected"><span class="choice-marker">✓</span><span><strong>允许保存本次原型记录</strong><small>不保存真实照片、原始语音、姓名和学校</small></span></label>
        </div>
        <div class="button-row end"><button class="btn primary" data-action="onboarding-next">继续设置</button></div>
      </div>
    </main></div>`;
  }
  return `<div class="app-screen">${appHeader({ parent: false })}<main class="screen-body centered">
    <div class="content-narrow"><div class="eyebrow">儿童设置</div><h1>为孩子准备适合的内容</h1>
      <div class="settings-list">
        <div class="setting-row"><div><strong>孩子年级</strong><small>用于控制语言与认知难度</small></div><select class="fake-input" style="width:150px"><option>三年级</option><option>四年级</option></select></div>
        <div class="setting-row"><div><strong>教材版本</strong><small>版本不明时只匹配通用课标</small></div><select class="fake-input" style="width:150px"><option>人教版</option><option>暂不设置</option></select></div>
        <div class="setting-row"><div><strong>相关课外探索</strong><small>只开放与当前知识相关的安全内容</small></div><button class="switch ${state.settings.explore ? 'on' : ''}" data-setting="explore" aria-label="切换相关课外探索"></button></div>
      </div>
      <div class="button-row end"><button class="btn primary" data-screen="home">进入儿童模式</button></div>
    </div>
  </main></div>`;
}

function renderHome() {
  const knowledgeTopics = [
    ['string', '声音', fixtureQuestion, '比较振幅、响度和音调'],
    ['vacuum', '声音', '没有空气，还能听到声音吗？', '观察声音传播需要什么'],
    ['slow', '声音', '琴弦振动得太快，怎么看清？', '进入慢放观察琴弦运动']
  ];
  return `<div class="app-screen">${appHeader({ parent: true })}<main class="screen-body">
    <div class="content-wide home-layout">
      <div class="home-welcome"><div><h1>今天想弄明白什么？</h1><p>可以拍下不会的，也可以直接问一个为什么。</p></div><div class="helper">下午好，小宇<br>三年级</div></div>
      <div class="entry-grid">
        <button class="entry-card" data-screen="askPhoto"><span class="entry-icon">▧</span><h2>拍下不会的</h2><p>课本、题目、插图或身边的东西</p><span class="entry-arrow">→</span></button>
        <button class="entry-card" data-screen="askVoice"><span class="entry-icon">◉</span><h2>问一个为什么</h2><p>说出你正在好奇或没弄懂的问题</p><span class="entry-arrow">→</span></button>
      </div>
      <section class="home-section knowledge-planet" aria-labelledby="knowledge-title">
        <div class="home-section-heading"><div><h2 id="knowledge-title">知识星球</h2><p>选择一个准备好的知识解答，直接进入互动演示</p></div></div>
        <div class="knowledge-grid">${knowledgeTopics.map(([id, subject, title, note]) => `<button class="knowledge-card" data-knowledge="${id}"><span class="knowledge-orbit" aria-hidden="true"></span><span><small>${subject}</small><strong>${title}</strong><em>${note}</em></span><span class="card-arrow">→</span></button>`).join('')}</div>
      </section>
      <section class="home-section home-history" aria-labelledby="home-history-title">
        <div class="home-section-heading"><div><h2 id="home-history-title">我的探索</h2><p>最近问过的问题</p></div><button class="section-link" data-screen="history">全部探索记录 <span>→</span></button></div>
        <div class="home-record-grid">${records.slice(0, 3).map((record, index) => `<button class="home-record-card" data-history-index="${index}"><span><small>${record.date}</small><strong>${record.title}</strong><em>${record.result}</em></span><span class="card-arrow">→</span></button>`).join('')}</div>
      </section>
    </div>
  </main></div>`;
}

function renderPublicEntry() {
  return `<div class="app-screen public-screen"><main class="screen-body centered public-entry-body">
    <div class="public-entry-layout">
      <div class="public-entry-copy">
        <div class="public-mark" aria-hidden="true"><span></span><span></span><span></span></div>
        <div class="eyebrow">固定声音主题体验</div>
        <h1>你问为什么，<br />小知现场演给你看。</h1>
        <p class="public-lead">这是一个约 4 分钟的固定声音主题体验，用来展示互动视觉讲解方式。当前不会识别真实语音，也不能回答任意问题。</p>
        <div class="public-entry-note"><strong>数据说明</strong><span>本体验不调用相机或麦克风，不要求登录，也不保存儿童个人信息。</span></div>
        <button class="btn primary public-start" data-screen="ask">开始体验 <span aria-hidden="true">→</span></button>
      </div>
      <div class="public-entry-visual" aria-label="琴弦、音叉和振动记录图的演示插图">
        <div class="entry-lab-label">声音 · 振动 · 观察</div>
        <div class="entry-string-scene"><i></i><i></i><span></span></div>
        <div class="entry-fork-scene"><span></span><b></b><b></b></div>
        <div class="entry-graph"><span></span><span></span><span></span><span></span><span></span></div>
        <div class="entry-caption">同一根弦 · 同一组条件 · 一次可操作的发现</div>
      </div>
    </div>
  </main></div>`;
}

function renderAsk() {
  const modes = [
    ['text', '文字问题', '直接看见你要问的内容', '▤'],
    ['photo', '拍照', '框出课本或身边的对象', '▧'],
    ['voice', '语音', '说出你正在好奇的为什么', '◉']
  ];
  return `<div class="app-screen public-screen"><header class="public-topbar"><button class="back-button" data-action="back" aria-label="返回入口">‹</button><div><strong>发起一个问题</strong><small>先选择你习惯的方式</small></div><span class="public-step">1 / 4</span></header><main class="screen-body public-ask-body">
    <div class="public-ask-layout">
      <div class="public-ask-copy"><div class="eyebrow">问题是固定的，入口可以不同</div><h1>从一个“为什么”开始</h1><p>真实产品可以接住文字、照片或语音。这个 Demo 固定演示同一个声音问题，让你先感受完整解决链路。</p><div class="public-question-label">本次演示的问题</div><div class="fixed-question">“${fixtureQuestion}”</div><div class="notice info">点击下面的入口会展示对应的使用体感；不会请求权限，也不会真的上传或识别。</div></div>
      <div class="ask-panel"><div class="ask-panel-heading"><span>你想怎样告诉小知？</span><small>选择一种方式</small></div><div class="ask-mode-grid">${modes.map(([id,label,note,icon])=>`<button class="ask-mode ${state.askMode===id?'selected':''}" data-ask-mode="${id}"><span class="ask-mode-icon">${icon}</span><span><strong>${label}</strong><small>${note}</small></span><b>${state.askMode===id?'✓':'→'}</b></button>`).join('')}</div><div class="fixed-input-wrap"><label for="fixed-question">文字问题</label><input id="fixed-question" class="fake-input fixed-question-input" value="${fixtureQuestion}" readonly aria-readonly="true" /><small>为了保证演示可复现，问题不能修改。</small></div><div class="ask-feedback" role="status">${state.askMode==='photo'?'拍照入口已准备好，Demo 将使用固定课本琴弦图片。':state.askMode==='voice'?'语音入口已准备好，Demo 将使用固定文字转写。':'文字入口已准备好，问题已放入提问框。'}</div><div class="button-row end"><button class="btn primary" data-screen="confirm">确认这个问题 <span aria-hidden="true">→</span></button></div></div>
    </div>
  </main></div>`;
}

function renderAskVoice() {
  return `<div class="app-screen">${appHeader({ back: true })}<main class="screen-body centered">
    <div class="content-narrow"><h1>把问题说给我听</h1><p>按住说话，松开后先确认文字。原型不会调用真实麦克风。</p>
      <div class="ask-box">
        <button class="voice-button ${state.recording ? 'recording' : ''}" data-action="record">
          <span>${state.recording ? '<span class="waveform"><span></span><span></span><span></span><span></span><span></span></span>正在听…' : '● 按住说话'}</span>
        </button>
        <div class="helper" style="text-align:center">测试夹具会识别为：${fixtureQuestion}</div>
        <div style="margin-top:22px"><label class="helper" for="question-input">也可以打字</label><input id="question-input" class="fake-input" data-question-input value="${escapeHtml(state.questionText)}" /></div>
      </div>
      <div class="button-row end"><button class="btn primary" data-screen="confirm">确认问题</button></div>
    </div>
  </main></div>`;
}

function renderAskPhoto() {
  return `<div class="app-screen">${appHeader({ back: true })}<main class="screen-body">
    <div class="content-narrow"><h1>拍下不会的地方</h1><p>只框选需要解释的部分，提交前检查姓名、学校和人脸。</p>
      <button class="capture-frame" data-action="capture"><div class="capture-sheet"><strong>${state.captured ? '已框选：课本中的琴弦插图' : '将课本放在框内'}</strong><p>${state.captured ? '原始照片不会进入持久化记录' : '点击使用固定测试图片'}</p><div style="font-size:44px">${state.captured ? '✓' : '▧'}</div></div></button>
      <section class="photo-supplement" aria-labelledby="photo-supplement-title">
        <div><h2 id="photo-supplement-title">补充你的问题 <span>选填</span></h2><p>可以说一句，也可以输入文字，帮助我理解你想问什么。</p></div>
        <div class="photo-supplement-inputs">
          <button class="voice-compact ${state.recording ? 'recording' : ''}" data-action="record" aria-label="录入语音补充">
            ${state.recording ? '<span class="waveform"><span></span><span></span><span></span><span></span><span></span></span><strong>正在听</strong>' : '<span class="voice-compact-icon">●</span><strong>说一句</strong>'}
          </button>
          <div><label class="helper" for="photo-question-input">文字补充</label><input id="photo-question-input" class="fake-input" data-question-input placeholder="${fixtureQuestion}" /></div>
        </div>
      </section>
      <div class="button-row end"><button class="btn" data-screen="home">取消</button><button class="btn primary" data-screen="confirm" ${state.captured ? '' : 'disabled'}>使用框选内容</button></div>
    </div>
  </main></div>`;
}

function renderConfirm() {
  return `<div class="app-screen">${appHeader({ back: true })}<main class="screen-body centered">
    <div class="content-narrow"><div class="eyebrow">你想问的问题是</div><div class="question-quote">“${escapeHtml(state.questionText)}”</div>
      <div class="button-row"><button class="btn" data-screen="ask">修改问题</button><button class="btn primary" data-screen="loading">就是这个问题</button></div>
    </div>
  </main></div>`;
}

function renderLoading() {
  return `<div class="app-screen">${appHeader({ back: true })}<main class="screen-body centered">
    <div class="loading-wrap"><div class="loading-graphic" aria-hidden="true"><div class="loading-rig"><i></i><span></span><i></i><b></b></div><small>正在准备琴弦观察画面</small></div><h1>正在准备第一段观察</h1><p>先把同一根琴弦的轻拨和用力拨放在一起比较。</p><div class="progress-track" role="progressbar" aria-label="讲解准备进度" aria-valuemin="0" aria-valuemax="100"><div class="progress-bar"></div></div><div class="helper">准备完成后会自动开始，互动模型将在讲解后出现</div>
    </div>
  </main></div>`;
}

function exploreHeader() {
  return `<header class="explore-header"><button class="back-button" data-screen="publicEntry" aria-label="返回体验入口">‹</button>
    <div class="topic-switcher" role="tablist" aria-label="讲解主题">
      <button class="${!state.branch ? 'active' : ''}" data-topic="main" role="tab" aria-selected="${!state.branch}" ${state.returningFromVacuum ? 'disabled' : ''}>琴弦振动</button>
      ${state.branchAvailable ? `<button class="${state.branch ? 'active' : ''}" data-topic="vacuum" role="tab" aria-selected="${state.branch}" ${state.returningFromVacuum ? 'disabled' : ''}>真空中的声音</button>` : ''}
    </div>
    <span class="explore-header-spacer" aria-hidden="true"></span>
  </header>`;
}

function renderExplore() {
  const vacuum = state.branch;
  const segmentSets = vacuum
    ? [
        ['先拆开两件事', '琴弦在动，声音才能出发', '问得好！先别急着回答“听不听得到”，我们把它拆成两步来看。', ['第一步：琴弦自己会不会振动', '第二步：振动能不能走到耳朵', '这样就不会把“振动”和“传播”混在一起']],
        ['声音是怎样走过来的？', '空气像一支接力队', '琴弦不会直接碰到耳朵。它先推旁边的空气，空气再把振动一层层传过来。', ['琴弦推动附近空气', '空气接力传递振动', '最后，耳朵接收到振动']],
        ['如果没有空气呢？', '找出接力中断的位置', '真空里，琴弦仍然可以振动；可是中间没有空气接力，振动就传不到远处。', ['琴弦：仍然振动', '空气：没有了', '结论：远处听不到通过空气传来的声音']]
      ]
    : [
        ['先把问题比公平', '只改变力度，其他条件都不动', '想象你手里就是同一把吉他。我们只把手指的力气变大，琴弦本身不换。', ['保持：弦长、松紧、粗细', '改变：拨弦力度', '要观察：摆动多大、振动多快、听起来怎样']],
        ['看看真实现象', '摆得更开，不等于来回得更快', '轻轻拨，琴弦摆动得窄；用力拨，琴弦摆动得更开。可是同样一小段时间里，它们来回的次数差不多。', ['轻轻拨：摆动范围较小', '用力拨：摆动范围更大', '共同点：往返节奏基本相同']],
        ['给发现起名字', '振幅管响度，频率管音调', '摆动范围叫振幅，单位时间内振动的次数叫频率。现在就能解释刚才听到的现象了。', ['力气变大 → 振幅变大 → 声音更响', '频率基本不变 → 音调基本不变', '结论只适用于同一根弦、其他条件不变时']]
      ];
  const activeSegment = segmentSets[state.segment - 1];
  const segmentProgress = state.progress;
  const timelineDuration = currentTimelineDuration();
  const amplitude = state.force === 'strong' ? 30 : 14;
  const stringCurve = state.force === 'strong' ? 28 : 48;
  const recordPath = state.force === 'strong'
    ? 'M0 50 C12 15 28 15 40 50 S68 85 80 50 S108 15 120 50 S148 85 160 50 S188 15 200 50 S228 85 240 50 S268 15 280 50 S308 85 320 50 S348 15 360 50 S388 85 400 50'
    : 'M0 50 C12 34 28 34 40 50 S68 66 80 50 S108 34 120 50 S148 66 160 50 S188 34 200 50 S228 66 240 50 S268 34 280 50 S308 66 320 50 S348 34 360 50 S388 66 400 50';
  if (!state.coreStarted) {
    return `<div class="app-screen explore-screen">${exploreHeader()}<main class="lesson-intro-screen"><div class="lesson-intro-content"><span class="slide-type">今天要弄明白的问题</span><h1>${fixtureQuestion}</h1><p>先听小知一步步讲清楚。讲解时只看文字和图解，讲完以后再亲手拨琴弦验证。</p><div class="narration-cue lesson-intro-cue"><span aria-hidden="true">${state.playing ? '◉' : '▶'}</span><div><strong>${state.playing ? '小知正在介绍今天的问题' : '问题介绍旁白已播完'}</strong><small>先看和听三小段讲解，讲完后再亲手拨琴弦验证。</small></div><button data-action="replay-screen-narration" aria-label="重听问题介绍旁白">重听</button></div><div class="intro-string" aria-hidden="true"><i></i><span></span><i></i></div><button class="btn primary" data-action="start-lesson">开始讲解 <span aria-hidden="true">→</span></button></div></main></div>`;
  }
  const speech = activeSegment[2];
  const tutorHeader = `<div class="tutor-id"><span class="tutor-avatar">小知</span><div><strong>对话</strong><small>${state.segmentLeadIn ? '先看一眼画面，马上开始' : vacuum ? '正在回答关联追问' : state.playing ? `正在讲解“${activeSegment[0]}”` : state.lessonComplete ? '核心讲解已完成' : '讲解已暂停'}</small></div></div>`;
  const dialogueThread = `<div class="dialog-thread">
    ${vacuum && state.conversationQuestion ? `<div class="dialog-message child"><small>你问</small><p>${escapeHtml(state.conversationQuestion)}</p></div><div class="dialog-message tutor"><small>小知老师</small><p>${state.returningFromVacuum ? '这个问题弄明白了。我们再回到琴弦，继续把原来的问题弄清楚。' : '这个问题把我们从“琴弦怎样振动”带到了“声音怎样传播”。我们先把它弄明白。'}</p></div>` : ''}
    <div class="dialog-message tutor"><small>小知老师 · ${state.playing ? '正在讲解' : '当前画面'}</small><p>${speech}</p></div>
    <div class="key-point">${vacuum ? '琴弦仍会振动；没有空气接力，声音不能通过空气传到耳朵。' : '同一根弦更用力拨，主要改变振幅和响度；频率和音调基本不变。'}</div>
  </div>`;
  const recordingState = state.followupRecording ? `<div class="voice-recording-state" role="status"><span class="voice-recording-bars" aria-hidden="true"><i></i><i></i><i></i><i></i></span><strong>正在听…</strong></div>` : '';
  const interruptTools = `<div class="interrupt-tools fixed-followups"><div class="fixed-followup-label">${vacuum ? '关联主题播放中' : '讲解中也可以随时追问（固定演示）'}</div>
    <label class="followup-field" for="fixed-followup-input">追问</label>${recordingState}<div class="followup-composer"><input id="fixed-followup-input" value="${vacuum ? '' : '如果没有空气呢？'}" readonly aria-readonly="true" ${vacuum ? 'aria-label="当前主题无预设追问"' : 'aria-label="预设追问：如果没有空气呢？"'} /><button class="followup-voice ${state.followupRecording ? 'recording' : ''}" data-action="interrupt" ${vacuum || state.followupRecording ? 'disabled' : ''} aria-label="模拟语音录入"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="3" width="8" height="12" rx="4"></rect><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6"></path></svg></button><button class="followup-send" data-action="send-followup" ${vacuum || state.followupRecording ? 'disabled' : ''} aria-label="发送预设追问">发送</button></div>
    <small class="followup-demo-note">${vacuum ? '这个主题暂时不能继续追问。' : state.followupRecording ? '正在演示语音录入，不会调用麦克风。' : state.followupTranscriptReady ? '语音已转成同一个预设问题，现在可以发送。' : '可以直接发送预设文字，也可以点击麦克风体验语音转写。'}</small>
  </div>`;
  const lessonAction = migrationReady() ? '<button class="btn primary lesson-complete-action" data-screen="migration">进入迁移验证</button>' : '';
  const mobileLessonAction = migrationReady() ? '<div class="mobile-lesson-action"><button class="btn primary" data-screen="migration">进入迁移验证</button></div>' : '';
  const narrativeVisual = vacuum ? `<div class="scene-canvas vacuum"><span class="scene-caption">介质：真空</span><div class="bell-jar"><div class="vacuum-string"><span></span></div><div class="vacuum-particles"></div><strong>琴弦仍在振动</strong><small>没有空气把振动传到耳朵</small></div></div>` : state.segment === 1 ? `<div class="fair-compare-visual"><div class="single-string-diagram"><i></i><span></span><i></i></div><div class="condition-row" data-reveal-at="26"><span>弦长不变</span><span>松紧不变</span><span>粗细不变</span></div><strong data-reveal-at="68">只改变：拨弦力度</strong></div>` : state.segment === 2 ? `<div class="comparison-diagram"><div class="vibration-card light"><span>轻轻拨</span><div class="vibration-line"><i></i><svg viewBox="0 0 320 110"><line x1="0" y1="55" x2="320" y2="55"/><path d="M0 55 C12 38 28 38 40 55 S68 72 80 55 S108 38 120 55 S148 72 160 55 S188 38 200 55 S228 72 240 55 S268 38 280 55 S308 72 320 55"/></svg><i></i></div><small><b>振幅较小</b><em>频率不变</em></small></div><div class="vibration-card strong" data-reveal-at="42"><span>用力拨</span><div class="vibration-line"><i></i><svg viewBox="0 0 320 110"><line x1="0" y1="55" x2="320" y2="55"/><path d="M0 55 C12 18 28 18 40 55 S68 92 80 55 S108 18 120 55 S148 92 160 55 S188 18 200 55 S228 92 240 55 S268 18 280 55 S308 92 320 55"/></svg><i></i><span class="sound-arcs" aria-hidden="true"><b></b><b></b></span></div><small><b>振幅更大</b><em>频率不变</em></small></div><div class="comparison-summary"><span>摆动范围变大</span><strong>往返次数相近</strong></div></div>` : `<div class="principle-chain"><div data-reveal-at="18"><span>力气变大</span><b>→</b><span class="green">振幅变大</span><b>→</b><strong>声音更响</strong></div><div data-reveal-at="48"><span>同一根弦</span><b>→</b><span class="blue">频率基本不变</span><b>→</b><strong>音调基本不变</strong></div><p data-reveal-at="78">振幅看“摆多开”，频率看“振多快”。</p></div>`;
  const practiceVisual = `<div class="practice-stage"><div class="practice-heading"><div><span>轮到你了</span><h2>现在你可以动手来试试</h2><p>先轻轻拨一次，再用力拨一次，亲手验证刚才的发现。</p></div><span class="practice-status">${operationsComplete() ? '两次都完成' : state.operations.light ? '还差用力拨' : '先从轻拨开始'}</span></div><div class="dual-experiment">
    <section class="experiment-pane string-pane"><header><strong>琴弦慢放</strong><span>${state.slow ? '0.5× 慢放' : '1×'}</span></header><div class="string-apparatus"><span class="air-particles" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></span><span class="wood-post left"></span><span class="wood-post right"></span><svg viewBox="0 0 400 110" preserveAspectRatio="none" aria-hidden="true"><path class="string-ghost" d="M30 70 Q200 50 370 70"/><path class="string-curve" data-base-curve="${stringCurve}" d="M30 70 Q200 ${stringCurve} 370 70"/></svg><span class="experiment-sound-arcs" aria-hidden="true"><i></i><i></i></span><button class="string-drag-target" data-string-drag aria-label="拖动琴弦，松开完成拨弦" style="--drag-y:${stringCurve - 70}px"><span></span></button></div><div class="experiment-note"><i class="green"></i>${operationsComplete() ? (state.force === 'strong' ? '用力拨：振幅更大' : '轻拨：振幅较小') : state.operations.light ? '轻拨已记录，现在请用力拨' : '先轻轻拖动琴弦并松开'}</div></section>
    <section class="experiment-pane record-pane"><header><strong>振动记录图</strong><span>固定位置随时间</span></header><svg class="record-svg" viewBox="0 0 400 100" preserveAspectRatio="none" role="img" aria-label="振动记录图，同一时间内往返次数基本相同"><line x1="0" y1="50" x2="400" y2="50"/><path d="${recordPath}"/><g class="amplitude-guide"><line x1="366" y1="${50-amplitude}" x2="366" y2="${50+amplitude}"/><line x1="357" y1="${50-amplitude}" x2="375" y2="${50-amplitude}"/><line x1="357" y1="${50+amplitude}" x2="375" y2="${50+amplitude}"/></g></svg><div class="record-labels"><span class="amplitude-label">振幅${state.force === 'strong' ? '变大' : '较小'}</span><span class="frequency-label">频率基本不变</span></div></section></div><div class="scene-controls">${state.dragFailures >= 2 ? `<button class="control-button ${state.force === 'light' ? 'active' : ''}" data-force="light">轻拨一次</button><button class="control-button ${state.force === 'strong' ? 'active' : ''}" data-force="strong" ${state.operations.light ? '' : 'disabled'}>用力拨一次</button>` : ''}${operationsComplete() ? `<button class="control-button ${state.slow ? 'active' : ''}" data-action="slow">${state.slow ? '恢复速度' : '慢放观察'}</button>` : ''}</div></div>`;
  return `<div class="app-screen explore-screen">${exploreHeader()}<main class="explore-main">
    <section class="visual-workspace">
      <div class="lesson-slide ${state.segmentLeadIn ? 'segment-prelude' : ''} ${state.lessonComplete && !vacuum ? 'practice-slide' : ''}">
        <div class="lesson-title"><div><span class="slide-type">${state.lessonComplete && !vacuum ? '动手验证' : '核心讲解 · 图解与动画'}</span><h1>${state.lessonComplete && !vacuum ? '把刚才的发现亲手验证一次' : activeSegment[0]}</h1><p>${state.lessonComplete && !vacuum ? '讲解已经结束，互动区现在才开放。' : activeSegment[1]}</p></div><span class="result-tag ${vacuum ? 'warn' : ''}">${vacuum ? '关联主题' : state.lessonComplete ? '可以操作' : `自动播放 ${state.segment}/3`}</span></div>
        ${mobileLessonAction}
        ${state.lessonComplete && !vacuum ? practiceVisual : `<div class="slide-body narrative-slide">
          <div class="slide-copy">
            ${vacuum && state.returningFromVacuum ? `<div class="return-transition-card"><strong>关联问题讲完了</strong><p>如果你弄懂了，让我们再回到刚才的琴弦振动，接着往下看吧～</p><small>马上继续</small></div>` : ''}
            ${state.segmentLeadIn ? '<div class="segment-prelude-cue" role="status">先看一眼画面，马上开始</div>' : ''}
            <p class="slide-lead" data-reveal-at="8">${formatTeachingText(activeSegment[2])}</p>
            <div class="slide-points">${activeSegment[3].map((point, index) => `<div data-reveal-at="${22 + index * 20}"><span>${index + 1}</span><strong>${formatTeachingText(point)}</strong></div>`).join('')}</div>
            ${state.segment === 3 ? `<div class="slide-takeaway" data-reveal-at="82">${vacuum ? '<strong>关键结论</strong><span>物体仍振动，但声音不能穿过真空传播。</span>' : '<strong>关键结论</strong><span>更用力主要让声音更响，音调基本不变。</span>'}</div>` : ''}
          </div>
          <div class="slide-visual-wrap ${vacuum ? 'branch-visual' : 'narrative-visual-wrap'}">${narrativeVisual}</div>
        </div>`}
      </div>
      <div class="segment-area">
        <div class="segment-tabs" role="tablist" aria-label="当前主题的讲解子片段">${segmentSets.map((segment, index) => { const number = index + 1; return `<button class="${state.segment === number ? 'active' : ''}" data-segment="${number}" role="tab" aria-selected="${state.segment === number}" ${state.returningFromVacuum ? 'disabled' : ''}><span>${number}</span>${segment[0]}</button>`; }).join('')}</div>
        <div class="segment-player"><button class="player-skip" data-action="previous-segment" aria-label="上一段" ${state.returningFromVacuum ? 'disabled' : ''}>|◀</button><button class="play-button" data-action="toggle-play" aria-label="${state.returningFromVacuum ? '正在播放主题连接语' : state.playing ? `暂停“${activeSegment[0]}”` : `继续“${activeSegment[0]}”`}" ${state.returningFromVacuum ? 'disabled' : ''}>${state.returningFromVacuum ? '•••' : state.playing ? 'Ⅱ' : '▶'}</button><div class="timeline-control"><input type="range" min="0" max="100" value="${segmentProgress}" data-progress aria-label="${activeSegment[0]}播放进度" ${state.returningFromVacuum ? 'disabled' : ''}><small data-timeline-clock data-segment-title="${activeSegment[0]}">${formatClock(timelineDuration * segmentProgress / 100)} / ${formatClock(timelineDuration)} · ${state.returningFromVacuum ? '正在连接两个主题' : activeSegment[0]}</small></div><button class="player-skip" data-action="next-segment" aria-label="下一段" ${state.returningFromVacuum ? 'disabled' : ''}>▶|</button></div>
      </div>
    </section>
    <aside class="tutor-panel">${tutorHeader}${dialogueThread}${interruptTools}${lessonAction}</aside>
  </main>
  ${!state.mobileTutorOpen ? `<button class="mobile-tutor-widget" data-action="open-mobile-tutor" aria-label="${vacuum ? '打开小知对话' : '按住小知语音提问，轻点打开对话'}"><span class="mobile-tutor-bubble"><i class="tutor-hold-wave" aria-hidden="true"><b></b><b></b><b></b></i><strong>${vacuum ? '正在回答' : '按住问老师'}</strong></span><span class="mobile-tutor-character">小知</span></button>` : ''}
  ${state.mobileTutorOpen ? `<div class="mobile-tutor-backdrop"><section class="mobile-tutor-drawer" aria-label="小知对话"><div class="mobile-drawer-head">${tutorHeader}<button data-action="close-mobile-tutor" aria-label="收起对话">×</button></div>${dialogueThread}${interruptTools}${lessonAction}</section></div>` : ''}
  </div>`;
}

function renderMigration() {
  const xylophone = state.migrationStage === 'xylophone';
  const conclusionOptions = [['higher', '会更高'], ['same', '基本不变']];
  const reasonOptions = [['amplitude', '振幅变大，频率基本不变', '更用力主要让振动幅度变大，每秒振动次数基本不变。'], ['frequency', '频率变高，振幅也变大', '更用力让每秒振动次数变多，所以音调变高。']];
  const loudnessOptions = [['louder', '声音会更响'], ['same', '响度基本不变']];
  return `<div class="app-screen">${appHeader({ back: true, title: xylophone ? '木琴迁移' : '音叉迁移', subtitle: '分别验证结论和原因' })}<main class="screen-body migration-screen">
    <div class="content-wide"><div class="eyebrow">${xylophone ? '提示后换一个新情境' : '第一次迁移验证'}</div><h1>${xylophone ? '更用力敲同一块音条，音调会更高吗？' : '更用力敲同一个音叉，音调会更高吗？'}</h1><p>${xylophone ? '同一块音条，长度、厚度和材料不变，只改变敲击力度。' : '同一个音叉不更换，只改变敲击力度。先把结论和原因分别想清楚。'}</p>
      ${xylophone ? '<div class="hint-box migration-hint"><strong>针对性提示</strong><br>分别观察振动幅度和相同时间内的振动次数。</div>' : ''}
      <div class="migration-layout"><div class="transfer-object ${xylophone ? 'xylophone-object' : 'fork-object'}">${xylophone ? '<div class="mallet light"></div><div class="mallet strong"></div><div class="xylophone-bar"></div><span class="object-caption">同一块音条 · 轻敲 / 用力敲</span>' : '<div class="tuning-fork"><div class="fork-shape"><span class="fork-prong left"></span><span class="fork-prong right"></span><span class="fork-stem"></span></div></div><span class="object-caption">同一个音叉 · 轻敲 / 用力敲</span>'}</div>
        <div class="transfer-answers">${xylophone ? `<fieldset><legend><span>1</span> 响度怎样变化</legend><div class="transfer-choice-grid">${loudnessOptions.map(([id,label])=>`<button class="choice ${state.migrationLoudness===id?'selected':''}" data-migration-loudness="${id}"><span class="choice-marker">${state.migrationLoudness===id?'✓':''}</span><strong>${label}</strong></button>`).join('')}</div></fieldset>` : ''}<fieldset><legend><span>${xylophone ? '2' : '1'}</span> 音调怎样变化</legend><div class="transfer-choice-grid">${conclusionOptions.map(([id,label])=>`<button class="choice ${state.migrationConclusion===id?'selected':''}" data-migration-conclusion="${id}"><span class="choice-marker">${state.migrationConclusion===id?'✓':''}</span><strong>${label}</strong></button>`).join('')}</div></fieldset><fieldset><legend><span>${xylophone ? '3' : '2'}</span> 为什么</legend><div class="choice-list">${reasonOptions.map(([id,label,note])=>`<button class="choice ${state.migrationReason===id?'selected':''}" data-migration-reason="${id}"><span class="choice-marker">${state.migrationReason===id?'✓':''}</span><span><strong>${label}</strong><small>${note}</small></span></button>`).join('')}</div></fieldset>
        <div class="button-row end"><button class="btn primary" data-action="check-migration" ${state.migrationConclusion && state.migrationReason && (!xylophone || state.migrationLoudness) ? '' : 'disabled'}>提交验证</button></div></div>
      </div>
    </div>
  </main></div>`;
}

function renderFeedback() {
  const options = [['clear','讲明白了'],['little','还有一点不懂'],['unclear','没讲明白']];
  return `<div class="app-screen">${appHeader({ back: true })}<main class="screen-body centered"><div class="content-narrow" style="text-align:center">
    <h1>刚才的讲解对你有帮助吗？</h1><p>这不是打分，只是帮助我们换一种更合适的讲法。</p>
    <div class="feedback-grid">${options.map(([id,label])=>`<button class="feedback-option ${state.feedback===id?'selected':''}" data-feedback="${id}">${label}</button>`).join('')}</div>
    ${state.feedback && state.feedback !== 'clear' ? '<div class="choice-list" style="text-align:left"><button class="choice">讲得太快</button><button class="choice">动画没看懂</button><button class="choice">想换一种讲法</button></div>' : ''}
    <div class="button-row center"><button class="btn ghost" data-screen="complete">跳过</button><button class="btn primary" data-screen="complete" ${state.feedback ? '' : 'disabled'}>完成</button></div>
  </div></main></div>`;
}

function renderComplete() {
  const conclusionPassed = state.migrationConclusion === 'same';
  const reasonPassed = state.migrationReason === 'amplitude';
  const result = conclusionPassed && reasonPassed ? '自己弄懂了' : conclusionPassed || reasonPassed ? '部分理解' : '建议陪一陪';
  const completionWay = state.transferResult === 'first-pass' ? '首次通过' : state.transferResult === 'prompted-pass' ? '提示后通过' : '尚未完整通过';
  return `<div class="app-screen complete-screen"><main class="screen-body centered"><div class="result-wrap">
    <div class="completion-mark">✓</div><h1>${result}</h1><p class="result-subtitle">完成方式：${completionWay}</p>
    <div class="result-evidence">
      <div><span>实验操作</span><strong>${operationsComplete() ? '轻拨、用力拨、慢放' : '尚未完成轻拨和用力拨'}</strong><em>${operationsComplete() ? '已完成' : '未完成'}</em></div>
      <div><span>关联追问</span><strong>${state.followupsCompleted.vacuum ? '没有空气时，琴弦仍振动' : '尚未完成真空追问'}</strong><em>${state.followupsCompleted.vacuum ? '声音传不过去' : '未完成'}</em></div>
      <div><span>迁移结论</span><strong>${conclusionPassed ? '通过' : '未通过'}</strong><em>${state.migrationStage === 'xylophone' ? '木琴音条' : '同一音叉'}</em></div>
      <div><span>因果解释</span><strong>${reasonPassed ? '通过' : '未通过'}</strong><em>振幅与频率</em></div>
      <div><span>家庭协助</span><strong>未确认</strong><em>未通过行为推断</em></div>
    </div>
    <section class="core-finding"><span>核心发现</span><p>同一根弦更用力拨，主要改变振幅和响度；频率和音调基本不变。</p></section>
    <div class="result-actions"><button class="btn primary" data-action="open-survey">填写问卷，申请加入内测群</button><button class="btn" data-action="restart-demo">重新体验</button></div>
    <p class="demo-disclaimer">本次内容为固定演示，不代表动态生成能力已经上线。</p>
  </div></main></div>`;
}

function renderHistory() {
  const selected = records[state.historySelected];
  const selectedEvidence = parentRecordsData[state.historySelected] || parentRecordsData[0];
  const detailContent = `<div class="eyebrow">${selected.date}</div><h2>${selected.title}</h2><p>这条记录通过保存的对话、场景快照和操作事件重建，不重新调用模型。</p>
    <div class="evidence-timeline"><div class="evidence-row"><strong>问题起点</strong><p>${selectedEvidence.misconception}</p><small>问题确认节点</small></div><div class="evidence-row"><strong>关键操作</strong><p>${selectedEvidence.intervention}</p><small>互动讲解节点</small></div><div class="evidence-row"><strong>迁移结果</strong><p>${selectedEvidence.transfer}</p><small>${selectedEvidence.statusLabel}</small></div></div>
    <div class="button-row"><button class="btn" data-action="replay">从头回放</button><button class="btn primary" data-action="continue-node">从关键节点继续问</button></div>`;
  return `<div class="app-screen">${appHeader({ back: true })}<main class="screen-body"><div class="content-wide">
    <div class="section-heading"><div><h1>我的探索</h1><p>回看当时的问题和操作，或从关键节点继续问。</p></div></div>
    <div class="list-layout"><div class="record-list">${records.map((r,i)=>`<div class="history-record-entry"><button class="record-row ${state.historySelected===i?'active':''}" data-record="${i}" aria-expanded="${state.viewport === 'mobile' && state.historyExpanded === i}"><strong>${r.title}</strong><small>${r.date} · ${r.topics} 个主题 · ${r.questions} 次追问</small><span class="record-row-footer"><span class="result-tag ${r.result==='部分理解'?'warn':''}">${r.result}</span><span class="history-disclosure">${state.viewport === 'mobile' && state.historyExpanded === i ? '收起 ↑' : '查看详情 ↓'}</span></span></button>${state.historyExpanded === i ? `<section class="mobile-history-detail">${detailContent}</section>` : ''}</div>`).join('')}</div>
      <section class="record-detail">${detailContent}</section></div>
  </div></main>${state.historyDetail ? `<div class="modal-backdrop"><div class="modal" style="position:relative"><button class="modal-close" data-action="close-history-modal">×</button><div class="eyebrow">新分支</div><h2>从“慢放观察”继续</h2><p>已继承当时的琴弦力度、慢放速度、对话摘要和学习目标。原记录不会被改写。</p><input class="fake-input" value="如果换一根更短的弦呢？"><div class="button-row end"><button class="btn primary" data-action="start-branch">开始新探索</button></div></div></div>` : ''}</div>`;
}

function renderParentPin() {
  return `<div class="app-screen">${appHeader({ back: true, title: '家长验证', subtitle: '儿童模式已暂停', parent: false })}<main class="screen-body centered"><div class="content-narrow" style="text-align:center">
    <h1>输入家长 PIN</h1><p>家长结论和数据设置不会显示在儿童模式。</p><div class="pin-inputs"><span class="pin-box">•</span><span class="pin-box">•</span><span class="pin-box">•</span><span class="pin-box">•</span></div>
    <button class="btn primary" data-screen="parentToday">进入家长工作台</button><div class="helper" style="margin-top:14px">原型 PIN：任意四位</div>
  </div></main></div>`;
}

function parentShell(content, active, title, description) {
  const items = [['parentToday','今日'],['parentRecords','探索记录'],['parentInsights','近期画像'],['parentSettings','设置']];
  return `<div class="app-screen"><div class="parent-shell"><aside class="parent-sidebar"><div class="rail-brand"><span class="rail-mark">PV</span><div><strong>家长工作台</strong><small>小宇 · 三年级</small></div></div><nav class="parent-nav">${items.map(([id,label])=>`<button class="${active===id?'active':''}" data-screen="${id}">${label}</button>`).join('')}</nav><button class="parent-exit" data-screen="home">返回儿童模式</button></aside>
    <section class="parent-content"><header class="parent-topbar"><div><strong>${title}</strong><small style="display:block;color:var(--muted);margin-top:3px">${description}</small></div><span class="helper">7 月 17 日</span></header><main class="parent-body">${content}</main></section></div></div>`;
}

function renderParentToday() {
  const todayIds = ['sound-string', 'fraction-size', 'shadow-length'];
  const todayRecords = parentRecordsData.filter(record => todayIds.includes(record.id));
  const content = `<div class="metrics"><button class="metric" data-parent-filter="all"><span>今天问了</span><strong>3</strong><small>查看今天的全部探索</small></button><button class="metric" data-parent-filter="understood"><span>自己弄懂了</span><strong>1</strong><small>锚定到“已理解”记录</small></button><button class="metric" data-parent-filter="help"><span>建议陪一陪</span><strong>1</strong><small>锚定到需要陪伴的记录</small></button></div>
    <section class="parent-section"><div class="section-heading"><div><h2>今天的探索</h2><p>点击一条记录查看误解、干预与迁移证据。</p></div></div><div class="parent-list">${todayRecords.map(record => `<button class="parent-list-row" data-parent-record="${record.id}"><span><strong>${record.title}</strong><small>${record.date.replace('今天 ', '')} · ${record.subject} · ${record.independent}</small></span><span>${record.subject.split(' · ')[0]}</span><span class="result-tag ${record.status === 'partial' ? 'warn' : record.status === 'help' ? 'help' : ''}">${record.statusLabel}</span></button>`).join('')}</div></section>`;
  return parentShell(content, 'parentToday', '今日', '看孩子今天是否真正弄懂');
}

function renderParentRecordDetail(record) {
  return `<section class="parent-record-detail"><div class="eyebrow">${record.date} · ${record.subject}</div><h2>${record.title}</h2><div class="report-summary"><div><small>最终结果</small><strong>${record.statusLabel}</strong></div><div><small>是否独立</small><strong>${record.independent}</strong></div><div><small>儿童反馈</small><strong>${record.feedback}</strong></div></div>
    <div class="parent-section"><h3>关键学习证据</h3><div class="evidence-timeline"><div class="evidence-row"><strong>原来的想法</strong><p>${record.misconception}</p><small>作为本次讲解的待验证假设</small></div><div class="evidence-row"><strong>采取的视觉干预</strong><p>${record.intervention}</p><small>记录实际呈现和操作过程</small></div><div class="evidence-row"><strong>迁移证据</strong><p>${record.transfer}</p><small>${record.statusLabel}</small></div></div></div>
    <div class="notice ${record.status === 'help' ? 'warn' : 'info'}">${record.advice}</div>
    <div class="button-row"><button class="btn" data-action="full-process">展开完整探索过程</button><button class="btn danger" data-action="delete-record">删除本次记录</button></div>
  </section>`;
}

function renderParentRecords() {
  const filterOptions = [['all', '全部记录'], ['understood', '已理解'], ['partial', '部分理解'], ['help', '建议陪一陪']];
  const statusOrder = ['understood', 'partial', 'help'];
  const visibleRecords = state.parentFilter === 'all' ? parentRecordsData : parentRecordsData.filter(record => record.status === state.parentFilter);
  const statusLabels = { understood: '已理解', partial: '部分理解', help: '建议陪一陪' };
  const groups = statusOrder.filter(status => state.parentFilter === 'all' || state.parentFilter === status).map(status => [status, visibleRecords.filter(record => record.status === status)]).filter(([, items]) => items.length);
  const content = `<div class="section-heading parent-record-heading"><div><h1>探索记录</h1><p>按学习结果分类，选择记录查看误解、干预和迁移证据。</p></div></div>
    <div class="parent-record-filters" aria-label="探索记录分类">${filterOptions.map(([id, label]) => `<button class="${state.parentFilter === id ? 'active' : ''}" data-parent-category="${id}">${label}<span>${id === 'all' ? parentRecordsData.length : parentRecordsData.filter(record => record.status === id).length}</span></button>`).join('')}</div>
    <div class="parent-record-layout" id="parent-records-list">
      <div class="parent-record-groups">${groups.map(([status, items]) => `<section class="parent-record-group" id="parent-records-${status}"><div class="parent-record-group-title"><h2>${statusLabels[status]}</h2><span>${items.length} 条</span></div>${items.map(record => `<div class="parent-record-entry"><button class="parent-record-row ${state.parentRecordExpanded === record.id ? 'active' : ''}" id="parent-record-${record.id}" data-parent-record="${record.id}" aria-expanded="${state.parentRecordExpanded === record.id}"><span><small>${record.date} · ${record.subject}</small><strong>${record.title}</strong><em>${record.intervention}</em></span><span class="record-row-side"><span class="result-tag ${record.status === 'partial' ? 'warn' : record.status === 'help' ? 'help' : ''}">${record.statusLabel}</span><span class="record-disclosure">${state.parentRecordExpanded === record.id ? '收起 ↑' : '查看详情 ↓'}</span></span></button>${state.parentRecordExpanded === record.id ? renderParentRecordDetail(record) : ''}</div>`).join('')}</section>`).join('')}</div>
    </div>`;
  return parentShell(content, 'parentRecords', '探索记录', '误解、干预与迁移证据') + deleteModal();
}

function deleteModal() {
  if (!state.deleteModal) return '';
  return `<div class="modal-backdrop"><div class="modal"><h2>删除这次探索？</h2><p>将同时删除对话、场景快照、互动操作和由此产生的个体认知记录。由这条记录继续产生的后代分支也会删除。</p><div class="notice danger">此操作在生产环境中不可撤销。</div><div class="button-row end"><button class="btn" data-action="cancel-delete">取消</button><button class="btn danger" data-action="confirm-delete">确认删除</button></div></div></div>`;
}

function renderParentInsights() {
  const content = `<div class="notice warn"><strong>演示档案</strong><br>以下画像使用独立的 7 次审核夹具记录，只用于测试家长是否理解证据强弱，不代表当前 MVP 已具备真实跨会话归纳能力。</div>
    <div class="section-heading" style="margin-top:22px"><div><h1>最近 14 天</h1><p>7 次有效探索 · 覆盖 3 个概念</p></div></div>
    <div class="insight-list"><div class="insight-row"><div class="insight-head"><strong>变量并排比较对孩子更有效</strong><span class="evidence-strength">证据较充分 · 5 次</span></div><p>在分数、声音和影子主题中，并排改变一个变量后，迁移题所需提示更少。</p></div><div class="insight-row"><div class="insight-head"><strong>仍会混淆“更大”和“更多份”</strong><span class="evidence-strength">需要继续观察 · 2 次</span></div><p>分数主题中两次出现类似选择，但目前不足以形成稳定判断。</p></div><div class="insight-row"><div class="insight-head"><strong>近期主动追问声音传播</strong><span class="evidence-strength">近期趋势 · 3 次</span></div><p>从琴弦延伸到真空、耳朵和水下传播，属于相关兴趣方向。</p></div></div>`;
  return parentShell(content, 'parentInsights', '近期学习画像', '有时间范围和证据强度的阶段观察');
}

function renderParentSettings() {
  const s = state.settings;
  const content = `<div class="section-heading"><div><h1>设置</h1><p>管理课外范围、历史保存与儿童数据。</p></div></div><div class="settings-list">
    <div class="setting-row"><div><strong>孩子年级</strong><small>控制语言与知识难度</small></div><select class="fake-input" style="width:140px"><option>三年级</option><option>四年级</option></select></div>
    <div class="setting-row"><div><strong>教材版本</strong><small>未识别时使用通用课标知识</small></div><select class="fake-input" style="width:140px"><option>人教版</option><option>暂不设置</option></select></div>
    <div class="setting-row"><div><strong>相关课外探索</strong><small>只允许从课内问题进入相关安全内容</small></div><button class="switch ${s.explore?'on':''}" data-setting="explore" aria-label="切换课外探索"></button></div>
    <div class="setting-row"><div><strong>保存探索历史</strong><small>关闭后当次仍可完成，退出后不能回放或继续</small></div><button class="switch ${s.history?'on':''}" data-setting="history" aria-label="切换历史保存"></button></div>
    <div class="setting-row"><div><strong>保存期限</strong><small>到期自动清除文字对话和结构化互动记录</small></div><select class="fake-input" style="width:140px"><option>90 天</option><option>30 天</option><option>直到手动删除</option></select></div>
    <div class="setting-row"><div><strong>原始照片和语音</strong><small>识别和转写完成后删除，不长期保存</small></div><span class="result-tag">默认删除</span></div>
  </div><div class="button-row"><button class="btn danger" data-action="clear-all">清空全部历史</button></div>`;
  return parentShell(content, 'parentSettings', '设置', '权限、保存期限和数据删除') + deleteModal();
}

function renderFailure() {
  return `<div class="app-screen">${appHeader({ back: true })}<main class="screen-body centered"><div class="loading-wrap"><div class="completion-mark" style="background:var(--yellow);margin:0 auto 20px">!</div><h1>这次没能准备好画面</h1><p>你的问题和刚才的进度还在。可以再试一次，或先换一个问题。</p><div class="notice warn">固定夹具状态：开头达到 15 秒且没有可用的保底内容。</div><div class="button-row center"><button class="btn primary" data-screen="loading">再试一次</button><button class="btn" data-screen="askVoice">换个问题</button><button class="btn ghost" data-screen="home">回首页</button></div></div></main></div>`;
}

function render() {
  const renderers = {
    publicEntry: renderPublicEntry, ask: renderAsk,
    onboarding: renderOnboarding, home: renderHome, askVoice: renderAskVoice, askPhoto: renderAskPhoto,
    confirm: renderConfirm, loading: renderLoading, explore: renderExplore,
    migration: renderMigration, feedback: renderFeedback, complete: renderComplete, history: renderHistory,
    parentPin: renderParentPin, parentToday: renderParentToday, parentRecords: renderParentRecords,
    parentInsights: renderParentInsights, parentSettings: renderParentSettings, failure: renderFailure
  };
  app.innerHTML = (renderers[state.screen] || renderHome)();
  app.className = `device ${state.viewport}`;
  const [title, description] = screens[state.screen] || screens.home;
  titleEl.textContent = title;
  descriptionEl.textContent = description;
  document.body.classList.toggle('public-demo', !researchMode);
  renderNav();
  updateTimelineUi();
}

function renderNav() {
  nav.innerHTML = navGroups.map(([group, ids]) => `<div class="nav-group"><div class="nav-group-label">${group}</div>${ids.map(id => `<button class="prototype-nav-button ${state.screen === id ? 'active' : ''}" data-screen="${id}">${screens[id][0]}</button>`).join('')}</div>`).join('');
}

function goTo(screen) {
  if (!screens[screen] && screen !== 'askPhoto') return;
  clearTimeout(loadingTimer);
  loadingTimer = null;
  resetTutorHold();
  if (screen !== 'explore') stopCurrentNarration();
  if (screen !== 'explore') {
    clearTimeout(followupRecordingTimer);
    followupRecordingTimer = null;
    state.followupRecording = false;
    state.followupTranscriptReady = false;
    state.pendingSnapshot = null;
  }
  state.screen = screen;
  if (screen === 'explore') state.playing = state.coreStarted;
  if (screen !== 'explore') state.mobileTutorOpen = false;
  render();
  if (screen === 'loading') {
    loadingTimer = setTimeout(() => {
      state.coreStarted = false;
      state.segment = 1;
      state.progress = 0;
      goTo('explore');
    }, 3200);
  } else if (screen === 'explore' && state.playing) {
    startSegmentPlayback({ fromProgress: state.progress });
  } else if (screen === 'explore' && !state.coreStarted) {
    playScreenNarration('explore');
  }
}

function scrollToParentRecord(anchorId) {
  requestAnimationFrame(() => document.getElementById(anchorId)?.scrollIntoView({ block: 'start' }));
}

document.addEventListener('click', (event) => {
  const screenTarget = event.target.closest('[data-screen]');
  if (screenTarget && !screenTarget.disabled) {
    if (screenTarget.dataset.screen === 'askPhoto') { state.inputSource = 'photo'; state.questionText = fixtureQuestion; }
    if (screenTarget.dataset.screen === 'askVoice') { state.inputSource = 'voice'; state.questionText = fixtureQuestion; }
    if (screenTarget.dataset.screen === 'confirm' && state.screen === 'ask') { state.inputSource = state.askMode; state.questionText = fixtureQuestion; }
    goTo(screenTarget.dataset.screen); return;
  }
  const askMode = event.target.closest('[data-ask-mode]');
  if (askMode) {
    state.askMode = askMode.dataset.askMode;
    if (state.askMode === 'photo') state.inputSource = 'photo';
    if (state.askMode === 'voice') state.inputSource = 'voice';
    if (state.askMode === 'text') state.inputSource = 'text';
    showToast(state.askMode === 'photo' ? '拍照入口已准备，Demo 使用固定图片' : state.askMode === 'voice' ? '语音入口已准备，Demo 使用固定转写' : '文字入口已准备');
    render(); return;
  }
  const parentFilter = event.target.closest('[data-parent-filter]');
  if (parentFilter) {
    state.parentFilter = parentFilter.dataset.parentFilter;
    state.parentRecordExpanded = null;
    const firstMatch = state.parentFilter === 'all' ? parentRecordsData[0] : parentRecordsData.find(record => record.status === state.parentFilter);
    if (firstMatch) state.parentRecordSelected = firstMatch.id;
    goTo('parentRecords');
    scrollToParentRecord(state.parentFilter === 'all' ? 'parent-records-list' : `parent-records-${state.parentFilter}`);
    return;
  }
  const parentCategory = event.target.closest('[data-parent-category]');
  if (parentCategory) {
    state.parentFilter = parentCategory.dataset.parentCategory;
    state.parentRecordExpanded = null;
    const firstMatch = state.parentFilter === 'all' ? parentRecordsData[0] : parentRecordsData.find(record => record.status === state.parentFilter);
    if (firstMatch) state.parentRecordSelected = firstMatch.id;
    render();
    scrollToParentRecord(state.parentFilter === 'all' ? 'parent-records-list' : `parent-records-${state.parentFilter}`);
    return;
  }
  const parentRecord = event.target.closest('[data-parent-record]');
  if (parentRecord) {
    const selectedRecord = parentRecordsData.find(record => record.id === parentRecord.dataset.parentRecord);
    if (!selectedRecord) return;
    state.parentRecordSelected = selectedRecord.id;
    if (state.screen === 'parentRecords') {
      state.parentRecordExpanded = state.parentRecordExpanded === selectedRecord.id ? null : selectedRecord.id;
      render();
      if (state.parentRecordExpanded) scrollToParentRecord(`parent-record-${selectedRecord.id}`);
    } else {
      state.parentFilter = 'all';
      state.parentRecordExpanded = selectedRecord.id;
      goTo('parentRecords');
      scrollToParentRecord(`parent-record-${selectedRecord.id}`);
    }
    return;
  }
  const viewportTarget = event.target.closest('[data-viewport]');
  if (viewportTarget) {
    state.viewport = viewportTarget.dataset.viewport;
    document.querySelectorAll('[data-viewport]').forEach(b => b.classList.toggle('active', b.dataset.viewport === state.viewport));
    render(); return;
  }
  const force = event.target.closest('[data-force]');
  if (force) {
    const nextForce = force.dataset.force;
    if (nextForce === 'strong' && !state.operations.light) { showToast('先轻拨一次，再用力拨'); return; }
    state.force = nextForce;
    state.operations[nextForce] = true;
    state.playing = false;
    playFixedAudio(audioSources[state.force]);
    render(); return;
  }
  const migration = event.target.closest('[data-migration]');
  if (migration) { state.migrationConclusion = migration.dataset.migration; render(); return; }
  const migrationConclusion = event.target.closest('[data-migration-conclusion]');
  if (migrationConclusion) { state.migrationConclusion = migrationConclusion.dataset.migrationConclusion; render(); return; }
  const migrationReason = event.target.closest('[data-migration-reason]');
  if (migrationReason) { state.migrationReason = migrationReason.dataset.migrationReason; render(); return; }
  const migrationLoudness = event.target.closest('[data-migration-loudness]');
  if (migrationLoudness) { state.migrationLoudness = migrationLoudness.dataset.migrationLoudness; render(); return; }
  const followup = event.target.closest('[data-followup]');
  if (followup && !followup.disabled) { state.followupSelected = followup.dataset.followup; render(); return; }
  const feedback = event.target.closest('[data-feedback]');
  if (feedback) { state.feedback = feedback.dataset.feedback; render(); return; }
  const record = event.target.closest('[data-record]');
  if (record) {
    const index = Number(record.dataset.record);
    state.historySelected = index;
    if (state.viewport === 'mobile') state.historyExpanded = state.historyExpanded === index ? null : index;
    render();
    return;
  }
  const historyEntry = event.target.closest('[data-history-index]');
  if (historyEntry) { state.historySelected = Number(historyEntry.dataset.historyIndex); goTo('history'); return; }
  const knowledge = event.target.closest('[data-knowledge]');
  if (knowledge) {
    state.branch = knowledge.dataset.knowledge === 'vacuum';
    state.branchAvailable = state.branch;
    state.slow = knowledge.dataset.knowledge === 'slow';
    state.force = 'strong';
    state.segment = 1;
    state.lessonComplete = false;
    state.conversationQuestion = '';
    goTo('explore');
    return;
  }
  const topic = event.target.closest('[data-topic]');
  if (topic) {
    stopCurrentNarration();
    if (topic.dataset.topic === 'main' && state.branch && state.savedSnapshot) {
      resumeMainFromInterrupt({ autoplay: true });
      return;
    }
    state.branch = topic.dataset.topic === 'vacuum';
    state.segment = 1;
    state.progress = 0;
    state.lessonComplete = false;
    startSegmentPlayback();
    return;
  }
  const segment = event.target.closest('[data-segment]');
  if (segment && !segment.disabled) {
    stopCurrentNarration();
    state.segment = Number(segment.dataset.segment);
    state.progress = 0;
    state.lessonComplete = false;
    startSegmentPlayback();
    return;
  }
  const setting = event.target.closest('[data-setting]');
  if (setting) { const key = setting.dataset.setting; state.settings[key] = !state.settings[key]; showToast(state.settings[key] ? '设置已开启' : '设置已关闭'); render(); return; }
  const action = event.target.closest('[data-action]')?.dataset.action;
  if (!action) return;
  const handlers = {
    back: () => {
      const targets = { ask: 'publicEntry', confirm: 'ask', askVoice: 'ask', askPhoto: 'ask', loading: 'confirm', migration: 'explore', feedback: 'migration', history: 'home', parentPin: 'home', failure: 'loading' };
      goTo(targets[state.screen] || 'home');
    },
    'replay-screen-narration': () => playScreenNarration(state.screen),
    'start-lesson': () => { state.coreStarted = true; state.segment = 1; state.progress = 0; state.lessonComplete = false; startSegmentPlayback(); },
    captions: () => { state.settings.captions = !state.settings.captions; render(); },
    'onboarding-next': () => { state.onboardingStep = 2; render(); },
    record: () => { if (state.screen === 'askVoice') { state.inputSource = 'voice'; state.questionText = fixtureQuestion; } state.recording = !state.recording; render(); if (state.recording) setTimeout(() => { state.recording = false; render(); showToast(state.screen === 'askPhoto' ? '已添加语音补充' : '已生成固定测试文字'); }, 900); },
    capture: () => { state.captured = true; render(); showToast('已使用固定测试图片'); },
    'edit-question': () => { goTo(state.inputSource === 'photo' ? 'askPhoto' : 'askVoice'); showToast('可以重新说或修改文字'); },
    'retake-photo': () => { state.captured = false; goTo('askPhoto'); showToast('请重新拍照并框选问题'); },
    'toggle-play': () => {
      if (state.playing) {
        stopCurrentNarration();
        state.playing = false;
        render();
      } else {
        startSegmentPlayback({ fromProgress: state.progress });
      }
    },
    slow: () => {
      state.slow = !state.slow;
      if (state.lessonComplete && operationsComplete()) state.followupsCompleted.slow = true;
      if (!state.lessonComplete) startSegmentPlayback({ fromProgress: state.progress });
      else { state.playing = false; render(); playFixedAudio(audioSources[state.force]); }
    },
    'open-mobile-tutor': () => {
      if (suppressNextTutorClick) { suppressNextTutorClick = false; return; }
      state.tutorWasPlaying = state.playing;
      stopCurrentNarration();
      state.playing = false;
      state.mobileTutorOpen = true;
      render();
    },
    'close-mobile-tutor': () => {
      clearTimeout(followupRecordingTimer);
      followupRecordingTimer = null;
      const shouldResume = state.tutorWasPlaying && !state.lessonComplete;
      state.mobileTutorOpen = false;
      state.tutorWasPlaying = false;
      state.followupRecording = false;
      state.followupTranscriptReady = false;
      state.pendingSnapshot = null;
      state.playing = shouldResume;
      if (shouldResume) startSegmentPlayback({ fromProgress: state.progress });
      else render();
    },
    interrupt: () => {
      if (state.branch || state.followupRecording) return;
      state.pendingSnapshot = captureMainSnapshot();
      state.playing = false;
      state.followupRecording = true;
      state.followupTranscriptReady = false;
      stopCurrentNarration();
      render();
      clearTimeout(followupRecordingTimer);
      followupRecordingTimer = setTimeout(() => {
        state.followupRecording = false;
        state.followupTranscriptReady = true;
        followupRecordingTimer = null;
        render();
      }, 1200);
    },
    'send-followup': () => {
      if (state.branch || state.followupRecording) return;
      startVacuumFollowup();
    },
    'previous-segment': () => { state.segment = Math.max(1, state.segment - 1); state.progress = 0; state.lessonComplete = false; startSegmentPlayback(); },
    'next-segment': () => {
      state.segment = Math.min(3, state.segment + 1); state.progress = 0; state.lessonComplete = false; startSegmentPlayback();
    },
    'return-main': () => {
      resumeMainFromInterrupt({ autoplay: true });
    },
    'medium-air': () => { state.branch = false; render(); },
    'check-migration': () => {
      if (!state.migrationConclusion || !state.migrationReason) return;
      if (state.migrationStage === 'xylophone' && !state.migrationLoudness) return;
      const correct = state.migrationConclusion === 'same' && state.migrationReason === 'amplitude' && (state.migrationStage !== 'xylophone' || state.migrationLoudness === 'louder');
      if (correct) { state.transferResult = state.migrationStage === 'fork' ? 'first-pass' : 'prompted-pass'; goTo('feedback'); }
      else if (state.migrationStage === 'fork') { state.migrationAttempted = true; state.migrationStage = 'xylophone'; state.migrationConclusion = null; state.migrationReason = null; state.migrationLoudness = null; render(); showToast('先看提示，再换一个新情境'); }
      else { state.transferResult = 'incomplete'; goTo('feedback'); }
    },
    'open-survey': () => { if (SURVEY_URL) window.location.assign(SURVEY_URL); else showToast('问卷链接尚未开放'); },
    'restart-demo': () => { stopCurrentNarration(); clearTimeout(followupRecordingTimer); followupRecordingTimer = null; state.screen = 'publicEntry'; state.askMode = 'text'; state.force = 'light'; state.operations = { light: false, strong: false }; state.dragFailures = 0; state.followupsCompleted = { slow: false, vacuum: false }; state.followupSelected = 'slow'; state.followupInputMode = 'text'; state.slow = false; state.playing = false; state.segment = 1; state.progress = 0; state.lessonComplete = false; state.coreStarted = false; state.branch = false; state.branchAvailable = false; state.migrationStage = 'fork'; state.migrationConclusion = null; state.migrationReason = null; state.migrationLoudness = null; state.transferResult = null; state.feedback = null; state.savedSnapshot = null; state.pendingSnapshot = null; state.followupRecording = false; state.followupTranscriptReady = false; state.segmentLeadIn = false; state.returningFromVacuum = false; state.tutorWasPlaying = false; render(); },
    replay: () => { state.force = 'strong'; state.slow = true; state.branch = false; state.branchAvailable = true; state.segment = 1; state.lessonComplete = false; goTo('explore'); showToast('正在按保存事件重建现场'); },
    'continue-node': () => { state.historyDetail = true; render(); },
    'close-history-modal': () => { state.historyDetail = false; render(); },
    'start-branch': () => { state.historyDetail = false; state.slow = true; state.branch = false; state.branchAvailable = false; state.segment = 1; state.lessonComplete = false; goTo('explore'); showToast('新分支已创建，原历史未改写'); },
    'full-process': () => showToast('完整过程已展开：共 9 个事件节点'),
    'delete-record': () => { state.deleteModal = true; render(); },
    'cancel-delete': () => { state.deleteModal = false; render(); },
    'confirm-delete': () => { state.deleteModal = false; goTo('parentRecords'); showToast('演示记录已删除'); },
    'clear-all': () => { state.deleteModal = true; render(); }
  };
  handlers[action]?.();
});

document.addEventListener('input', (event) => {
  if (event.target.matches('[data-question-input]') && state.screen === 'askVoice') {
    state.inputSource = 'text';
    state.questionText = event.target.value.trim() || fixtureQuestion;
  }
  if (event.target.matches('[data-progress]')) {
    stopCurrentNarration();
    state.progress = Number(event.target.value);
    if (state.segment === 3) state.lessonComplete = state.progress >= 100;
    if (!state.branch && state.segment === 2 && state.progress < 30) state.force = 'light';
    state.playing = false;
    updateTimelineUi();
  }
});

document.addEventListener('change', (event) => {
  if (event.target.matches('[data-progress]')) {
    const resumedProgress = Math.min(99.5, state.progress);
    state.lessonComplete = false;
    startSegmentPlayback({ fromProgress: resumedProgress, withLeadIn: false });
  }
});

document.addEventListener('pointerdown', (event) => {
  const tutorWidget = event.target.closest('.mobile-tutor-widget');
  if (tutorWidget && !state.branch && !state.returningFromVacuum) {
    clearTimeout(tutorHoldTimer);
    tutorHoldSnapshot = captureMainSnapshot();
    tutorHoldWasPlaying = state.playing;
    tutorWidget.setPointerCapture?.(event.pointerId);
    tutorHoldTimer = setTimeout(() => {
      tutorHoldTimer = null;
      tutorHoldActive = true;
      state.pendingSnapshot = tutorHoldSnapshot;
      stopCurrentNarration();
      state.playing = false;
      tutorWidget.classList.add('holding');
      tutorWidget.setAttribute('aria-label', '正在模拟语音输入，松开自动发送');
      const bubbleText = tutorWidget.querySelector('.mobile-tutor-bubble strong');
      if (bubbleText) bubbleText.textContent = '松开就发送';
    }, TUTOR_HOLD_DELAY_MS);
  }
  const dragTarget = event.target.closest('[data-string-drag]');
  if (!dragTarget) return;
  state.draggingString = true;
  state.dragStartY = event.clientY;
  dragTarget.setPointerCapture?.(event.pointerId);
});

document.addEventListener('pointermove', (event) => {
  if (!state.draggingString) return;
  const target = document.querySelector('[data-string-drag]');
  if (!target) return;
  const offset = Math.max(-42, Math.min(42, event.clientY - state.dragStartY));
  target.style.transform = `translateY(${offset}px)`;
  const curve = document.querySelector('.string-curve');
  if (curve) {
    const baseCurve = Number(curve.dataset.baseCurve || 48);
    const controlY = Math.max(16, Math.min(94, baseCurve + offset));
    curve.setAttribute('d', `M30 70 Q200 ${controlY} 370 70`);
  }
});

document.addEventListener('pointerup', (event) => {
  if (tutorHoldTimer || tutorHoldActive) {
    clearTimeout(tutorHoldTimer);
    tutorHoldTimer = null;
    if (tutorHoldActive) {
      event.preventDefault();
      suppressNextTutorClick = true;
      const snapshot = tutorHoldSnapshot || captureMainSnapshot();
      resetTutorHold();
      startVacuumFollowup(snapshot);
      setTimeout(() => { suppressNextTutorClick = false; }, 500);
      return;
    }
    resetTutorHold();
  }
  if (!state.draggingString) return;
  const distance = Math.abs(event.clientY - state.dragStartY);
  state.draggingString = false;
  if (distance < 8) {
    state.dragFailures += 1;
    render();
    showToast(state.dragFailures >= 2 ? '可以改用下方保底按钮' : '再拖远一点，松开完成拨弦');
    return;
  }
  const nextForce = distance > 26 ? 'strong' : 'light';
  if (nextForce === 'strong' && !state.operations.light) {
    state.dragFailures += 1;
    render();
    showToast('先轻轻拖动一次，再用力拖动');
    return;
  }
  state.force = nextForce;
  state.operations[nextForce] = true;
  state.playing = false;
  playFixedAudio(audioSources[state.force]);
  render();
  showToast(state.force === 'strong' ? '用力拨：振幅变大，音调基本不变' : '轻拨：记录一次较小振幅');
});

document.addEventListener('pointercancel', () => {
  if (!tutorHoldTimer && !tutorHoldActive) return;
  const shouldResume = tutorHoldActive && tutorHoldWasPlaying;
  resetTutorHold();
  if (shouldResume) startSegmentPlayback({ fromProgress: state.progress, withLeadIn: false });
});

document.addEventListener('contextmenu', (event) => {
  if (event.target.closest('.mobile-tutor-widget')) event.preventDefault();
});

window.addEventListener('popstate', () => goTo('home'));
window.addEventListener('resize', () => {
  if (viewportOverride) return;
  const nextViewport = window.innerWidth < 760 || window.innerHeight > window.innerWidth ? 'mobile' : 'tablet';
  if (nextViewport === state.viewport) return;
  state.viewport = nextViewport;
  render();
});
render();
