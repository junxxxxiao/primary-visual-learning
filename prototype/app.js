const app = document.querySelector('#app');
const nav = document.querySelector('#prototype-nav');
const titleEl = document.querySelector('#screen-title');
const descriptionEl = document.querySelector('#screen-description');
const fixtureQuestion = '用力拨琴弦，声音会更高吗？';

const screens = {
  onboarding: ['首次使用', '家长授权与儿童设置'],
  home: ['儿童首页', '选择学习入口'],
  askVoice: ['语音提问', '固定夹具模拟语音输入'],
  askPhoto: ['拍照提问', '固定夹具模拟框选与隐私检查'],
  confirm: ['问题确认', '确认儿童原话与学习目标'],
  prediction: ['诊断预测', '选择会改变后续讲解路径'],
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
  ['核心流程', ['home', 'askVoice', 'confirm', 'prediction', 'loading', 'explore', 'migration', 'feedback', 'complete']],
  ['历史与家长', ['history', 'parentToday', 'parentRecords', 'parentInsights', 'parentSettings']],
  ['边界状态', ['onboarding', 'failure']]
];

const state = {
  screen: 'home',
  viewport: 'tablet',
  prediction: 'higher',
  force: 'strong',
  slow: false,
  playing: true,
  segment: 2,
  branch: false,
  branchAvailable: false,
  lessonComplete: false,
  interruptOpen: false,
  interruptChoice: 'vacuum',
  interruptInputMode: 'voice',
  interruptDraft: '如果没有空气呢？',
  typedInterrupt: '',
  conversationQuestion: '',
  mobileTutorOpen: false,
  migrationAnswer: null,
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
  onboardingStep: 1
};

const previewParams = new URLSearchParams(location.search);
if (screens[previewParams.get('screen')] || previewParams.get('screen') === 'askPhoto') {
  state.screen = previewParams.get('screen');
}
if (['tablet', 'mobile'].includes(previewParams.get('viewport'))) {
  state.viewport = previewParams.get('viewport');
}
if (previewParams.get('branch') === 'true') {
  state.branch = true;
  state.branchAvailable = true;
}
if (previewParams.get('interrupt') === 'true') {
  state.screen = 'explore';
  state.interruptOpen = true;
  state.playing = false;
}

const records = [
  { title: '用力拨琴弦，声音会更高吗？', date: '今天 16:20', topics: 2, questions: 2, result: '已理解' },
  { title: '为什么四分之一比三分之一小？', date: '昨天 19:05', topics: 1, questions: 1, result: '部分理解' },
  { title: '影子为什么会变长？', date: '7 月 15 日', topics: 2, questions: 3, result: '已理解' }
];

