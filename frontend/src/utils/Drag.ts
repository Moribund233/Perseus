/**
 * 统一的边框拖拽样式与功能系统
 * 提供简易的拖拽样式应用和功能实现
 */

/**
 * 拖拽方向类型定义
 */
export type DragDirection = 'top' | 'bottom' | 'left' | 'right';
export type DragDirections = DragDirection | DragDirection[];

/**
 * 拖拽配置选项
 */
export interface DragOptions {
  /** 拖拽方向 */
  direction: DragDirections;
  /** 拖拽时的回调函数 */
  onDrag?: (size: number, direction: DragDirection) => void;
  /** 拖拽结束时的回调函数 */
  onDragEnd?: (size: number, direction: DragDirection) => void;
}

/**
 * 拖拽样式类名常量
 */
export const DRAG_CLASSES = {
  base: 'drag-handle',
  top: 'drag-top',
  bottom: 'drag-bottom',
  left: 'drag-left',
  right: 'drag-right',
  active: 'drag-active',
  hover: 'drag-hover'
} as const;

/**
 * 拖拽方向配置接口
 */
interface DragDirectionConfig {
  direction: DragDirection;
  cursor: string;
}

/**
 * 生成拖拽手柄的CSS样式
 * @param config 拖拽方向配置
 */
function generateDragHandleStyle(config: DragDirectionConfig): string {
  const { direction, cursor } = config;
  
  // 只生成当前方向的样式
  switch (direction) {
    case 'top':
      return `
        /* 顶部方向 */
        .${DRAG_CLASSES.base}.${DRAG_CLASSES.top} {
          cursor: ${cursor};
        }
        
        .${DRAG_CLASSES.base}.${DRAG_CLASSES.top}:hover,
        .${DRAG_CLASSES.base}.${DRAG_CLASSES.top}.${DRAG_CLASSES.active} {
          box-shadow: inset 0 4px 0 0 rgba(52, 152, 219, 0.6);
        }
      `;
    
    case 'bottom':
      return `
        /* 底部方向 */
        .${DRAG_CLASSES.base}.${DRAG_CLASSES.bottom} {
          cursor: ${cursor};
        }
        
        .${DRAG_CLASSES.base}.${DRAG_CLASSES.bottom}:hover,
        .${DRAG_CLASSES.base}.${DRAG_CLASSES.bottom}.${DRAG_CLASSES.active} {
          box-shadow: inset 0 -4px 0 0 rgba(52, 152, 219, 0.6);
        }
      `;
    
    case 'left':
      return `
        /* 左侧方向 */
        .${DRAG_CLASSES.base}.${DRAG_CLASSES.left} {
          cursor: ${cursor};
        }
        
        .${DRAG_CLASSES.base}.${DRAG_CLASSES.left}:hover,
        .${DRAG_CLASSES.base}.${DRAG_CLASSES.left}.${DRAG_CLASSES.active} {
          box-shadow: inset 4px 0 0 0 rgba(52, 152, 219, 0.6);
        }
      `;
    
    case 'right':
      return `
        /* 右侧方向 */
        .${DRAG_CLASSES.base}.${DRAG_CLASSES.right} {
          cursor: ${cursor};
        }
        
        .${DRAG_CLASSES.base}.${DRAG_CLASSES.right}:hover,
        .${DRAG_CLASSES.base}.${DRAG_CLASSES.right}.${DRAG_CLASSES.active} {
          box-shadow: inset -4px 0 0 0 rgba(52, 152, 219, 0.6);
        }
      `;
    
    default:
      return '';
  }
}

/**
 * 获取所有拖拽方向的配置
 */
function getDragDirectionConfigs(): DragDirectionConfig[] {
  return [
    {
      direction: 'top',
      cursor: 'ns-resize'
    },
    {
      direction: 'bottom',
      cursor: 'ns-resize'
    },
    {
      direction: 'left',
      cursor: 'ew-resize'
    },
    {
      direction: 'right',
      cursor: 'ew-resize'
    }
  ];
}

/**
 * 初始化拖拽样式系统
 * 将拖拽样式添加到全局样式表中
 */
export function initDragStyles(): void {
  if (typeof document === 'undefined') return;
  
  // 检查是否已经添加过样式
  if (document.getElementById('drag-styles')) return;
  
  // 获取所有拖拽方向的配置并生成样式
  const directionStyleContent = getDragDirectionConfigs()
    .map(config => generateDragHandleStyle(config))
    .join('\n');
  
  const style = document.createElement('style');
  style.id = 'drag-styles';
  style.textContent = `
    /* 基础拖拽手柄样式 */
    .${DRAG_CLASSES.base} {
      position: relative;
      z-index: 10;
      transition: all 0.2s ease;
    }
    
    /* 激活状态 */
    .${DRAG_CLASSES.base}.${DRAG_CLASSES.active} {
      user-select: none;
    }
    
    /* 悬停状态 */
    .${DRAG_CLASSES.base}.${DRAG_CLASSES.hover} {
      user-select: none;
    }
    
    /* 方向样式 */
    ${directionStyleContent}
  `;
  
  document.head.appendChild(style);
}

