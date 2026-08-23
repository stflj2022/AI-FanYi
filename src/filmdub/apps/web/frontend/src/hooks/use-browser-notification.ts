import { useEffect, useState } from 'react'

interface NotificationOptions {
  title: string
  body?: string
  icon?: string
  tag?: string
  onClick?: () => void
}

export function useBrowserNotification() {
  const [permission, setPermission] = useState<NotificationPermission>('default')

  useEffect(() => {
    if ('Notification' in window) {
      setPermission(Notification.permission)
    }
  }, [])

  const requestPermission = async (): Promise<boolean> => {
    if (!('Notification' in window)) {
      console.warn('Browser does not support notifications')
      return false
    }

    const result = await Notification.requestPermission()
    setPermission(result)
    return result === 'granted'
  }

  const show = ({ title, body, icon, tag, onClick }: NotificationOptions) => {
    if (permission !== 'granted') {
      console.warn('Notification permission not granted')
      return null
    }

    const notification = new Notification(title, {
      body,
      icon: icon || '/favicon.ico',
      tag,
    })

    if (onClick) {
      notification.onclick = () => {
        window.focus()
        onClick()
        notification.close()
      }
    }

    return notification
  }

  const success = (title: string, body?: string, options?: Partial<NotificationOptions>) => {
    return show({
      title,
      body,
      ...options,
    })
  }

  const error = (title: string, body?: string, options?: Partial<NotificationOptions>) => {
    return show({
      title: `❌ ${title}`,
      body,
      ...options,
    })
  }

  return {
    permission,
    requestPermission,
    show,
    success,
    error,
  }
}
