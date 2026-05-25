import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { JobSnapshot } from '@/api/simulation'
import type { PredictionRun } from '@/api/prediction'

/**
 * 跨页面缓存最近的仿真 / 预测运行，便于全局历史检索。
 * 当前未在视图中订阅，保留为后续 M4 决策看板的状态接入点。
 */
export const useRunsStore = defineStore('runs', () => {
  const simulations = ref<JobSnapshot[]>([])
  const predictions = ref<PredictionRun[]>([])

  function addSimulation(run: JobSnapshot) {
    simulations.value = [run, ...simulations.value]
  }
  function addPrediction(run: PredictionRun) {
    predictions.value = [run, ...predictions.value]
  }

  return { simulations, predictions, addSimulation, addPrediction }
})