/**
 * 为元素启用拖拽功能
 * @param element 要启用拖拽的元素
 * @param options 拖拽配置选项
 * @returns 清理函数，用于移除拖拽功能
 */
export function enableDrag(element: HTMLElement, options: DragOptions): () => void {
  // 初始化样式
  initDragStyles();
  
  // 处理拖拽方向：将单个方向转换为数组
  const directions = Array.isArray(options.direction) ? options.direction : [options.direction];
  
  // 添加基础拖拽类
  element.classList.add(DRAG_CLASSES.base);
  
  let isDragging = false;
  let currentDirection: DragDirection | null = null;
  let startPosition = 0;
  let startSize = 0;
  
  // 动态添加/移除方向类名的函数
  const updateDragDirection = (e: MouseEvent) => {
    if (isDragging) return;
    
    // 移除所有方向类名
    directions.forEach(direction => {
      element.classList.remove(DRAG_CLASSES[direction]);
    });
    
    // 确定鼠标位置对应的拖拽方向
    const rect = element.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    
    // 检测鼠标靠近哪个方向的拖拽区域（边缘10px内）
    let direction: DragDirection | null = null;
    if (clickX < 10) direction = 'left';
    else if (clickX > rect.width - 10) direction = 'right';
    else if (clickY < 10) direction = 'top';
    else if (clickY > rect.height - 10) direction = 'bottom';
    
    // 只有检测到方向且该方向在支持的方向列表中，才添加对应的类名
    if (direction && directions.includes(direction)) {
      element.classList.add(DRAG_CLASSES[direction]);
    }
  };
  
  // 鼠标离开时移除所有方向类名
  const clearDragDirection = () => {
    if (isDragging) return;
    directions.forEach(direction => {
      element.classList.remove(DRAG_CLASSES[direction]);
    });
  };
  
  // 获取父容器尺寸作为默认maxSize
  const getParentContainerSize = (direction: DragDirection): number => {
    const parent = element.parentElement;
    if (!parent) return Infinity;
    
    const parentRect = parent.getBoundingClientRect();
    return direction === 'top' || direction === 'bottom' ? parentRect.height : parentRect.width;
  };
  
  // 获取元素初始尺寸作为默认minSize
  const initialSize = {
    width: element.getBoundingClientRect().width,
    height: element.getBoundingClientRect().height
  };
  
  // 鼠标按下事件处理
  const handleMouseDown = (e: MouseEvent) => {
    if (e.button !== 0) return; // 只处理左键点击
    
    // 确定点击位置对应的拖拽方向
    const rect = element.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    
    // 检测点击的是哪个方向的拖拽区域（边缘10px内）
    let direction: DragDirection | null = null;
    if (clickX < 10) direction = 'left';
    else if (clickX > rect.width - 10) direction = 'right';
    else if (clickY < 10) direction = 'top';
    else if (clickY > rect.height - 10) direction = 'bottom';
    
    // 只有点击在支持的拖拽方向上才触发拖拽
    if (!direction || !directions.includes(direction)) return;
    
    isDragging = true;
    currentDirection = direction;
    element.classList.add(DRAG_CLASSES.active, DRAG_CLASSES[direction]);
    
    // 记录初始位置和尺寸
    startPosition = getPosition(e, direction);
    startSize = getCurrentSize(element, direction);
    
    // 阻止默认行为和事件冒泡
    e.preventDefault();
    e.stopPropagation();
    
    // 添加全局事件监听器
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };
  
  // 鼠标移动事件处理
  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging || !currentDirection) {
      // 鼠标未拖拽时，动态更新拖拽方向
      updateDragDirection(e);
      return;
    }
    
    const direction = currentDirection;
    const currentPosition = getPosition(e, direction);
    const delta = startPosition - currentPosition;
    let newSize = startSize;
    
    // 根据拖拽方向计算新尺寸
    switch (direction) {
      case 'top':
      case 'bottom':
        newSize = direction === 'top' ? startSize + delta : startSize - delta;
        break;
      case 'left':
      case 'right':
        newSize = direction === 'left' ? startSize + delta : startSize - delta;
        break;
    }
    
    // 使用默认尺寸限制
    const isVertical = direction === 'top' || direction === 'bottom';
    const minSize = isVertical ? initialSize.height : initialSize.width;
    const maxSize = getParentContainerSize(direction);
    
    // 应用尺寸限制
    newSize = Math.max(newSize, minSize);
    newSize = Math.min(newSize, maxSize);
    
    // 应用新尺寸
    applySize(element, newSize, direction);
    
    // 调用回调函数
    options.onDrag?.(newSize, direction);
  };
  
  // 鼠标抬起事件处理
  const handleMouseUp = () => {
    if (!isDragging || !currentDirection) return;
    
    const direction = currentDirection;
    isDragging = false;
    currentDirection = null;
    element.classList.remove(DRAG_CLASSES.active);
    
    // 移除所有方向类名
    clearDragDirection();
    
    const currentSize = getCurrentSize(element, direction);
    options.onDragEnd?.(currentSize, direction);
    
    // 移除全局事件监听器
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };
  
  // 鼠标悬停事件处理
  const handleMouseEnter = () => {
    element.classList.add(DRAG_CLASSES.hover);
  };
  
  const handleMouseLeave = () => {
    if (!isDragging) {
      element.classList.remove(DRAG_CLASSES.hover);
      // 鼠标离开时清除所有方向类名
      clearDragDirection();
    }
  };
  
  // 添加事件监听器
  element.addEventListener('mousedown', handleMouseDown);
  element.addEventListener('mousemove', updateDragDirection);
  element.addEventListener('mouseenter', handleMouseEnter);
  element.addEventListener('mouseleave', handleMouseLeave);
  
  // 返回清理函数
  return () => {
    element.removeEventListener('mousedown', handleMouseDown);
    element.removeEventListener('mousemove', updateDragDirection);
    element.removeEventListener('mouseenter', handleMouseEnter);
    element.removeEventListener('mouseleave', handleMouseLeave);
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
    
    // 移除方向类名
    directions.forEach(direction => {
      element.classList.remove(DRAG_CLASSES[direction]);
    });
    
    // 移除基础类名
    element.classList.remove(DRAG_CLASSES.base, DRAG_CLASSES.hover, DRAG_CLASSES.active);
  };
}

