import { useSpring, animated } from '@react-spring/web';

export function PageTransition({ children, id }: { children: React.ReactNode; id?: string }) {
  const style = useSpring({
    from: { opacity: 0, y: 6 },
    to: { opacity: 1, y: 0 },
    reset: true,
    key: id,
    config: { tension: 280, friction: 30 },
  });

  return (
    <animated.div style={style} key={id}>
      {children}
    </animated.div>
  );
}
