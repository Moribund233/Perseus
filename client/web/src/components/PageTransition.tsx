import { useLocation } from 'react-router-dom';
import { useSpring, animated } from '@react-spring/web';

interface PageTransitionProps {
  children: React.ReactNode;
  /**
   * 撑满父容器高度并在内部滚动 (AppLayout 内的路由页面使用)。
   * 布局依赖 height: 100% 的页面 (聊天/仓库/编辑器) 若外层包装没有
   * 确定高度, 会退化成内容高度, 导致三栏 Panel 无法撑满视口。
   * 独立滚动流页面 (如 Landing) 传 false 保持自然文档流。
   */
  fill?: boolean;
}

export function PageTransition({ children, fill = true }: PageTransitionProps) {
  const location = useLocation();
  const style = useSpring({
    from: { opacity: 0, y: 6 },
    to: { opacity: 1, y: 0 },
    reset: true,
    config: { tension: 280, friction: 30 },
  });

  return (
    <animated.div
      style={{
        ...style,
        ...(fill ? { height: '100%', overflow: 'auto' } : {}),
      }}
      key={location.pathname}
    >
      {children}
    </animated.div>
  );
}
