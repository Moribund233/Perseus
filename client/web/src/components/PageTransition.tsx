import { useLocation } from 'react-router-dom';
import { useSpring, animated } from '@react-spring/web';

export function PageTransition({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const style = useSpring({
    from: { opacity: 0, y: 6 },
    to: { opacity: 1, y: 0 },
    reset: true,
    config: { tension: 280, friction: 30 },
  });

  return (
    <animated.div style={style} key={location.pathname}>
      {children}
    </animated.div>
  );
}