const parentRecordsData = [
  { id: 'sound-string', title: '用力拨琴弦，声音会更高吗？', date: '今天 16:20', subject: '科学 · 声音', status: 'understood', statusLabel: '已理解', independent: '是', feedback: '讲明白了', misconception: '孩子原本认为“用力越大，音调越高”。', intervention: '保持弦长、松紧和粗细不变，对比轻拨与用力拨，并慢放观察振幅。', transfer: '在音叉情境中独立判断“更用力主要让声音更响”。', advice: '暂不需要介入，可以在生活中继续比较轻敲与重敲。' },
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
    ['string', '声音', '用力拨琴弦，为什么声音会更响？', '比较振幅、响度和音调'],
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

function renderAskVoice() {
  return `<div class="app-screen">${appHeader({ back: true })}<main class="screen-body centered">
    <div class="content-narrow"><h1>把问题说给我听</h1><p>按住说话，松开后先确认文字。原型不会调用真实麦克风。</p>
      <div class="ask-box">
        <button class="voice-button ${state.recording ? 'recording' : ''}" data-action="record">
          <span>${state.recording ? '<span class="waveform"><span></span><span></span><span></span><span></span><span></span></span>正在听…' : '● 按住说话'}</span>
        </button>
        <div class="helper" style="text-align:center">测试夹具会识别为：用力拨琴弦，声音会更高吗？</div>
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
          <div><label class="helper" for="photo-question-input">文字补充</label><input id="photo-question-input" class="fake-input" data-question-input placeholder="例如：用力拨会让声音更高吗？" /></div>
        </div>
      </section>
      <div class="button-row end"><button class="btn" data-screen="home">取消</button><button class="btn primary" data-screen="confirm" ${state.captured ? '' : 'disabled'}>使用框选内容</button></div>
    </div>
  </main></div>`;
}

function renderConfirm() {
  const fromPhoto = state.inputSource === 'photo';
  const sourceLabel = fromPhoto ? '从照片中识别到的问题' : state.inputSource === 'text' ? '你输入的问题是' : '我听到的是';
  return `<div class="app-screen">${appHeader({ back: true })}<main class="screen-body centered">
    <div class="content-narrow"><div class="eyebrow">${sourceLabel}</div><div class="question-quote">“${escapeHtml(state.questionText)}”</div>
      ${fromPhoto ? '<div class="source-note"><strong>识别自</strong><span>已框选的课本琴弦插图</span></div>' : ''}
      <div class="goal-box"><span>这次要弄明白</span><strong>拨弦力度、振幅、响度和音调之间的关系</strong></div>
      <div class="notice" style="margin-top:14px">比较时保持同一根弦的长度、松紧和粗细不变。</div>
      <div class="button-row">${fromPhoto ? '<button class="btn" data-action="retake-photo">重新拍照</button>' : ''}<button class="btn" data-action="edit-question">修改问题</button><button class="btn primary" data-screen="prediction">就是这个问题</button></div>
    </div>
  </main></div>`;
}

function renderPrediction() {
  const options = [
    ['higher', '会变高', '用力越大，音调越高'],
    ['louder', '不会变高，只会更响', '音调保持不变'],
    ['unsure', '不确定', '我想先看一看']
  ];
  return `<div class="app-screen">${appHeader({ back: true })}<main class="screen-body centered">
    <div class="content-narrow"><div class="eyebrow">先猜一猜</div><h1>同一根琴弦，用力拨会发生什么？</h1><p>先选你的想法，接下来用画面验证。这里不会马上显示对错。</p>
      <div class="choice-list">${options.map(([id, label, note]) => `<button class="choice ${state.prediction === id ? 'selected' : ''}" data-prediction="${id}"><span class="choice-marker">${state.prediction === id ? '✓' : ''}</span><span><strong>${label}</strong><small>${note}</small></span></button>`).join('')}</div>
      <div class="button-row end"><button class="btn primary" data-screen="loading">去验证</button></div>
    </div>
  </main></div>`;
}

function renderLoading() {
  return `<div class="app-screen">${appHeader({ back: true })}<main class="screen-body centered">
    <div class="loading-wrap"><div class="loading-graphic"><div class="loading-string"></div></div><h1>正在准备第一段观察</h1><p>先把同一根琴弦的轻拨和用力拨放在一起比较。</p><div class="progress-track"><div class="progress-bar"></div></div><div class="helper">有效讲解会先开始，互动模型随后准备好</div>
      <div class="button-row center"><button class="btn primary" data-screen="explore">进入讲解</button><button class="btn ghost" data-screen="failure">查看 15 秒失败状态</button></div>
    </div>
  </main></div>`;
}

function exploreHeader() {
  return `<header class="explore-header"><button class="back-button" data-screen="home" aria-label="退出探索">‹</button>
    <div class="topic-switcher" role="tablist" aria-label="讲解主题">
      <button class="${!state.branch ? 'active' : ''}" data-topic="main" role="tab" aria-selected="${!state.branch}">琴弦振动</button>
      ${state.branchAvailable ? `<button class="${state.branch ? 'active' : ''}" data-topic="vacuum" role="tab" aria-selected="${state.branch}">真空中的声音</button>` : ''}
    </div>
    <span class="explore-header-spacer" aria-hidden="true"></span>
  </header>`;
}

function interruptModal() {
  if (!state.interruptOpen) return '';
  return `<div class="modal-backdrop"><div class="modal" style="position:relative"><button class="modal-close" data-action="close-modal" aria-label="关闭">×</button>
    <div class="eyebrow">讲解已暂停，现场已保存</div><h2>${state.interruptInputMode === 'voice' ? '我听到的是' : '你输入的是'}</h2>
    <div class="question-quote" style="font-size:17px">“${escapeHtml(state.interruptDraft)}”</div>
    <p>确认后，这句话会显示在右侧对话区，并继续相应的讲解。</p>
    <div class="button-row end"><button class="btn" data-action="close-modal">修改问题</button><button class="btn primary" data-action="confirm-interrupt">确认问题</button></div>
  </div></div>`;
}

function renderExplore() {
  const vacuum = state.branch;
  const segmentSets = vacuum
    ? [
        ['琴弦还会振动吗？', '先区分物体振动和声音传播', '即使没有空气，拨动的琴弦本身仍然会来回振动。', ['保持：同一根琴弦', '改变：周围有没有空气', '观察：琴弦是否继续振动']],
        ['声音怎样传出去？', '观察空气在传播中的作用', '声音需要周围的物质把振动一层层传到远处。', ['琴弦推动附近空气', '空气把振动继续传递', '耳朵接收到振动']],
        ['没有空气会怎样？', '整理真空中的声音结论', '真空中没有空气粒子，振动无法继续传播到远处。', ['琴弦：仍然振动', '空气：不存在', '结果：远处听不到声音']]
      ]
    : [
        ['先看同一根弦', '保持长度、松紧和粗细不变', '要公平比较，先只改变拨弦的力度，其他条件保持不变。', ['保持：弦长、松紧、粗细', '改变：拨弦力度', '观察：振幅和听到的声音']],
        ['用力拨改变了什么？', '观察琴弦离开中间位置的距离', '用力拨时，琴弦离开中间位置更远，也就是振幅更大。', ['轻轻拨：振幅较小', '用力拨：振幅较大', '比较：声音响度']],
        ['把发现说清楚', '区分振幅、响度和音调', '力度主要改变振幅和响度，音调主要由振动快慢决定。', ['力度变大 → 振幅变大', '振幅变大 → 声音更响', '音调不一定变高']]
      ];
  const activeSegment = segmentSets[state.segment - 1];
  const segmentProgress = state.segment === 1 ? 38 : state.segment === 2 ? 54 : 100;
  const speech = vacuum
    ? '琴弦仍然会振动，但真空里没有空气把振动一层层传出去，所以远处听不到声音。'
    : state.slow
      ? '现在慢放了。你看到用力拨时，琴弦离开中间位置更远，这叫振幅更大。'
      : '先保持琴弦的长度、松紧和粗细不变。用力拨，主要让振幅变大，所以声音更响。';
  const tutorHeader = `<div class="tutor-id"><span class="tutor-avatar">小知</span><div><strong>对话</strong><small>${state.playing ? `正在讲解“${activeSegment[0]}”` : '讲解已暂停，等待你的问题'}</small></div></div>`;
  const dialogueThread = `<div class="dialog-thread">
    <div class="dialog-message tutor"><small>小知老师 · ${state.conversationQuestion ? '已保存刚才的讲解现场' : '正在讲解'}</small><p>${state.conversationQuestion ? '我先停在这里，看看你想追问什么。' : speech}</p></div>
    ${state.conversationQuestion ? `<div class="dialog-message child"><small>你问</small><p>${escapeHtml(state.conversationQuestion)}</p></div><div class="dialog-message tutor"><small>小知老师</small><p>${speech}</p></div>` : ''}
    <div class="key-point">${vacuum ? '琴弦振动 ≠ 声音一定能传到远处。传播还需要介质。' : '力度主要影响振幅和响度；音调主要由振动快慢决定。'}</div>
  </div>`;
  const interruptTools = `<div class="interrupt-tools">
    <button class="interrupt-button" data-action="interrupt">● 语音追问</button>
    <div class="interrupt-text-row"><input class="interrupt-text-input" data-interrupt-text value="${escapeHtml(state.typedInterrupt)}" placeholder="输入你想追问的问题"><button data-action="send-text-interrupt">发送</button></div>
  </div>`;
  const lessonAction = state.lessonComplete && !vacuum ? '<button class="btn primary lesson-complete-action" data-screen="migration">我看明白了，去试一题</button>' : '';
  return `<div class="app-screen explore-screen">${exploreHeader()}<main class="explore-main">
    <section class="visual-workspace">
      <div class="lesson-slide">
        <div class="lesson-title"><div><span class="slide-type">核心讲解 · 图解与动画</span><h1>${activeSegment[0]}</h1><p>${activeSegment[1]}</p></div><span class="result-tag ${vacuum ? 'warn' : ''}">${vacuum ? '关联主题' : `子片段 ${state.segment}/3`}</span></div>
        <div class="slide-body">
          <div class="slide-copy">
            <p class="slide-lead">${activeSegment[2]}</p>
            <div class="slide-points">${activeSegment[3].map((point, index) => `<div><span>${index + 1}</span><strong>${point}</strong></div>`).join('')}</div>
            ${state.segment === 3 ? `<div class="slide-takeaway">${vacuum ? '<strong>关键结论</strong><span>物体仍振动，但声音不能穿过真空传播。</span>' : '<strong>关键结论</strong><span>更用力主要让声音更响，不会因此让音调更高。</span>'}</div>` : ''}
          </div>
          <div class="slide-visual-wrap">
            <div class="scene-canvas ${vacuum ? 'vacuum' : ''}"><span class="scene-caption">${vacuum ? '介质：真空' : `播放速度：${state.slow ? '0.4×' : '1×'}`}</span>
              ${vacuum ? '<div class="wave-field"><span class="wave-ring"></span><span class="wave-ring"></span><span class="wave-ring"></span><span class="vacuum-label">没有空气粒子传递振动</span></div>' : ''}
              <div class="string-rig"><span class="peg"></span><div class="string-stage"><div class="string-line ${state.playing ? 'vibrating' : ''} ${state.force === 'strong' ? 'strong' : ''} ${state.slow ? 'slow' : ''}"></div>${state.force === 'strong' && !vacuum ? '<div class="amplitude-mark"><span>振幅更大</span></div>' : ''}</div><span class="peg"></span></div>
            </div>
            <div class="scene-controls">
              ${vacuum ? '<button class="control-button" data-action="medium-air">空气</button><button class="control-button active">真空</button><button class="control-button" data-action="return-main">返回琴弦</button>' : `<button class="control-button ${state.force === 'light' ? 'active' : ''}" data-force="light">轻轻拨</button><button class="control-button ${state.force === 'strong' ? 'active' : ''}" data-force="strong">用力拨</button><button class="control-button ${state.slow ? 'active' : ''}" data-action="slow">${state.slow ? '恢复速度' : '慢放观察'}</button>`}
            </div>
          </div>
        </div>
      </div>
      <div class="segment-area">
        <div class="segment-tabs" role="tablist" aria-label="当前主题的讲解子片段">${segmentSets.map((segment, index) => `<button class="${state.segment === index + 1 ? 'active' : ''}" data-segment="${index + 1}" role="tab" aria-selected="${state.segment === index + 1}"><span>${index + 1}</span>${segment[0]}</button>`).join('')}</div>
        <div class="segment-player"><button class="play-button" data-action="toggle-play" aria-label="${state.playing ? `暂停“${activeSegment[0]}”` : `继续“${activeSegment[0]}”`}">${state.playing ? 'Ⅱ' : '▶'}</button><div><div class="segment-track"><div class="segment-progress" style="width:${segmentProgress}%"></div></div><small>“${activeSegment[0]}”播放进度</small></div><span class="segment-count">${segmentProgress}%</span></div>
      </div>
    </section>
    <aside class="tutor-panel">${tutorHeader}${dialogueThread}${interruptTools}${lessonAction}</aside>
  </main>
  ${!state.mobileTutorOpen ? '<button class="mobile-tutor-widget" data-action="open-mobile-tutor"><span class="mobile-tutor-character">小知</span><span class="mobile-tutor-bubble">有不懂的，可以随时问我</span></button>' : ''}
  ${state.mobileTutorOpen ? `<div class="mobile-tutor-backdrop"><section class="mobile-tutor-drawer" aria-label="小知对话"><div class="mobile-drawer-head">${tutorHeader}<button data-action="close-mobile-tutor" aria-label="收起对话">×</button></div>${dialogueThread}${interruptTools}${lessonAction}</section></div>` : ''}
  ${interruptModal()}</div>`;
}

function renderMigration() {
  const options = [['higher', '音调变高'], ['same', '音调基本不变，只是更响'], ['lower', '音调变低']];
  const correct = state.migrationAnswer === 'same';
  return `<div class="app-screen">${appHeader({ back: true })}<main class="screen-body">
    <div class="content-wide"><div class="eyebrow">换一个新情境</div><h1>同一个音叉被敲得更用力，会发生什么？</h1><p>音叉本身没有更换。先用刚才发现的规律判断。</p>
      <div class="migration-layout"><div class="tuning-fork"><div class="fork-shape"><span class="fork-prong left"></span><span class="fork-prong right"></span><span class="fork-stem"></span></div></div>
        <div><div class="choice-list">${options.map(([id,label]) => `<button class="choice ${state.migrationAnswer === id ? 'selected' : ''}" data-migration="${id}"><span class="choice-marker">${state.migrationAnswer === id ? '✓' : ''}</span><strong>${label}</strong></button>`).join('')}</div>
        ${state.migrationAttempted && !correct ? '<div class="hint-box"><strong>再想一想</strong><br>用力改变的是振动的幅度，还是每秒振动的次数？</div>' : ''}
        ${correct ? '<div class="notice info" style="margin-top:16px">你把琴弦上的规律用到了音叉上：用力主要让振幅更大、声音更响。</div>' : ''}
        <div class="button-row end"><button class="btn ${correct ? 'success' : 'primary'}" data-action="check-migration">${correct ? '继续' : state.migrationAttempted ? '再回答一次' : '检查想法'}</button></div></div>
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
  return `<div class="app-screen">${appHeader()}<main class="screen-body centered"><div class="content-narrow">
    <div class="completion-mark">✓</div><h1>这次探索已完成</h1><p>已自动保存到“我的探索”，以后可以回到任何关键节点继续问。</p>
    <div class="discovery-list">
      <div class="discovery-item"><span>1</span><div><strong>你的核心发现</strong><p>用力拨同一根琴弦，主要让振幅变大、声音更响，不会因此让音调更高。</p></div></div>
      <div class="discovery-item"><span>2</span><div><strong>你亲手验证了</strong><p>切换轻轻拨和用力拨，并用慢放观察振幅。</p></div></div>
      <div class="discovery-item"><span>3</span><div><strong>你继续追问了</strong><p>真空中琴弦仍会振动，但声音不能靠空气传播。</p></div></div>
    </div>
    <div class="notice info">迁移验证：已理解 · 独立完成 · 使用 0 次提示</div>
    <div class="button-row"><button class="btn" data-screen="home">回首页</button><button class="btn primary" data-screen="history">回看这次探索</button></div>
  </div></main></div>`;
}

function renderHistory() {
  const selected = records[state.historySelected];
  const selectedEvidence = parentRecordsData[state.historySelected] || parentRecordsData[0];
  const detailContent = `<div class="eyebrow">${selected.date}</div><h2>${selected.title}</h2><p>这条记录通过保存的对话、场景快照和操作事件重建，不重新调用模型。</p>
    <div class="evidence-timeline"><div class="evidence-row"><strong>原来的想法</strong><p>${selectedEvidence.misconception}</p><small>预测节点</small></div><div class="evidence-row"><strong>关键操作</strong><p>${selectedEvidence.intervention}</p><small>互动讲解节点</small></div><div class="evidence-row"><strong>迁移结果</strong><p>${selectedEvidence.transfer}</p><small>${selectedEvidence.statusLabel}</small></div></div>
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
    onboarding: renderOnboarding, home: renderHome, askVoice: renderAskVoice, askPhoto: renderAskPhoto,
    confirm: renderConfirm, prediction: renderPrediction, loading: renderLoading, explore: renderExplore,
    migration: renderMigration, feedback: renderFeedback, complete: renderComplete, history: renderHistory,
    parentPin: renderParentPin, parentToday: renderParentToday, parentRecords: renderParentRecords,
    parentInsights: renderParentInsights, parentSettings: renderParentSettings, failure: renderFailure
  };
  app.innerHTML = (renderers[state.screen] || renderHome)();
  app.className = `device ${state.viewport}`;
  const [title, description] = screens[state.screen] || screens.home;
  titleEl.textContent = title;
  descriptionEl.textContent = description;
  renderNav();
}

