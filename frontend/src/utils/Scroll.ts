/**
 * 滚动工具类
 * 提供水平滚动功能，解决纯CSS样式无法通过鼠标滚轮触发水平滚动的问题
 */

/**
 * 滚动方向类型
 */
export type ScrollDirection = 'horizontal' | 'vertical' | 'both'

/**
 * 滚动配置选项
 */
export interface ScrollOptions {
  /** 滚动速度系数，默认1.0 */
  speed?: number
  /** 是否启用平滑滚动，默认true */
  smooth?: boolean
  /** 是否在滚动时显示滚动条，默认false */
  showScrollbar?: boolean
  /** 滚动条显示时间（毫秒），默认2000 */
  scrollbarTimeout?: number
  /** 滚动方向，默认'both' */
  direction?: ScrollDirection
  /** 是否将垂直滚轮转换为水平滚动，默认false */
  wheelToHorizontal?: boolean
}

/**
 * 检测元素是否可以水平滚动
 * @param element 目标元素
 * @returns 是否可以水平滚动
 */
export function canScrollHorizontally(element: HTMLElement): boolean {
  return element.scrollWidth > element.clientWidth
}

/**
 * 检测元素是否可以垂直滚动
 * @param element 目标元素
 * @returns 是否可以垂直滚动
 */
export function canScrollVertically(element: HTMLElement): boolean {
  return element.scrollHeight > element.clientHeight
}

/**
 * 滚动功能
 * @param element 需要启用滚动的元素
 * @param options 配置选项
 * @returns 清理函数，用于移除事件监听器
 */
