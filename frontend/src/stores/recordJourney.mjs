const defaultSummary = {
  title: '故宫亲子探索',
  destination: '故宫博物院',
  completedTaskCount: 0,
  discoveryCount: 0,
  badgeCount: 0,
}

const rotations = [-2, 1, -1, 2]

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function normalizeId(value) {
  return value === null || value === undefined ? '' : String(value)
}

function createAlbumItem(item, index) {
  return {
    id: item.id,
    sourceTaskId: normalizeId(item.sourceTaskId),
    source: item.source,
    type: item.type || 'photo',
    title: item.title,
    description: item.description,
    displayImagePath: item.displayImagePath || '',
    dateLabel: item.dateLabel || '今天',
    rotation: item.rotation ?? rotations[index % rotations.length],
  }
}

function taskHasRecord(task) {
  return Boolean(
    task?.status === 'completed' ||
      normalizeText(task?.record?.displayImagePath) ||
      normalizeText(task?.record?.note),
  )
}

function createTaskAlbumItem(task, index, mockByTaskId) {
  const sourceTaskId = normalizeId(task.id)
  const mock = mockByTaskId.get(sourceTaskId)
  const note = normalizeText(task.record?.note)
  const subtitle = normalizeText(task.subtitle)

  return createAlbumItem(
    {
      id: `task-${sourceTaskId}`,
      sourceTaskId,
      source: 'task',
      type: mock?.type || 'photo',
      title: normalizeText(task.title) || mock?.title || '探索记录',
      description: note || subtitle || mock?.description || '记录了一次新的旅行发现。',
      displayImagePath: normalizeText(task.record?.displayImagePath) || mock?.imagePath || '',
      dateLabel: '今天',
    },
    index,
  )
}

export function generateJourneyRecordData({
  plan,
  tasks = [],
  mockRecords = [],
  growthSkills = {},
} = {}) {
  const mockByTaskId = new Map(
    mockRecords.filter((record) => record.sourceTaskId).map((record) => [normalizeId(record.sourceTaskId), record]),
  )
  const usedTaskIds = new Set()
  const albumItems = []

  tasks
    .filter(taskHasRecord)
    .sort((left, right) => (left.order || 0) - (right.order || 0))
    .forEach((task) => {
      albumItems.push(createTaskAlbumItem(task, albumItems.length, mockByTaskId))
      usedTaskIds.add(normalizeId(task.id))
    })

  mockRecords.forEach((record) => {
    if (record.sourceTaskId && usedTaskIds.has(normalizeId(record.sourceTaskId))) {
      return
    }

    if (albumItems.length >= 3) {
      return
    }

    albumItems.push(
      createAlbumItem(
        {
          ...record,
          source: 'mock',
        },
        albumItems.length,
      ),
    )
  })

  const completedTaskCount = tasks.filter((task) => task.status === 'completed').length
  const summary = {
    title: normalizeText(plan?.title) || defaultSummary.title,
    destination: normalizeText(plan?.destination) || defaultSummary.destination,
    completedTaskCount,
    discoveryCount: albumItems.length,
    badgeCount: completedTaskCount > 0 ? 1 : 0,
  }

  return {
    summary,
    albumItems,
    growthSkills: {
      observation: Number(growthSkills.observation) || 0,
      expression: Number(growthSkills.expression) || 0,
      initiative: Number(growthSkills.initiative) || 0,
    },
  }
}
