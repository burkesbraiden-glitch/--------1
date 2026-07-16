import { defineStore } from 'pinia'
import { mockGrowthSkills, mockRecords } from '../mock/records'
import { generateJourneyRecordData } from './recordJourney.mjs'

export const useRecordStore = defineStore('record', {
  state: () => ({
    records: mockRecords,
    discoveries: mockRecords.filter((record) => record.type !== 'dialogue'),
    dialogues: mockRecords.filter((record) => record.type === 'dialogue'),
    growthSkills: mockGrowthSkills,
    currentJourneyRecord: generateJourneyRecordData({
      plan: null,
      tasks: [],
      mockRecords,
      growthSkills: mockGrowthSkills,
    }),
  }),
  actions: {
    generateJourneyRecord({ plan, tasks } = {}) {
      const journeyRecord = generateJourneyRecordData({
        plan,
        tasks,
        mockRecords: this.records,
        growthSkills: this.growthSkills,
      })

      this.currentJourneyRecord = journeyRecord

      return journeyRecord
    },
  },
})

