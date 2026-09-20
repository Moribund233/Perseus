import { Skeleton } from 'antd';

interface AdminSkeletonProps {
  /** 面板头部标题（可选） */
  heading?: string | null;
  rows?: number;
}

/** 管理控制台统一骨架屏：ac 主题面板 + antd Skeleton */
export default function AdminSkeleton({ heading, rows = 4 }: AdminSkeletonProps) {
  return (
    <div className="ac-panel" aria-busy="true" aria-label={heading ?? undefined}>
      {heading && <div className="ac-panel-head">{heading}</div>}
      <div className="ac-panel-body">
        <Skeleton active title={{ width: 180 }} paragraph={{ rows }} />
      </div>
    </div>
  );
}