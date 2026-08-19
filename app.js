/* Race engine + two views (台大各系 / 跨校同系). Loaded by index.html
   after data.js and data-cross.js. */
(function () {
  'use strict';

  const SECONDS_PER_YEAR = 2;
  const SLIDER_SCALE = 1000;
  const ROW_HEIGHT = 27;
  const AD_YEAR_OFFSET = 1911;
  const SHOW_ALL = 999;
  const ERA_SPLIT_YEAR = 111;

  const CATEGORY_COLORS = {
    '理組': '#3273dc',
    '文組': '#f0a020',
    '醫學': '#e5484d',
    '其他': '#8a93a3',
  };
  const PUBLIC_COLOR = '#2f9e64';
  const PRIVATE_COLOR = '#9a5cd0';

  function makeViews() {
    const views = {};
    if (window.EXAM_DATA) {
      views.ntu = {
        label: '台大各系',
        data: window.EXAM_DATA,
        chipDefs: Object.keys(CATEGORY_COLORS).map((id) => ({
          id, color: CATEGORY_COLORS[id],
        })),
        itemChip: (item) => item.c,
        colorOf: (item) => CATEGORY_COLORS[item.c],
        select: null,
        state: {
          t: 0, playing: false, topN: 20,
          chips: new Set(['理組', '醫學']), selectValue: null,
        },
      };
    }
    if (window.EXAM_CROSS_DATA) {
      const cross = window.EXAM_CROSS_DATA;
      const defaultDept = cross.deptTypes.some((d) => d.id === '資訊工程')
        ? '資訊工程' : (cross.deptTypes[0] || {}).id;
      views.cross = {
        label: '跨校同系',
        data: cross,
        chipDefs: [
          { id: '公立', color: PUBLIC_COLOR },
          { id: '私立', color: PRIVATE_COLOR },
        ],
        itemChip: (item) => (item.pub ? '公立' : '私立'),
        colorOf: (item) => (item.pub ? PUBLIC_COLOR : PRIVATE_COLOR),
        select: {
          options: cross.deptTypes.map((d) => ({
            value: d.id, label: d.id + '（' + d.schools + ' 校）',
          })),
        },
        state: {
          t: 0, playing: false, topN: 20,
          chips: new Set(['公立', '私立']), selectValue: defaultDept,
        },
      };
    }
    return views;
  }

  const el = (id) => document.getElementById(id);
  const rowsEl = el('rows');
  const playBtn = el('playBtn');
  const slider = el('slider');
  const topNSelect = el('topN');
  const chipsEl = el('chips');
  const deptSelect = el('deptSelect');
  const bigYearEl = el('bigYear');
  const adYearEl = el('adYear');
  const eraNoteEl = el('eraNote');
  const tabsEl = el('tabs');

  const VIEWS = makeViews();
  let active = VIEWS.ntu ? 'ntu' : 'cross';
  let lastFrameTime = null;
  let sliderDragging = false;

  const view = () => VIEWS[active];
  const maxT = () => view().data.years.length - 1;

  function buildRows() {
    rowsEl.textContent = '';
    const nodes = new Map();
    view().data.items.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'row hidden';
      const name = document.createElement('span');
      name.className = 'name';
      name.textContent = item.n;
      const track = document.createElement('div');
      track.className = 'track';
      const bar = document.createElement('div');
      bar.className = 'bar';
      bar.style.background = view().colorOf(item);
      const val = document.createElement('span');
      val.className = 'val';
      track.appendChild(bar);
      track.appendChild(val);
      row.appendChild(name);
      row.appendChild(track);
      rowsEl.appendChild(row);
      nodes.set(item.n, { row, bar, val, hidden: true });
    });
    view().nodes = nodes;
    view().globalMax = Math.max(
      ...view().data.items.flatMap((item) => item.s.filter((v) => v != null))
    ) * 1.02;
  }

  function buildChips() {
    chipsEl.textContent = '';
    view().chipDefs.forEach((def) => {
      const chip = document.createElement('button');
      chip.className = 'chip' + (view().state.chips.has(def.id) ? ' active' : '');
      const dot = document.createElement('span');
      dot.className = 'dot';
      dot.style.background = def.color;
      chip.appendChild(dot);
      chip.appendChild(document.createTextNode(def.id));
      chip.addEventListener('click', () => {
        const chips = new Set(view().state.chips);
        if (chips.has(def.id)) chips.delete(def.id);
        else chips.add(def.id);
        view().state.chips = chips;
        chip.classList.toggle('active');
        render();
      });
      chipsEl.appendChild(chip);
    });
  }

  function buildSelect() {
    const config = view().select;
    deptSelect.style.display = config ? '' : 'none';
    if (!config) return;
    deptSelect.textContent = '';
    config.options.forEach((opt) => {
      const option = document.createElement('option');
      option.value = opt.value;
      option.textContent = opt.label;
      deptSelect.appendChild(option);
    });
    deptSelect.value = view().state.selectValue;
  }

  function buildTabs() {
    tabsEl.textContent = '';
    Object.keys(VIEWS).forEach((key) => {
      const tab = document.createElement('button');
      tab.className = 'tab' + (key === active ? ' active' : '');
      tab.textContent = VIEWS[key].label;
      tab.addEventListener('click', () => switchView(key));
      tabsEl.appendChild(tab);
    });
  }

  function switchView(key) {
    if (key === active) return;
    setPlaying(false);
    active = key;
    document.body.className = 'view-' + key;
    buildTabs();
    initView();
  }

  function valueAt(item, t) {
    const i = Math.floor(t);
    const fraction = t - i;
    const v0 = item.s[i];
    if (fraction < 1e-6) return v0;
    const v1 = item.s[i + 1];
    if (v0 == null || v1 == null) return null;
    return v0 + (v1 - v0) * fraction;
  }

  function itemVisible(item) {
    const state = view().state;
    if (!state.chips.has(view().itemChip(item))) return false;
    if (view().select && item.d !== state.selectValue) return false;
    return true;
  }

  function visibleEntries(t) {
    const state = view().state;
    return view().data.items
      .filter(itemVisible)
      .map((item) => ({ item, value: valueAt(item, t) }))
      .filter((entry) => entry.value != null)
      .sort((a, b) => b.value - a.value || a.item.n.localeCompare(b.item.n, 'zh-Hant'))
      .slice(0, state.topN === SHOW_ALL ? Infinity : state.topN);
  }

  function placeRow(node, rank) {
    const y = rank * ROW_HEIGHT;
    if (node.hidden) {
      node.row.style.transition = 'none';
      node.row.style.transform = 'translateY(' + y + 'px)';
      void node.row.offsetHeight;
      node.row.style.transition = '';
      node.row.classList.remove('hidden');
      node.hidden = false;
      return;
    }
    node.row.style.transform = 'translateY(' + y + 'px)';
  }

  function updateYearBox(t) {
    const years = view().data.years;
    const yearIndex = Math.min(Math.round(t), maxT());
    const year = years[yearIndex];
    bigYearEl.textContent = year;
    adYearEl.textContent = '西元 ' + (year + AD_YEAR_OFFSET);
    const splitIndex = years.indexOf(ERA_SPLIT_YEAR);
    const isCrossing =
      splitIndex > 0 && t > splitIndex - 0.95 && t < splitIndex + 1;
    if (isCrossing) {
      eraNoteEl.className = 'flash';
      eraNoteEl.textContent = '制度變更：指考 → 分科測驗（每科滿分 100 → 60 級分）';
    } else if (splitIndex > 0 && yearIndex >= splitIndex) {
      eraNoteEl.className = '';
      eraNoteEl.textContent = '分科測驗時代｜每科 60 級分';
    } else {
      eraNoteEl.className = '';
      eraNoteEl.textContent = '指考時代｜每科滿分 100';
    }
  }

  function render() {
    const state = view().state;
    const entries = visibleEntries(state.t);
    const shownNames = new Set(entries.map((entry) => entry.item.n));
    entries.forEach((entry, rank) => {
      const node = view().nodes.get(entry.item.n);
      placeRow(node, rank);
      node.bar.style.width = (entry.value / view().globalMax) * 100 + '%';
      node.val.textContent = entry.value.toFixed(2);
    });
    view().nodes.forEach((node, name) => {
      if (shownNames.has(name) || node.hidden) return;
      node.row.classList.add('hidden');
      node.hidden = true;
    });
    rowsEl.style.height = entries.length * ROW_HEIGHT + 'px';
    updateYearBox(state.t);
    if (!sliderDragging) {
      slider.value = String(Math.round(state.t * SLIDER_SCALE));
    }
  }

  function setPlaying(playing) {
    view().state.playing = playing;
    playBtn.textContent = playing ? '⏸ 暫停' : '▶ 播放';
  }

  function tick(now) {
    const state = view().state;
    if (state.playing) {
      const dt = lastFrameTime == null ? 0 : (now - lastFrameTime) / 1000;
      state.t = Math.min(state.t + dt / SECONDS_PER_YEAR, maxT());
      if (state.t >= maxT()) setPlaying(false);
      render();
    }
    lastFrameTime = now;
    requestAnimationFrame(tick);
  }

  function initView() {
    buildRows();
    buildChips();
    buildSelect();
    slider.max = String(maxT() * SLIDER_SCALE);
    topNSelect.value = String(view().state.topN);
    setPlaying(false);
    render();
  }

  playBtn.addEventListener('click', () => {
    const state = view().state;
    if (!state.playing && state.t >= maxT()) state.t = 0;
    setPlaying(!state.playing);
  });

  slider.addEventListener('input', () => {
    sliderDragging = true;
    setPlaying(false);
    view().state.t = Number(slider.value) / SLIDER_SCALE;
    render();
    sliderDragging = false;
  });

  topNSelect.addEventListener('change', () => {
    view().state.topN = Number(topNSelect.value);
    render();
  });

  deptSelect.addEventListener('change', () => {
    view().state.selectValue = deptSelect.value;
    render();
  });

  document.body.className = 'view-' + active;
  buildTabs();
  initView();
  requestAnimationFrame(tick);
})();
