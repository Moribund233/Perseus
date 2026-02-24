"""
自动依赖发现模块

从 SQLAlchemy 模型中自动提取表之间的外键依赖关系，
替代手动维护的 TABLE_DEPENDENCIES。

使用方法:
    from utils.migration.auto_dependency import DependencyResolver
    
    resolver = DependencyResolver(source_connection)
    sorted_tables = resolver.get_sorted_tables()
"""

from typing import Dict, List, Set, Optional
from collections import defaultdict
import logging

from sqlalchemy import inspect
from sqlalchemy.orm import RelationshipProperty

from utils.migration.connection import Connection

logger = logging.getLogger(__name__)


class DependencyResolver:
    """
    自动依赖解析器
    
    通过分析数据库外键约束，自动构建表依赖关系图，
    并提供拓扑排序功能。
    """
    
    def __init__(self, conn: Connection):
        """
        初始化依赖解析器
        
        Args:
            conn: 数据库连接
        """
        self.conn = conn
        self._inspector = inspect(conn.engine)
        self._dependency_cache: Optional[Dict[str, Set[str]]] = None
    
    def get_foreign_keys(self, table_name: str) -> List[Dict]:
        """
        获取表的外键信息
        
        Args:
            table_name: 表名
            
        Returns:
            List[Dict]: 外键列表，每个外键包含 'referred_table' 字段
        """
        try:
            return self._inspector.get_foreign_keys(table_name)
        except Exception as e:
            logger.warning(f"获取表 {table_name} 的外键信息失败: {e}")
            return []
    
    def build_dependency_graph(self) -> Dict[str, Set[str]]:
        """
        构建表依赖关系图
        
        通过分析所有表的外键约束，构建依赖关系：
        - key: 子表名
        - value: 父表名集合（该表依赖的表）
        
        Returns:
            Dict[str, Set[str]]: 依赖关系图
        """
        if self._dependency_cache is not None:
            return self._dependency_cache
        
        # 获取所有表
        all_tables = self._inspector.get_table_names()
        
        # 构建依赖图：子表 -> 父表集合
        dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        
        for table in all_tables:
            fks = self.get_foreign_keys(table)
            for fk in fks:
                # 外键指向的表是父表
                referred_table = fk.get('referred_table')
                if referred_table and referred_table in all_tables:
                    dependency_graph[table].add(referred_table)
                    logger.debug(f"发现依赖: {table} -> {referred_table}")
        
        # 确保所有表都在图中（包括没有外键的表）
        for table in all_tables:
            if table not in dependency_graph:
                dependency_graph[table] = set()
        
        self._dependency_cache = dict(dependency_graph)
        return self._dependency_cache
    
    def topological_sort(self, tables: Optional[List[str]] = None) -> List[str]:
        """
        对表进行拓扑排序
        
        确保父表先于子表，满足外键约束的插入顺序。
        
        Args:
            tables: 要排序的表名列表，None 表示所有表
            
        Returns:
            List[str]: 排序后的表名列表
        """
        graph = self.build_dependency_graph()
        
        if tables is not None:
            # 只保留指定的表
            graph = {k: v & set(tables) for k, v in graph.items() if k in tables}
        else:
            tables = list(graph.keys())
        
        # Kahn 算法进行拓扑排序
        in_degree = {table: 0 for table in tables}
        
        # 计算入度
        for table, parents in graph.items():
            if table in in_degree:
                in_degree[table] = len(parents)
        
        # 找到所有入度为0的节点（没有依赖的表）
        queue = [table for table, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # 按字母顺序处理，确保结果可预测
            queue.sort()
            current = queue.pop(0)
            result.append(current)
            
            # 减少依赖当前表的节点的入度
            for table, parents in graph.items():
                if current in parents and table in in_degree:
                    in_degree[table] -= 1
                    if in_degree[table] == 0:
                        queue.append(table)
        
        # 检查是否有循环依赖
        if len(result) != len(tables):
            remaining = set(tables) - set(result)
            logger.warning(f"以下表可能存在循环依赖，将按原顺序追加: {remaining}")
            result.extend(sorted(remaining))
        
        return result
    
    def get_sorted_tables(self) -> List[str]:
        """
        获取按依赖关系排序的所有表
        
        Returns:
            List[str]: 排序后的表名列表（父表在前）
        """
        return self.topological_sort()
    
    def get_migration_order(self, tables: Optional[List[str]] = None) -> List[str]:
        """
        获取数据迁移顺序
        
        与 topological_sort 相同，但提供更语义化的方法名。
        
        Args:
            tables: 要排序的表名列表
            
        Returns:
            List[str]: 迁移顺序（父表 -> 子表）
        """
        return self.topological_sort(tables)
    
    def get_reverse_migration_order(self, tables: Optional[List[str]] = None) -> List[str]:
        """
        获取反向迁移顺序（用于删除数据）
        
        删除数据时需要先删除子表，再删除父表。
        
        Args:
            tables: 要排序的表名列表
            
        Returns:
            List[str]: 反向迁移顺序（子表 -> 父表）
        """
        order = self.topological_sort(tables)
        return list(reversed(order))
    
    def print_dependency_tree(self, tables: Optional[List[str]] = None):
        """
        打印依赖树（用于调试）
        """
        graph = self.build_dependency_graph()
        
        if tables is None:
            tables = list(graph.keys())
        
        print("表依赖关系:")
        print("-" * 40)
        
        sorted_tables = self.topological_sort(tables)
        
        for table in sorted_tables:
            parents = graph.get(table, set())
            if parents:
                parent_str = ", ".join(sorted(parents))
                print(f"  {table} → 依赖: {parent_str}")
            else:
                print(f"  {table} → (无依赖)")


# 向后兼容：提供与手动依赖相同的接口
def get_table_dependencies(conn: Connection) -> Dict[str, Set[str]]:
    """
    获取表依赖关系（兼容接口）
    
    Args:
        conn: 数据库连接
        
    Returns:
        Dict[str, Set[str]]: 表依赖关系图
    """
    resolver = DependencyResolver(conn)
    return resolver.build_dependency_graph()


def sort_tables_by_dependency(conn: Connection, tables: Optional[List[str]] = None) -> List[str]:
    """
    按依赖关系排序表（兼容接口）
    
    Args:
        conn: 数据库连接
        tables: 要排序的表名列表
        
    Returns:
        List[str]: 排序后的表名列表
    """
    resolver = DependencyResolver(conn)
    return resolver.topological_sort(tables)
