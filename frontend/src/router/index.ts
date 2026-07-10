import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/manage' },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { title: 'Log in' },
    },
    {
      path: '/new',
      name: 'new-link',
      component: () => import('../views/NewLinkView.vue'),
      meta: { requiresAuth: true, title: 'New Link' },
    },
    {
      path: '/manage',
      name: 'manage',
      component: () => import('../views/ManageView.vue'),
      meta: { requiresAuth: true, title: 'Manage Links' },
    },
    {
      path: '/links/:code/share',
      name: 'share',
      component: () => import('../views/ShareView.vue'),
      meta: { requiresAuth: true, title: 'Share Link' },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/ProfileView.vue'),
      meta: { requiresAuth: true, title: 'Profile' },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('../views/AdminView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true, title: 'User Management' },
    },
    {
      path: '/p/:code',
      name: 'password-gate',
      component: () => import('../views/PasswordGateView.vue'),
    },
    {
      path: '/expired',
      name: 'expired',
      component: () => import('../views/ExpiredView.vue'),
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  // Only hydrate auth state for routes that actually need it — calling
  // restore() on public routes (e.g. /p/:code) 401s for anonymous visitors,
  // which trips the global axios interceptor and force-redirects to /login
  // before the public page ever gets to render.
  if ((to.meta.requiresAuth || to.meta.requiresAdmin) && !auth.isAuthenticated) {
    await auth.restore()
  }
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return '/login'
  }
  if (to.meta.requiresAdmin && !auth.user?.is_admin) {
    return '/manage'
  }
})

export default router