function renderNav() {
  nav.innerHTML = navGroups.map(([group, ids]) => `<div class="nav-group"><div class="nav-group-label">${group}</div>${ids.map(id => `<button class="prototype-nav-button ${state.screen === id ? 'active' : ''}" data-screen="${id}">${screens[id][0]}</button>`).join('')}</div>`).join('');
}

function goTo(screen) {
  if (!screens[screen] && screen !== 'askPhoto') return;
  state.screen = screen;
  if (screen === 'explore') state.playing = true;
  if (screen !== 'explore') state.mobileTutorOpen = false;
  render();
}

function scrollToParentRecord(anchorId) {
  requestAnimationFrame(() => document.getElementById(anchorId)?.scrollIntoView({ block: 'start' }));
}

document.addEventListener('click', (event) => {
  const screenTarget = event.target.closest('[data-screen]');
  if (screenTarget && !screenTarget.disabled) {
    if (screenTarget.dataset.screen === 'askPhoto') { state.inputSource = 'photo'; state.questionText = fixtureQuestion; }
    if (screenTarget.dataset.screen === 'askVoice') { state.inputSource = 'voice'; state.questionText = fixtureQuestion; }
    goTo(screenTarget.dataset.screen); return;
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
  const prediction = event.target.closest('[data-prediction]');
  if (prediction) { state.prediction = prediction.dataset.prediction; render(); return; }
  const force = event.target.closest('[data-force]');
  if (force) { state.force = force.dataset.force; state.playing = true; render(); return; }
  const interrupt = event.target.closest('[data-interrupt]');
  if (interrupt) { state.interruptChoice = interrupt.dataset.interrupt; render(); return; }
  const migration = event.target.closest('[data-migration]');
  if (migration) { state.migrationAnswer = migration.dataset.migration; render(); return; }
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
    state.branch = topic.dataset.topic === 'vacuum';
    state.segment = 1;
    state.lessonComplete = false;
    state.playing = true;
    render();
    return;
  }
  const segment = event.target.closest('[data-segment]');
  if (segment) {
    state.segment = Number(segment.dataset.segment);
    state.lessonComplete = state.segment === 3;
    state.playing = true;
    render();
    return;
  }
  const setting = event.target.closest('[data-setting]');
  if (setting) { const key = setting.dataset.setting; state.settings[key] = !state.settings[key]; showToast(state.settings[key] ? '设置已开启' : '设置已关闭'); render(); return; }
  const action = event.target.closest('[data-action]')?.dataset.action;
  if (!action) return;
  const handlers = {
    back: () => {
      const targets = { askVoice: 'home', askPhoto: 'home', confirm: state.inputSource === 'photo' ? 'askPhoto' : 'askVoice', prediction: 'confirm', loading: 'prediction', migration: 'explore', feedback: 'migration', history: 'home', parentPin: 'home', failure: 'loading' };
      goTo(targets[state.screen] || 'home');
    },
    captions: () => { state.settings.captions = !state.settings.captions; render(); },
    'onboarding-next': () => { state.onboardingStep = 2; render(); },
    record: () => { if (state.screen === 'askVoice') { state.inputSource = 'voice'; state.questionText = fixtureQuestion; } state.recording = !state.recording; render(); if (state.recording) setTimeout(() => { state.recording = false; render(); showToast(state.screen === 'askPhoto' ? '已添加语音补充' : '已生成固定测试文字'); }, 900); },
    capture: () => { state.captured = true; render(); showToast('已使用固定测试图片'); },
    'edit-question': () => { goTo(state.inputSource === 'photo' ? 'askPhoto' : 'askVoice'); showToast('可以重新说或修改文字'); },
    'retake-photo': () => { state.captured = false; goTo('askPhoto'); showToast('请重新拍照并框选问题'); },
    'toggle-play': () => { state.playing = !state.playing; render(); },
    slow: () => { state.slow = !state.slow; state.playing = true; render(); },
    'open-mobile-tutor': () => { state.mobileTutorOpen = true; render(); },
    'close-mobile-tutor': () => { state.mobileTutorOpen = false; render(); },
    interrupt: () => { state.playing = false; state.interruptInputMode = 'voice'; state.interruptDraft = '如果没有空气呢？'; state.interruptChoice = 'vacuum'; state.interruptOpen = true; render(); },
    'send-text-interrupt': () => {
      if (!state.typedInterrupt.trim()) { showToast('先输入你想追问的问题'); return; }
      state.playing = false;
      state.interruptInputMode = 'text';
      state.interruptDraft = state.typedInterrupt.trim();
      state.interruptChoice = /空气|真空/.test(state.interruptDraft) ? 'vacuum' : 'slow';
      state.interruptOpen = true;
      render();
    },
    'close-modal': () => { state.interruptOpen = false; render(); },
    'confirm-interrupt': () => {
      state.interruptOpen = false; state.playing = true; state.conversationQuestion = state.interruptDraft;
      if (state.interruptChoice === 'vacuum') { state.branchAvailable = true; state.branch = true; state.segment = 1; state.lessonComplete = false; }
      else state.slow = true;
      render(); showToast(state.interruptChoice === 'vacuum' ? '已创建关联主题' : '已修改当前场景');
    },
    'return-main': () => { state.branch = false; state.playing = true; render(); showToast('已恢复被打断的琴弦现场'); },
    'medium-air': () => { state.branch = false; render(); },
    'check-migration': () => {
      if (state.migrationAnswer === 'same') goTo('feedback');
      else { state.migrationAttempted = true; render(); }
    },
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
  if (event.target.matches('[data-interrupt-text]')) {
    state.typedInterrupt = event.target.value;
    return;
  }
  if (event.target.matches('[data-question-input]') && state.screen === 'askVoice') {
    state.inputSource = 'text';
    state.questionText = event.target.value.trim() || fixtureQuestion;
  }
});

window.addEventListener('popstate', () => goTo('home'));
render();
