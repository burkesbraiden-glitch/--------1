import { mockTasks } from './tasks'

export const mockPlans = [
  {
    id: 'forbidden-city-family',
    title: '故宫亲子探索',
    destination: '故宫博物院',
    ageGroup: '7-12',
    duration: '3小时',
    taskCount: 3,
    interests: ['古代生活', '建筑礼仪', '观察表达'],
    status: 'ready',
    taskIds: mockTasks.map((task) => task.id),
  },
]

