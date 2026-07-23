const screens = [...document.querySelectorAll('.screen')];
const storageKey = 'meet-once-mvp-state';

const interviewQuestions = [
  {
    question: '一段让你舒服的关系，最重要的是什么？',
    options: ['能安心表达，不必猜', '一起成长，彼此推动', '有趣、有火花、有惊喜', '稳定可靠，言行一致']
  },
  {
    question: '刚认识一个人时，你通常是什么节奏？',
    options: ['慢慢熟悉，不急着定义', '有感觉就主动推进', '看对方节奏再回应', '更愿意先从朋友开始']
  },
  {
    question: '第一次见面，你更偏向哪种场景？',
    options: ['安静喝咖啡', '公园或街区散步', '一起吃顿饭', '看展、书店或小活动']
  },
  {
    question: '发生分歧时，你更希望对方怎么做？',
    options: ['当下说清楚', '先冷静，再认真谈', '给我明确的安抚和回应', '别回避，但也别逼迫']
  },
  {
    question: '你现在最想认识怎样的人？',
    options: ['情绪稳定、真诚的人', '有行动力、对生活好奇的人', '温柔细腻、愿意沟通的人', '目标清晰、长期主义的人']
  }
];

const state = {
  screen: 'home',
  questionIndex: 0,
  answers: [],
  selectedTime: '',
  selectedVenue: '',
  ...loadState()
};

const ids = {
  progressText: document.getElementById('progressText'),
  progressFill: document.getElementById('progressFill'),
  questionText: document.getElementById('questionText'),
  answerOptions: document.getElementById('answerOptions'),
  freeAnswer: document.getElementById('freeAnswer'),
  backQuestionButton: document.getElementById('backQuestionButton'),
  nextQuestionButton: document.getElementById('nextQuestionButton'),
  confirmedTime: document.getElementById('confirmedTime'),
  confirmedVenue: document.getElementById('confirmedVenue')
};

function loadState() {
  try {
    return JSON.parse(localStorage.getItem(storageKey)) || {};
  } catch {
    return {};
  }
}

function saveState() {
  localStorage.setItem(storageKey, JSON.stringify({
    screen: state.screen,
    questionIndex: state.questionIndex,
    answers: state.answers,
    selectedTime: state.selectedTime,
    selectedVenue: state.selectedVenue
  }));
}