export function useScroll(
  element: HTMLElement,
  options: ScrollOptions = {}
): () => void {
  const {
    speed = 1.0,
    smooth = true,
    showScrollbar = false,
    scrollbarTimeout = 2000,
    direction = 'both',
    wheelToHorizontal = false
  } = options

  // 添加滚动样式类
  if (direction === 'horizontal' || direction === 'both') {
    element.classList.add('scrollbar-horizontal')
    if (!showScrollbar) {
      element.classList.add('scrollbar-horizontal-hide')
    }
  }
  if (direction === 'vertical' || direction === 'both') {
    element.classList.add('scrollbar-vertical')
    if (!showScrollbar) {
      element.classList.add('scrollbar-vertical-hide')
    }
  }
  if (smooth) {
    element.classList.add('scroll-smooth')
  }

  /**
   * 临时显示滚动条
   */
  let scrollbarTimeoutId: number | null = null
  const showTemporaryScrollbar = () => {
    if (direction === 'horizontal' || direction === 'both') {
      element.classList.remove('scrollbar-horizontal-hide')
    }
    if (direction === 'vertical' || direction === 'both') {
      element.classList.remove('scrollbar-vertical-hide')
    }
    
    // 清除之前的定时器
    if (scrollbarTimeoutId) {
      clearTimeout(scrollbarTimeoutId)
    }
    
    // 设置新的定时器隐藏滚动条
    scrollbarTimeoutId = setTimeout(() => {
      if (direction === 'horizontal' || direction === 'both') {
        element.classList.add('scrollbar-horizontal-hide')
      }
      if (direction === 'vertical' || direction === 'both') {
        element.classList.add('scrollbar-vertical-hide')
      }
      scrollbarTimeoutId = null
    }, scrollbarTimeout) as unknown as number
  }

  /**
   * 鼠标滚轮事件处理函数
   * @param event 鼠标滚轮事件
   */
  const handleWheel = (event: WheelEvent) => {
    // 检测元素的滚动能力
    const canScrollH = direction !== 'vertical' && canScrollHorizontally(element)
    const canScrollV = direction !== 'horizontal' && canScrollVertically(element)
    
    // 计算滚动方向（水平分量 vs 垂直分量）
    const isHorizontalScroll = Math.abs(event.deltaX) > Math.abs(event.deltaY)
    
    let prevented = false
    
    // 处理水平滚动
    if (canScrollH) {
      // 如果启用了垂直滚轮转水平滚动，或者检测到水平滚动意图
      if (wheelToHorizontal || isHorizontalScroll || !canScrollV) {
        // 计算滚动量，垂直滚轮转换为水平滚动时使用deltaY
        const scrollDelta = wheelToHorizontal ? event.deltaY : event.deltaX
        const scrollAmount = scrollDelta * speed
        element.scrollLeft += scrollAmount
        prevented = true
      }
    }
    
    // 处理垂直滚动
    if (canScrollV && (!isHorizontalScroll || !canScrollH) && !prevented) {
      // 垂直滚动使用默认行为，不需要preventDefault
      // 只有当同时需要水平滚动时，才阻止默认行为
      if (prevented) {
        event.preventDefault()
      }
    } else if (prevented) {
      // 如果只处理了水平滚动，也需要阻止默认行为
      event.preventDefault()
    }
    
    // 如果需要显示滚动条，临时显示
    if (showScrollbar && (canScrollH || canScrollV)) {
      showTemporaryScrollbar()
    }
  }

  /**
   * 键盘事件处理函数（支持箭头键滚动）
   * @param event 键盘事件
   */
  const handleKeydown = (event: KeyboardEvent) => {
    if (event.target !== element && !element.contains(event.target as Node)) {
      return
    }
    
    const scrollStep = 50 // 每次滚动的像素数
    let handled = false
    
    switch (event.key) {
      case 'ArrowLeft':
        if (direction === 'horizontal' || direction === 'both') {
          event.preventDefault()
          element.scrollLeft -= scrollStep
          handled = true
        }
        break
      case 'ArrowRight':
        if (direction === 'horizontal' || direction === 'both') {
          event.preventDefault()
          element.scrollLeft += scrollStep
          handled = true
        }
        break
      case 'ArrowUp':
        if (direction === 'vertical' || direction === 'both') {
          event.preventDefault()
          element.scrollTop -= scrollStep
          handled = true
        }
        break
      case 'ArrowDown':
        if (direction === 'vertical' || direction === 'both') {
          event.preventDefault()
          element.scrollTop += scrollStep
          handled = true
        }
        break
      case 'Home':
        if (direction === 'horizontal' || direction === 'both') {
          event.preventDefault()
          element.scrollLeft = 0
          handled = true
        }
        if (direction === 'vertical' || direction === 'both') {
          event.preventDefault()
          element.scrollTop = 0
          handled = true
        }
        break
      case 'End':
        if (direction === 'horizontal' || direction === 'both') {
          event.preventDefault()
          element.scrollLeft = element.scrollWidth
          handled = true
        }
        if (direction === 'vertical' || direction === 'both') {
          event.preventDefault()
          element.scrollTop = element.scrollHeight
          handled = true
        }
        break
    }
    
    // 如果需要显示滚动条，临时显示
    if (showScrollbar && handled) {
      showTemporaryScrollbar()
    }
  }

  /**
   * 触摸事件处理函数（支持触摸滑动滚动）
   */
  let touchStartX = 0
  let touchStartY = 0
  let touchStartScrollLeft = 0
  let touchStartScrollTop = 0
  
  const handleTouchStart = (event: TouchEvent) => {
    touchStartX = event.touches[0].clientX
    touchStartY = event.touches[0].clientY
    touchStartScrollLeft = element.scrollLeft
    touchStartScrollTop = element.scrollTop
  }
  
  const handleTouchMove = (event: TouchEvent) => {
    if (!touchStartX && !touchStartY) return
    
    const touchX = event.touches[0].clientX
    const touchY = event.touches[0].clientY
    const diffX = touchStartX - touchX
    const diffY = touchStartY - touchY
    
    if (direction === 'horizontal' || direction === 'both') {
      element.scrollLeft = touchStartScrollLeft + diffX
    }
    if (direction === 'vertical' || direction === 'both') {
      element.scrollTop = touchStartScrollTop + diffY
    }
    
    // 如果需要显示滚动条，临时显示
    if (showScrollbar) {
      showTemporaryScrollbar()
    }
  }
  
  const handleTouchEnd = () => {
    touchStartX = 0
    touchStartY = 0
    touchStartScrollLeft = 0
    touchStartScrollTop = 0
  }

  // 添加事件监听器
  element.addEventListener('wheel', handleWheel, { passive: false })
  document.addEventListener('keydown', handleKeydown)
  element.addEventListener('touchstart', handleTouchStart)
  element.addEventListener('touchmove', handleTouchMove)
  element.addEventListener('touchend', handleTouchEnd)

  /**
   * 清理函数，移除所有事件监听器
   */
  const cleanup = () => {
    element.removeEventListener('wheel', handleWheel)
    document.removeEventListener('keydown', handleKeydown)
    element.removeEventListener('touchstart', handleTouchStart)
    element.removeEventListener('touchmove', handleTouchMove)
    element.removeEventListener('touchend', handleTouchEnd)
    
    // 清除定时器
    if (scrollbarTimeoutId) {
      clearTimeout(scrollbarTimeoutId)
    }
    
    // 移除样式类
    element.classList.remove('scrollbar-horizontal', 'scrollbar-vertical', 'scroll-smooth')
    element.classList.remove('scrollbar-horizontal-hide', 'scrollbar-vertical-hide')
  }

  return cleanup
}

/**
 * 水平滚动功能（向下兼容）
 * @param element 需要启用水平滚动的元素
 * @param options 配置选项
 * @returns 清理函数，用于移除事件监听器
 */
