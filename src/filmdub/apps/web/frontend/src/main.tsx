import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { useAuthStore } from './store/authStore'

// 启动时检测本地免登录模式（AUTH_DISABLED）：命中则自动登录本地用户，无需输入密码
useAuthStore.getState().bootstrap()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
