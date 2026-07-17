(() => {
  const views = Array.from(document.querySelectorAll('.view'));
  const navItems = Array.from(document.querySelectorAll('.nav-item'));
  const pageTitle = document.getElementById('page-title');
  const toast = document.getElementById('toast');
  const selectedCount = document.getElementById('selected-count');
  const chosenPlanName = document.getElementById('chosen-plan-name');
  const reportPlan = document.getElementById('report-plan');
  const workorderPlan = document.getElementById('workorder-plan');
  const workorderStatus = document.getElementById('workorder-status');

  let selectedMeasures = new Set(['配变档位调整', '三相负荷调整']);
  let selectedPlan = 'B';
  let toastTimer;

  const planCopy = {
    A: {
      title: '方案 A：调档 + 三相调整',
      workorder: '方案 A：执行配变档位调整与三相负荷调整，治理后持续监测 7 天；若极端负荷下复发，转入工程治理。',
      report: '方案 A：调档 + 三相调整。预计最低电压提升至 200.8V，演示投资约 0.8 万元，实施周期约 1 天。该方案用于快速恢复，但极端负荷下仍存在复发风险。'
    },
    B: {
      title: '方案 B：管理措施 + 末端线路改造',
      workorder: '方案 B：先执行配变档位调整与三相负荷调整，再完成末端线路改造。',
      report: '方案 B：管理措施 + 末端线路改造。预计最低电压提升至 208.6V，演示投资约 18 万元，实施周期约 15 天。'
    },
    C: {
      title: '方案 C：新增配变布点 + 网架调整',
      workorder: '方案 C：完成新增配变布点、低压供电范围调整及配套网架改造，并同步复核现有配变负荷分配。',
      report: '方案 C：新增配变布点 + 网架调整。预计最低电压提升至 213.2V，演示投资约 52 万元，实施周期约 45 天。该方案效果最佳，但需落实设备用地和建设条件。'
    }
  };

  function showToast(message) {
    clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.add('show');
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
  }

  function showView(viewName, options = {}) {
    const target = document.getElementById(`view-${viewName}`);
    if (!target) return;

    views.forEach(view => view.classList.toggle('active', view === target));
    navItems.forEach(item => item.classList.toggle('active', item.dataset.view === viewName));
    pageTitle.textContent = target.dataset.title || '低电压治理';

    if (!options.preserveScroll) window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function syncMeasureCount() {
    selectedCount.textContent = String(selectedMeasures.size);
  }

  function resetDemo() {
    selectedMeasures = new Set(['配变档位调整', '三相负荷调整']);
    document.querySelectorAll('.measure-card').forEach(card => {
      const isSelected = selectedMeasures.has(card.dataset.measure);
      card.classList.toggle('selected', isSelected);
      const button = card.querySelector('.measure-toggle');
      button.textContent = isSelected ? '已加入候选' : '加入候选';
    });
    selectPlan('B', false);
    workorderStatus.textContent = '待确认';
    workorderStatus.className = 'tag warn';
    document.getElementById('owner-input').value = '待指定';
    document.getElementById('due-date-input').value = '2026-08-01';
    syncMeasureCount();
    showView('dashboard');
    showToast('演示状态已重置');
  }

  function selectPlan(planId, notify = true) {
    selectedPlan = planId;
    document.querySelectorAll('.plan-card').forEach(card => {
      const selected = card.dataset.plan === planId;
      card.classList.toggle('selected', selected);
      const button = card.querySelector('.select-plan');
      button.textContent = selected ? '已选择' : '选择此方案';
    });

    const copy = planCopy[planId];
    chosenPlanName.textContent = copy.title;
    workorderPlan.value = copy.workorder;
    reportPlan.textContent = copy.report;
    if (notify) showToast(`已选择${copy.title}`);
  }

  navItems.forEach(item => item.addEventListener('click', () => showView(item.dataset.view)));
  document.querySelectorAll('[data-go]').forEach(button => {
    button.addEventListener('click', () => showView(button.dataset.go));
  });

  document.getElementById('start-diagnosis').addEventListener('click', event => {
    const button = event.currentTarget;
    const original = button.textContent;
    button.disabled = true;
    button.textContent = '正在校核数据…';
    showToast('正在组合监测数据、台区档案和估计参数');

    setTimeout(() => {
      button.textContent = '正在分析成因…';
    }, 650);

    setTimeout(() => {
      button.disabled = false;
      button.textContent = original;
      showView('diagnosis');
      showToast('演示诊断完成：识别出 3 类主要成因');
    }, 1500);
  });

  document.getElementById('revise-diagnosis').addEventListener('click', () => {
    showToast('原型中暂以侧栏提示表示“人工修订诊断”；正式版本将保留修订记录和理由。');
  });

  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(item => item.classList.toggle('active', item === tab));
      document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
      document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
    });
  });

  document.querySelectorAll('.measure-card').forEach(card => {
    const toggle = card.querySelector('.measure-toggle');
    toggle.addEventListener('click', () => {
      const measure = card.dataset.measure;
      if (selectedMeasures.has(measure)) {
        selectedMeasures.delete(measure);
        card.classList.remove('selected');
        toggle.textContent = '加入候选';
        showToast(`已移除：${measure}`);
      } else {
        selectedMeasures.add(measure);
        card.classList.add('selected');
        toggle.textContent = '已加入候选';
        showToast(`已加入候选：${measure}`);
      }
      syncMeasureCount();
    });
  });

  document.querySelectorAll('.select-plan').forEach(button => {
    button.addEventListener('click', () => {
      const planId = button.closest('.plan-card').dataset.plan;
      selectPlan(planId);
    });
  });

  document.getElementById('create-workorder').addEventListener('click', () => {
    const owner = document.getElementById('owner-input').value.trim();
    const dueDate = document.getElementById('due-date-input').value;

    if (!owner || owner === '待指定') {
      showToast('请先指定演示工单责任人');
      document.getElementById('owner-input').focus();
      return;
    }
    if (!dueDate) {
      showToast('请设置计划完成日期');
      document.getElementById('due-date-input').focus();
      return;
    }

    workorderStatus.textContent = '已生成';
    workorderStatus.className = 'tag';
    showToast(`演示工单已生成：责任人 ${owner}，计划完成 ${dueDate}`);
  });

  document.getElementById('print-report').addEventListener('click', () => window.print());
  document.getElementById('reset-demo').addEventListener('click', resetDemo);

  syncMeasureCount();
})();
