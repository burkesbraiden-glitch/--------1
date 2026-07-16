import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { generateJourneyRecordData } from '../src/stores/recordJourney.mjs'

const root = process.cwd()

const plan = {
  id: 'forbidden-city-family',
  title: '故宫亲子探索',
  destination: '故宫博物院',
}

const tasks = [
  {
    id: 'roof-beasts',
    order: 1,
    title: '找屋顶上的小兽',
    subtitle: '在屋顶上找一找那些小兽',
    status: 'completed',
    record: {
      imagePath: 'temp://real-roof-photo.jpg',
      note: '我发现屋顶上的小兽排成了一队',
    },
  },
  {
    id: 'palace-gate',
    order: 2,
    title: '拍一扇宫门',
    subtitle: '找到一扇喜欢的宫门并拍下来',
    status: 'completed',
    record: {
      imagePath: '',
      note: '',
    },
  },
]

const mockRecords = [
  {
    id: 'record-roof-beasts',
    sourceTaskId: 'roof-beasts',
    type: 'photo',
    title: '屋顶上的小兽',
    description: '原来屋顶上有一排小兽。',
    imagePath: '',
    dateLabel: '10月12日',
  },
  {
    id: 'record-palace-gate',
    sourceTaskId: 'palace-gate',
    type: 'photo',
    title: '我最喜欢的宫门',
    description: '拍下了一扇红色宫门。',
    imagePath: '',
    dateLabel: '10月13日',
  },
  {
    id: 'record-dialogue',
    sourceTaskId: '',
    type: 'dialogue',
    title: '亲子对话',
    description: '孩子问：为什么屋顶这么高？',
    imagePath: '',
    dateLabel: '10月14日',
  },
]

const result = generateJourneyRecordData({
  plan,
  tasks,
  mockRecords,
  growthSkills: {
    observation: 1,
    expression: 1,
    initiative: 1,
  },
})

assert.equal(result.summary.title, '故宫亲子探索')
assert.equal(result.summary.destination, '故宫博物院')
assert.equal(result.summary.completedTaskCount, 2)
assert.equal(result.summary.discoveryCount, 3)
assert.equal(result.summary.badgeCount, 1)

assert.equal(result.albumItems.length, 3)
assert.equal(result.albumItems[0].source, 'task')
assert.equal(result.albumItems[0].sourceTaskId, 'roof-beasts')
assert.equal(result.albumItems[0].title, '找屋顶上的小兽')
assert.equal(result.albumItems[0].description, '我发现屋顶上的小兽排成了一队')
assert.equal(result.albumItems[0].imagePath, 'temp://real-roof-photo.jpg')

const roofItems = result.albumItems.filter((item) => item.sourceTaskId === 'roof-beasts')
assert.equal(roofItems.length, 1)

const gateItem = result.albumItems.find((item) => item.sourceTaskId === 'palace-gate')
assert.equal(gateItem.source, 'task')
assert.equal(gateItem.title, '拍一扇宫门')

const gateItems = result.albumItems.filter((item) => item.sourceTaskId === 'palace-gate')
assert.equal(gateItems.length, 1)

const dialogueItem = result.albumItems.find((item) => item.type === 'dialogue')
assert.equal(dialogueItem.title, '亲子对话')

assert.deepEqual(result.growthSkills, {
  observation: 1,
  expression: 1,
  initiative: 1,
})

const emptyResult = generateJourneyRecordData({
  plan: null,
  tasks: [],
  mockRecords,
  growthSkills: {},
})

assert.equal(emptyResult.summary.title, '故宫亲子探索')
assert.equal(emptyResult.summary.destination, '故宫博物院')
assert.equal(emptyResult.summary.completedTaskCount, 0)
assert.equal(emptyResult.summary.badgeCount, 0)
assert.equal(emptyResult.albumItems.length, 3)

const liveTasks = JSON.parse(JSON.stringify(tasks))
liveTasks[0].status = 'not-started'
liveTasks[0].record.imagePath = ''
liveTasks[0].record.note = ''

liveTasks[0].record.imagePath = 'temp://picked-without-refresh.jpg'
liveTasks[0].record.note = '我发现屋顶上的小兽排成了一队'
liveTasks[0].status = 'completed'

const liveResult = generateJourneyRecordData({
  plan,
  tasks: liveTasks,
  mockRecords,
  growthSkills: {
    observation: 1,
    expression: 1,
    initiative: 1,
  },
})

const liveRoofItem = liveResult.albumItems.find((item) => item.sourceTaskId === 'roof-beasts')
assert.equal(liveRoofItem.source, 'task')
assert.equal(liveRoofItem.imagePath, 'temp://picked-without-refresh.jpg')
assert.equal(liveRoofItem.description, '我发现屋顶上的小兽排成了一队')
assert.equal(liveResult.albumItems.filter((item) => item.sourceTaskId === 'roof-beasts').length, 1)

const pagesJson = JSON.parse(readFileSync(join(root, 'src/pages.json'), 'utf8'))
const recordPage = pagesJson.pages.find((page) => page.path === 'pages/record/index')
assert.equal(recordPage?.style?.navigationStyle, 'custom')

const growthBadge = readFileSync(join(root, 'src/components/GrowthBadge.vue'), 'utf8')
assert.match(growthBadge, /white-space:\s*nowrap/)
assert.match(growthBadge, /min-height:\s*[^;]+;/)

console.log('phase5 record journey checks passed')
