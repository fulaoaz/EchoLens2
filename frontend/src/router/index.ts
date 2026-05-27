import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'workbench',
    component: () => import('@/views/Workbench.vue'),
    meta: { title: '工作台' },
  },
  {
    path: '/project/:id',
    name: 'project-detail',
    component: () => import('@/views/ProjectDetail.vue'),
    meta: { title: '项目详情' },
    props: true,
  },
  {
    path: '/project/:id/simulation',
    name: 'simulation',
    component: () => import('@/views/SimulationConsole.vue'),
    meta: { title: '仿真控制台' },
    props: true,
  },
  {
    path: '/project/:id/prediction',
    name: 'prediction',
    component: () => import('@/views/PredictionLab.vue'),
    meta: { title: '预测实验室' },
    props: true,
  },
  {
    path: '/project/:id/decision',
    name: 'decision',
    component: () => import('@/views/DecisionBoard.vue'),
    meta: { title: '决策看板' },
    props: true,
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: '系统设置' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  const t = (to.meta?.title as string | undefined) ?? 'EchoLens 2.0'
  document.title = `${t} · EchoLens 2.0`
})

export default router