/**
 * 获取鼠标位置（根据拖拽方向）
 */
function getPosition(e: MouseEvent, direction: DragDirection): number {
  switch (direction) {
    case 'top':
    case 'bottom':
      return e.clientY;
    case 'left':
    case 'right':
      return e.clientX;
    default:
      return 0;
  }
}

/**
 * 获取元素当前尺寸（根据拖拽方向）
 */
function getCurrentSize(element: HTMLElement, direction: DragDirection): number {
  const rect = element.getBoundingClientRect();
  switch (direction) {
    case 'top':
    case 'bottom':
      return rect.height;
    case 'left':
    case 'right':
      return rect.width;
    default:
      return 0;
  }
}

/**
 * 应用新尺寸到元素
 * 针对Flex布局，使用flex-basis来控制尺寸
 */
function applySize(element: HTMLElement, size: number, direction: DragDirection): void {
  // 检查元素是否为Flex子元素及其Flex方向
  const parent = element.parentElement;
  const isFlexChild = parent ? window.getComputedStyle(parent).display === 'flex' : false;
  const flexDirection = isFlexChild && parent ? window.getComputedStyle(parent).flexDirection : 'row';
  
  // 只有当Flex方向与拖拽方向匹配时，才使用flexBasis
  const shouldUseFlexBasis = isFlexChild && 
    ((flexDirection === 'row' && (direction === 'left' || direction === 'right')) ||
     (flexDirection === 'column' && (direction === 'top' || direction === 'bottom')));
  
  switch (direction) {
    case 'top':
    case 'bottom':
      if (shouldUseFlexBasis) {
        element.style.flexBasis = `${size}px`;
      } else {
        element.style.height = `${size}px`;
      }
      break;
    case 'left':
    case 'right':
      if (shouldUseFlexBasis) {
        element.style.flexBasis = `${size}px`;
      } else {
        element.style.width = `${size}px`;
      }
      break;
  }
}

import { ref, onMounted, onUnmounted } from 'vue';

/**
 * Vue组合式函数：为Vue组件提供拖拽功能
 */
export function useDrag(options: DragOptions) {
  const elementRef = ref<HTMLElement>();
  let cleanup: (() => void) | undefined;
  
  const setupDrag = () => {
    if (elementRef.value) {
      cleanup?.(); // 清理之前的拖拽功能
      cleanup = enableDrag(elementRef.value, options);
    }
  };
  
  onMounted(() => {
    setupDrag();
  });
  
  onUnmounted(() => {
    cleanup?.();
  });
  
  return {
    elementRef,
    setupDrag
  };
}

/**
 * 简易应用函数：通过类名快速应用拖拽样式
 * @param element 要应用样式的元素
 * @param direction 拖拽方向
 */
export function applyDragStyle(element: HTMLElement, directions: DragDirections): void {
  initDragStyles();
  
  // 移除所有可能的拖拽方向类，但保留基础类
  Object.values(DRAG_CLASSES).forEach(className => {
    if (className !== DRAG_CLASSES.base) {
      element.classList.remove(className);
    }
  });
  
  // 添加基础类
  element.classList.add(DRAG_CLASSES.base);
  
  // 为每个方向添加对应的类名
  const directionsArray = Array.isArray(directions) ? directions : [directions];
  directionsArray.forEach(direction => {
    element.classList.add(DRAG_CLASSES[direction]);
  });
}