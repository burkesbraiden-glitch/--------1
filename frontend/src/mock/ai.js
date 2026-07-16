export const mockAiSuggestions = {
  home: ['帮我创建探索计划', '这个地方孩子能学什么？', '适合8岁孩子吗？'],
  plan: ['调整学习目标', '增加观察重点'],
  guide: ['讲简单一点', '换成孩子能听懂的话', '讲一个小故事'],
  'task-list': ['先做哪个任务？', '帮我安排顺序'],
  'task-detail': ['我找不到', '给我一点提示'],
  record: ['帮我整理今天的发现', '帮我总结孩子的成长', '把这次旅行写成小故事'],
  profile: ['看看成长收获', '补充孩子兴趣'],
  login: ['为什么要登录？', '先体验一下'],
}

export function getMockAiSuggestions(pageContext) {
  return mockAiSuggestions[pageContext] || ['帮我想想下一步']
}

export function getMockAiReply(message, pageContext) {
  const contextReply = {
    home: '可以先选一个地点，我会帮你把旅行变成孩子能观察和表达的小探索。',
    plan: '我们可以把目标缩小到观察、提问和表达三件事。',
    guide: '我会用更简单的话讲，让孩子听得懂也愿意接话。',
    'task-list': '可以先从最容易观察的任务开始，完成后再记录发现。',
    'task-detail': '别着急，先找颜色、形状或位置这些线索。',
    record: '我可以帮你把照片、发现和亲子对话整理成探索相册。',
    profile: '这里会沉淀孩子的观察、表达和主动探索成长。',
    login: '当前阶段先用 Mock 登录状态，项目不会因为没有账号系统而卡住。',
  }

  return `${contextReply[pageContext] || '收到，我们继续探索。'} 你刚才说：${message}`
}