function showScreen(name) {
  state.screen = name;
  screens.forEach((screen) => {
    screen.classList.toggle('active', screen.id === `screen-${name}`);
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
  saveState();
}

function renderInterview() {
  const index = Math.min(Math.max(state.questionIndex, 0), interviewQuestions.length - 1);
  const item = interviewQuestions[index];
  const currentAnswer = state.answers[index] || { option: '', freeText: '' };

  ids.progressText.textContent = `${index + 1} / ${interviewQuestions.length}`;
  ids.progressFill.style.width = `${((index + 1) / interviewQuestions.length) * 100}%`;
  ids.questionText.textContent = item.question;
  ids.answerOptions.innerHTML = '';

  item.options.forEach((option) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = option;
    button.classList.toggle('selected', currentAnswer.option === option);
    button.addEventListener('click', () => {
      saveCurrentAnswer(option, ids.freeAnswer.value.trim());
      renderInterview();
    });
    ids.answerOptions.appendChild(button);
  });

  ids.freeAnswer.value = currentAnswer.freeText || '';
  ids.backQuestionButton.disabled = index === 0;
  ids.nextQuestionButton.textContent = index === interviewQuestions.length - 1 ? '生成关系画像' : '继续';
  updateNextButton();
}

function saveCurrentAnswer(option, freeText) {
  state.answers[state.questionIndex] = {
    option: option ?? state.answers[state.questionIndex]?.option ?? '',
    freeText: freeText ?? ids.freeAnswer.value.trim()
  };
  saveState();
}

function updateNextButton() {
  const answer = state.answers[state.questionIndex] || {};
  ids.nextQuestionButton.disabled = !(answer.option || ids.freeAnswer.value.trim());
}

ids.freeAnswer.addEventListener('input', () => {
  saveCurrentAnswer(undefined, ids.freeAnswer.value.trim());
  updateNextButton();
});

document.getElementById('startButton').addEventListener('click', () => {
  state.questionIndex = 0;
  renderInterview();
  showScreen('interview');
});

document.getElementById('nextQuestionButton').addEventListener('click', () => {
  saveCurrentAnswer(undefined, ids.freeAnswer.value.trim());
  if (state.questionIndex < interviewQuestions.length - 1) {
    state.questionIndex += 1;
    renderInterview();
  } else {
    showScreen('profile');
  }
});

document.getElementById('backQuestionButton').addEventListener('click', () => {
  if (state.questionIndex > 0) {
    state.questionIndex -= 1;
    renderInterview();
  }
});

document.getElementById('findMatchButton').addEventListener('click', () => showScreen('match'));

document.getElementById('acceptButton').addEventListener('click', () => {
  showScreen('waiting');
  window.setTimeout(() => showScreen('schedule'), 2600);
});

document.getElementById('passButton').addEventListener('click', () => {
  const heading = document.querySelector('#screen-finished h2');
  const description = document.querySelector('#screen-finished p');
  heading.innerHTML = '拒绝也是匹配<br />重要的一部分';
  description.textContent = '本周不会继续给你塞候选人。真实产品会询问一个简短原因，用于改善下一次推荐，而不是诱导你继续滑动。';
  showScreen('finished');
});

function setupChoiceGroup(containerId, stateKey) {
  const container = document.getElementById(containerId);
  const buttons = [...container.querySelectorAll('button')];

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      state[stateKey] = button.dataset.value;
      buttons.forEach((candidate) => candidate.classList.toggle('selected', candidate === button));
      updateScheduleButton();
      saveState();
    });
  });

  return buttons;
}

const timeButtons = setupChoiceGroup('timeChoices', 'selectedTime');
const venueButtons = setupChoiceGroup('venueChoices', 'selectedVenue');

function updateScheduleButton() {
  document.getElementById('confirmScheduleButton').disabled = !(state.selectedTime && state.selectedVenue);
}

function restoreChoices() {
  timeButtons.forEach((button) => button.classList.toggle('selected', button.dataset.value === state.selectedTime));
  venueButtons.forEach((button) => button.classList.toggle('selected', button.dataset.value === state.selectedVenue));
  updateScheduleButton();
}

document.getElementById('confirmScheduleButton').addEventListener('click', () => {
  ids.confirmedTime.textContent = state.selectedTime;
  ids.confirmedVenue.textContent = `${state.selectedVenue} · 系统将在双方确认后展示具体地址`;
  showScreen('confirmed');
});

document.getElementById('finishButton').addEventListener('click', () => {
  const heading = document.querySelector('#screen-finished h2');
  const description = document.querySelector('#screen-finished p');
  heading.innerHTML = '我们卖的不是选择<br />而是一次真实见面';
  description.textContent = '下一步最重要的不是继续写功能，而是在一个城市找到首批 30–50 位真实用户，人工撮合并验证他们是否愿意赴约和付费。';
  showScreen('finished');
});

function resetDemo() {
  localStorage.removeItem(storageKey);
  state.screen = 'home';
  state.questionIndex = 0;
  state.answers = [];
  state.selectedTime = '';
  state.selectedVenue = '';
  restoreChoices();
  showScreen('home');
}

document.getElementById('resetButton').addEventListener('click', resetDemo);
document.getElementById('restartButton').addEventListener('click', resetDemo);
document.getElementById('brandButton').addEventListener('click', () => showScreen('home'));

renderInterview();
restoreChoices();

if (state.screen === 'waiting') {
  showScreen('schedule');
} else if (state.screen === 'confirmed' && state.selectedTime && state.selectedVenue) {
  ids.confirmedTime.textContent = state.selectedTime;
  ids.confirmedVenue.textContent = `${state.selectedVenue} · 系统将在双方确认后展示具体地址`;
  showScreen('confirmed');
} else {
  showScreen(state.screen || 'home');
}