export function useHorizontalScroll(
  element: HTMLElement,
  options: Omit<ScrollOptions, 'direction'> = {}
): () => void {
  return useScroll(element, { ...options, direction: 'horizontal' })
}

/**
 * 便捷函数：为元素启用滚动
 * @param selector CSS选择器
 * @param options 配置选项
 * @returns 清理函数数组
 */
export function enableScroll(
  selector: string,
  options?: ScrollOptions
): (() => void)[] {
  const elements = document.querySelectorAll<HTMLElement>(selector)
  const cleanups: (() => void)[] = []
  
  elements.forEach(element => {
    const cleanup = useScroll(element, options)
    cleanups.push(cleanup)
  })
  
  return cleanups
}

/**
 * 便捷函数：为元素启用水平滚动（向下兼容）
 * @param selector CSS选择器
 * @param options 配置选项
 * @returns 清理函数数组
 */
export function enableHorizontalScroll(
  selector: string,
  options?: Omit<ScrollOptions, 'direction'>
): (() => void)[] {
  const elements = document.querySelectorAll<HTMLElement>(selector)
  const cleanups: (() => void)[] = []
  
  elements.forEach(element => {
    const cleanup = useHorizontalScroll(element, options)
    cleanups.push(cleanup)
  })
  
  return cleanups
}

/**
 * 滚动到指定位置
 * @param element 目标元素
 * @param position 滚动位置（像素或百分比）
 * @param smooth 是否平滑滚动
 * @param scrollDirection 滚动方向，默认'horizontal'
 */
export function scrollToPosition(
  element: HTMLElement,
  position: number | string | { left?: number | string; top?: number | string },
  smooth = true,
  scrollDirection: ScrollDirection = 'horizontal'
): void {
  if (smooth) {
    element.classList.add('scroll-smooth')
  }
  
  const handleScrollPosition = (pos: number | string, scrollProp: 'scrollLeft' | 'scrollTop', maxSize: number) => {
    if (typeof pos === 'string' && pos.endsWith('%')) {
      const percent = parseFloat(pos) / 100
      element[scrollProp] = maxSize * percent
    } else {
      element[scrollProp] = Number(pos)
    }
  }
  
  // 处理对象形式的位置参数
  if (typeof position === 'object') {
    if (position.left !== undefined && (scrollDirection === 'horizontal' || scrollDirection === 'both')) {
      handleScrollPosition(position.left, 'scrollLeft', element.scrollWidth)
    }
    if (position.top !== undefined && (scrollDirection === 'vertical' || scrollDirection === 'both')) {
      handleScrollPosition(position.top, 'scrollTop', element.scrollHeight)
    }
  } else {
    // 处理单个位置参数
    if (scrollDirection === 'horizontal' || scrollDirection === 'both') {
      handleScrollPosition(position, 'scrollLeft', element.scrollWidth)
    }
    if (scrollDirection === 'vertical') {
      handleScrollPosition(position, 'scrollTop', element.scrollHeight)
    }
  }
  
  if (smooth) {
    // 平滑滚动完成后移除样式类
    setTimeout(() => {
      element.classList.remove('scroll-smooth')
    }, 500)
  }
}

/**
 * 获取滚动信息
 * @param element 目标元素
 * @returns 滚动信息对象
 */
export function getScrollInfo(element: HTMLElement): {
  horizontal: {
    scrollLeft: number
    scrollWidth: number
    clientWidth: number
    scrollable: boolean
    scrollPercentage: number
  }
  vertical: {
    scrollTop: number
    scrollHeight: number
    clientHeight: number
    scrollable: boolean
    scrollPercentage: number
  }
} {
  return {
    horizontal: {
      scrollLeft: element.scrollLeft,
      scrollWidth: element.scrollWidth,
      clientWidth: element.clientWidth,
      scrollable: canScrollHorizontally(element),
      scrollPercentage: element.scrollWidth > element.clientWidth ? (element.scrollLeft / (element.scrollWidth - element.clientWidth)) * 100 : 0
    },
    vertical: {
      scrollTop: element.scrollTop,
      scrollHeight: element.scrollHeight,
      clientHeight: element.clientHeight,
      scrollable: canScrollVertically(element),
      scrollPercentage: element.scrollHeight > element.clientHeight ? (element.scrollTop / (element.scrollHeight - element.clientHeight)) * 100 : 0
    }
  }
}

/**
 * 获取水平滚动信息（向下兼容）
 * @param element 目标元素
 * @returns 滚动信息对象
 */
export function getHorizontalScrollInfo(element: HTMLElement): {
  scrollLeft: number
  scrollWidth: number
  clientWidth: number
  scrollable: boolean
  scrollPercentage: number
} {
  return getScrollInfo(element).horizontal
}