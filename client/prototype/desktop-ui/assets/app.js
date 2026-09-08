/* ============================================================
   Perseus Desktop 原型交互脚本
   页面导航为原生 <a> 跳转；本脚本处理页内交互演示
   ============================================================ */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- Toast ---------- */
  function toast(msg, kind) {
    var wrap = $('.toast-wrap');
    if (!wrap) { return; }
    var t = document.createElement('div');
    t.className = 'toast ' + (kind || 'ok');
    var icon = kind === 'err' ? 'i-err' : (kind === 'info' ? 'i-info' : 'i-check-c');
    t.innerHTML = '<svg class="ic"><use href="#' + icon + '"/></svg><span>' + msg + '</span>';
    wrap.appendChild(t);
    requestAnimationFrame(function () { t.classList.add('show'); });
    setTimeout(function () {
      t.classList.remove('show');
      setTimeout(function () { t.remove(); }, 320);
    }, 3400);
  }

  /* ---------- 页内跳转兜底（data-nav 亦支持跨页链接） ---------- */
  var PAGES = {
    welcome: 'welcome.html', repos: 'repositories.html', repo: 'repo-detail.html',
    issues: 'issues.html', prs: 'pull-requests.html', ide: 'ide.html',
    servers: 'servers.html', settings: 'settings.html'
  };
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-nav]');
    if (el) {
      var page = PAGES[el.dataset.nav];
      if (page) { location.href = page; }
      return;
    }
    var dt = e.target.closest('[data-toast]');
    if (dt) { toast(dt.dataset.toast, dt.dataset.toastKind || 'ok'); }
  });

  /* ---------- 服务器下拉 ---------- */
  $$('[data-dd]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var dd = document.getElementById(btn.dataset.dd);
      if (!dd) { return; }
      var wasOpen = dd.classList.contains('open');
      $$('.tb-dd.open').forEach(function (d) { d.classList.remove('open'); });
      if (!wasOpen) { dd.classList.add('open'); }
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.tb-dd') && !e.target.closest('[data-dd]')) {
      $$('.tb-dd.open').forEach(function (d) { d.classList.remove('open'); });
    }
  });

  /* ---------- 筛选 pill 组（data-f 同组互斥） ---------- */
  $$('.fgroup, .fpills').forEach(function (group) {
    $$('[data-f]', group).forEach(function (b) {
      b.addEventListener('click', function () {
        $$('[data-f]', group).forEach(function (x) { x.classList.remove('on'); });
        b.classList.add('on');
      });
    });
  });
  $$('.viewtoggle button').forEach(function (b) {
    b.addEventListener('click', function () {
      $$('.viewtoggle button').forEach(function (x) { x.classList.remove('on'); });
      b.classList.add('on');
    });
  });
  $$('.theme-card').forEach(function (b) {
    b.addEventListener('click', function () {
      $$('.theme-card').forEach(function (x) { x.classList.remove('on'); });
      b.classList.add('on');
    });
  });
  $$('.radio-chip').forEach(function (b) {
    b.addEventListener('click', function () {
      $$('.radio-chip').forEach(function (x) { x.classList.remove('on'); });
      b.classList.add('on');
    });
  });

  /* ---------- 文件树折叠 ---------- */
  $$('.tree .frow.has-kids').forEach(function (row) {
    row.addEventListener('click', function () { row.parentElement.classList.toggle('open'); });
  });

  /* ---------- 通用 Tabs（data-tab / data-pane 同容器作用域） ---------- */
  $$('[data-tabs]').forEach(function (wrap) {
    var tabs = $$('[data-tab]', wrap);
    var panes = $$('[data-pane]', wrap);
    tabs.forEach(function (t) {
      t.addEventListener('click', function () {
        tabs.forEach(function (x) { x.classList.toggle('on', x === t); });
        panes.forEach(function (p) { p.classList.toggle('on', p.dataset.pane === t.dataset.tab); });
      });
    });
  });

  /* ---------- IDE：活动栏 → 侧栏切换 ---------- */
  $$('.activity .act[data-side]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      $$('.activity .act').forEach(function (x) { x.classList.toggle('on', x === btn); });
      $$('.sidebar .sb-pane').forEach(function (p) {
        p.classList.toggle('on', p.dataset.pane === btn.dataset.side);
      });
    });
  });

  /* ---------- IDE：命令面板 ---------- */
  var veil = $('#palette-veil');
  function openPalette() {
    if (!veil) { return; }
    veil.classList.add('open');
    var inp = $('.palette input'); if (inp) { inp.focus(); }
  }
  function closePalette() { if (veil) { veil.classList.remove('open'); } }
  var palBtn = $('#palette-open');
  if (palBtn) { palBtn.addEventListener('click', openPalette); }
  var palChip = $('#chip-palette');
  if (palChip) { palChip.addEventListener('click', function () { veil.classList.contains('open') ? closePalette() : openPalette(); }); }
  if (veil) {
    veil.addEventListener('click', function (e) { if (e.target === veil) { closePalette(); } });
    $$('.p-row', veil).forEach(function (r) {
      r.addEventListener('click', function () { closePalette(); toast(r.dataset.toast || '已执行：' + r.textContent.trim(), 'info'); });
    });
  }
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      if (veil) { veil.classList.contains('open') ? closePalette() : openPalette(); }
      else { toast('命令面板位于「IDE 工作区」原型页（Ctrl+K）', 'info'); }
    }
    if (e.key === 'Escape') {
      closePalette();
      $$('.modal-veil.open').forEach(function (m) { m.classList.remove('open'); });
      $$('.tb-dd.open').forEach(function (d) { d.classList.remove('open'); });
    }
  });

  /* ---------- IDE：底部面板 / 右侧辅助面板 ---------- */
  var bp = $('#bottom-panel');
  $$('#bp-toggle, .bp-toggle-btn').forEach(function (btn) {
    btn.addEventListener('click', function () { if (bp) { bp.classList.toggle('collapsed'); } });
  });
  $$('.sb-err, .sb-warn').forEach(function (chip) {
    chip.addEventListener('click', function () {
      if (bp) { bp.classList.remove('collapsed'); }
      var tabs = $$('#bottom-panel [data-tab]');
      var prob = tabs.filter(function (t) { return t.dataset.tab === 'problems'; })[0];
      if (prob) { prob.click(); }
    });
  });
  var aux = $('#aux');
  var auxToggle = $('#aux-toggle');
  if (aux && auxToggle) {
    auxToggle.addEventListener('click', function () {
      aux.classList.toggle('open');
      auxToggle.classList.toggle('on', aux.classList.contains('open'));
    });
  }

  /* ---------- IDE：Git 操作演示（含离线语义） ---------- */
  var gitCommit = $('#git-commit');
  if (gitCommit) {
    gitCommit.addEventListener('click', function () {
      var msg = $('#git-msg');
      if (msg && !msg.value.trim()) { toast('请输入提交信息', 'err'); return; }
      if (msg) { msg.value = ''; }
      toast('已提交 3 个文件到本地 main', 'ok');
    });
  }
  var gitPush = $('#git-push');
  if (gitPush) {
    gitPush.addEventListener('click', function () {
      if (document.body.classList.contains('sim-offline')) {
        toast('服务器离线 — 本地提交已保留，联网后可重试 Push', 'err');
      } else {
        toast('已推送到 origin/main（2 个提交）', 'ok');
      }
    });
  }
  var gitPull = $('#git-pull');
  if (gitPull) {
    gitPull.addEventListener('click', function () {
      if (document.body.classList.contains('sim-offline')) {
        toast('服务器离线 — Pull 已取消', 'err');
      } else {
        toast('已是最新（0 个变更）', 'info');
      }
    });
  }

  /* ---------- 弹窗 ---------- */
  $$('[data-open-modal]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var m = $(btn.dataset.openModal);
      if (m) { m.classList.add('open'); }
    });
  });
  $$('.modal-veil').forEach(function (m) {
    m.addEventListener('click', function (e) {
      if (e.target === m || e.target.closest('[data-close-modal]')) { m.classList.remove('open'); }
    });
  });

  /* ---------- 服务器卡片：设为当前 ---------- */
  $$('.srv-card .set-current').forEach(function (btn) {
    btn.addEventListener('click', function () {
      $$('.srv-card').forEach(function (c) { c.classList.remove('current'); });
      btn.closest('.srv-card').classList.add('current');
      toast('已连接到 ' + btn.closest('.srv-card').querySelector('b').textContent, 'ok');
    });
  });

  /* ---------- 设置页导航 ---------- */
  $$('.set-nav .nav-item').forEach(function (item) {
    item.addEventListener('click', function () {
      $$('.set-nav .nav-item').forEach(function (x) { x.classList.toggle('on', x === item); });
      var sec = document.getElementById(item.dataset.sec);
      if (sec) { sec.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
  });

  /* ---------- 原型条：模拟离线 / Toast 演示 ---------- */
  var chipOff = $('#chip-offline');
  if (chipOff) {
    chipOff.addEventListener('click', function () {
      document.body.classList.toggle('sim-offline');
      chipOff.classList.toggle('on', document.body.classList.contains('sim-offline'));
      toast(document.body.classList.contains('sim-offline')
        ? '已进入离线模拟：观察横幅 / 状态栏 / Push 行为'
        : '已恢复在线', 'info');
    });
  }
  var chipToast = $('#chip-toast');
  if (chipToast) {
    chipToast.addEventListener('click', function () { toast('示例通知：Clone 完成 → perseus', 'ok'); });
  }

  /* ---------- 聊天页演示：发送 / 表情回应 / 频道切换 / 成员面板 ---------- */
  var chatInput = $('#chat-input');
  var chatSend = $('#chat-send');
  var chatMsgs = $('#chat-msgs');
  function sendChat() {
    if (!chatInput || !chatMsgs) { return; }
    var v = chatInput.value.trim();
    if (!v) { return; }
    var off = document.body.classList.contains('sim-offline');
    var now = new Date();
    var hh = ('0' + now.getHours()).slice(-2) + ':' + ('0' + now.getMinutes()).slice(-2);
    var row = document.createElement('div');
    row.className = 'msg-row';
    row.innerHTML =
      '<span class="avatar" style="background:linear-gradient(135deg,#1f6feb,#bc8cff)">张</span>' +
      '<div class="m-main"><div class="m-head"><b>张伟（你）</b><time>' +
      (off ? '待发送 · 本地队列' : hh) +
      '</time></div><div class="m-text"></div></div>';
    row.querySelector('.m-text').textContent = v;
    var typing = $('.typing', chatMsgs);
    if (typing) { chatMsgs.insertBefore(row, typing); } else { chatMsgs.appendChild(row); }
    chatInput.value = '';
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
    toast(off ? '离线 — 消息已加入本地队列，重连后自动发送' : '已发送（WS 透传 dev-server）', off ? 'err' : 'ok');
  }
  if (chatSend) { chatSend.addEventListener('click', sendChat); }
  if (chatInput) {
    chatInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
    });
  }
  if (chatMsgs) { chatMsgs.scrollTop = chatMsgs.scrollHeight; }
  $$('.react[data-r]').forEach(function (r) {
    r.addEventListener('click', function () { r.classList.toggle('on'); });
  });
  $$('.cs-scroll .chan-row').forEach(function (row) {
    row.addEventListener('click', function () {
      $$('.cs-scroll .chan-row').forEach(function (x) { x.classList.remove('on'); });
      row.classList.add('on');
      toast('原型：切换到 ' + row.querySelector('.nm').textContent, 'info');
    });
  });
  var memToggle = $('#mem-toggle');
  var chatMembers = $('#chat-members');
  if (memToggle && chatMembers) {
    memToggle.addEventListener('click', function () {
      chatMembers.classList.toggle('open');
      memToggle.classList.toggle('on', chatMembers.classList.contains('open'));
    });
  }
})();
