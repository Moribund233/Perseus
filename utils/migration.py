"""
Database migration utilities

Supports exporting/importing data between different database types.
Uses SQLAlchemy to handle dialect differences automatically.

Usage:
    # Export data from SQLite
    python -m utils.migration export sqlite:///./langit.db data_export.json
    
    # Import data to PostgreSQL
    python -m utils.migration import postgresql://user:pass@localhost/dbname data_export.json
    
    # Or use programmatically
    from utils.migration import DatabaseMigration
    migrator = DatabaseMigration()
    migrator.export_data("sqlite:///./source.db", "export.json")
    migrator.import_data("postgresql://user:pass@localhost/target", "export.json")
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from sqlalchemy import create_engine, MetaData, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# Lazy imports to avoid triggering database validation on module import
_models = None
_Base = None


def _get_models():
    """Lazy load models to avoid database validation on import"""
    global _models, _Base
    if _models is None:
        from models import Base
        from models.user import User
        from models.repository import Repository
        from models.repository_member import RepositoryMember
        from models.branch import Branch
        from models.commit import Commit
        from models.pull_request import PullRequest, PRComment, PRReview
        from models.issue import Issue, Label, IssueComment
        
        _Base = Base
        _models = {
            "users": User,
            "repositories": Repository,
            "repository_members": RepositoryMember,
            "branches": Branch,
            "commits": Commit,
            "pull_requests": PullRequest,
            "pr_comments": PRComment,
            "pr_reviews": PRReview,
            "issues": Issue,
            "labels": Label,
            "issue_comments": IssueComment,
        }
    return _Base, _models


class MigrationError(Exception):
    """Database migration error"""
    pass


class DatabaseMigration:
    """
    Database migration tool
    
    Handles exporting and importing data between different database types.
    Uses JSON as intermediate format for cross-database compatibility.
    """
    
    # Define table order for dependency handling (foreign keys)
    export_order = [
        "users",
        "labels",
        "repositories",
        "repository_members",
        "branches",
        "commits",
        "pull_requests",
        "pr_reviews",
        "pr_comments",
        "issues",
        "issue_comments",
    ]
    # Reverse order for import (children first)
    import_order = list(reversed(export_order))
    
    def __init__(self):
        self._models_cache = None
        self._base_cache = None
    
    @property
    def models(self):
        """Lazy load models"""
        if self._models_cache is None:
            self._base_cache, self._models_cache = _get_models()
        return self._models_cache
    
    @property
    def Base(self):
        """Lazy load Base"""
        if self._base_cache is None:
            self._base_cache, self._models_cache = _get_models()
        return self._base_cache
    
    def _get_engine(self, db_url: str) -> Any:
        """Create database engine"""
        try:
            # 处理 PostgreSQL URL，确保使用正确的驱动
            # 优先使用 pg8000 (纯 Python 实现，无需编译)
            if db_url.startswith('postgresql://'):
                db_url = db_url.replace('postgresql://', 'postgresql+pg8000://', 1)
            elif db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql+pg8000://', 1)
            
            # 对于 MySQL，确保使用 pymysql 驱动
            if db_url.startswith('mysql://'):
                db_url = db_url.replace('mysql://', 'mysql+pymysql://', 1)
            
            # 对于 SQLite，添加编码参数
            if db_url.startswith('sqlite://'):
                # 将相对路径转换为绝对路径，避免编码问题
                if db_url.startswith('sqlite:///./'):
                    import os
                    db_path = db_url.replace('sqlite:///./', '')
                    abs_path = os.path.abspath(db_path)
                    db_url = f"sqlite:///{abs_path}"
                return create_engine(db_url, connect_args={'check_same_thread': False})
            
            return create_engine(db_url)
        except Exception as e:
            raise MigrationError(f"Failed to create engine for {db_url}: {e}")
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a single value for JSON"""
        if value is None:
            return None
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (int, float, str, bool)):
            return value
        else:
            return str(value)
    
    def _deserialize_value(self, value: Any, target_type: Any) -> Any:
        """Deserialize a value from JSON"""
        if value is None:
            return None
        elif target_type == datetime and isinstance(value, str):
            return datetime.fromisoformat(value)
        else:
            return value
    
    def export_data(self, source_url: str, output_file: str) -> Dict[str, int]:
        """
        Export all data from source database to JSON file
        
        Args:
            source_url: Source database URL
            output_file: Output JSON file path
            
        Returns:
            Dict mapping table names to row counts
            
        Raises:
            MigrationError: If export fails
        """
        logger.info(f"Exporting data from {source_url}")
        
        engine = self._get_engine(source_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            export_data = {
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "source_url": source_url,
                    "version": "1.0",
                },
                "tables": {}
            }
            
            counts = {}
            
            for table_name in self.export_order:
                model_class = self.models[table_name]
                records = session.query(model_class).all()
                
                table_data = []
                for record in records:
                    row_data = {}
                    for column in record.__table__.columns:
                        value = getattr(record, column.name)
                        row_data[column.name] = self._serialize_value(value)
                    table_data.append(row_data)
                
                export_data["tables"][table_name] = table_data
                counts[table_name] = len(table_data)
                logger.info(f"Exported {len(table_data)} records from {table_name}")
            
            # Write to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=True)
            
            logger.info(f"Export completed: {output_file}")
            return counts
            
        except Exception as e:
            raise MigrationError(f"Export failed: {e}")
        finally:
            session.close()
            engine.dispose()
    
    def import_data(self, target_url: str, input_file: str, 
                   clear_existing: bool = False) -> Dict[str, int]:
        """
        Import data from JSON file to target database
        
        Args:
            target_url: Target database URL
            input_file: Input JSON file path
            clear_existing: Whether to clear existing data before import
            
        Returns:
            Dict mapping table names to imported row counts
            
        Raises:
            MigrationError: If import fails
        """
        logger.info(f"Importing data to {target_url}")
        
        # Load export file
        input_path = Path(input_file)
        if not input_path.exists():
            raise MigrationError(f"Import file not found: {input_file}")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        engine = self._get_engine(target_url)
        
        # Create tables if not exist
        self.Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            counts = {}
            
            # Clear existing data if requested
            if clear_existing:
                logger.warning("Clearing existing data")
                for table_name in self.import_order:
                    model_class = self.models[table_name]
                    session.query(model_class).delete()
                session.commit()
            
            # Import data
            for table_name in self.export_order:  # Use export order for import (parents first)
                if table_name not in export_data["tables"]:
                    logger.warning(f"Table {table_name} not found in export file")
                    continue
                
                model_class = self.models[table_name]
                table_data = export_data["tables"][table_name]
                
                imported_count = 0
                for row_data in table_data:
                    # Deserialize values
                    deserialized_data = {}
                    for column in model_class.__table__.columns:
                        if column.name in row_data:
                            value = row_data[column.name]
                            deserialized_data[column.name] = self._deserialize_value(
                                value, column.type.python_type if hasattr(column.type, 'python_type') else str
                            )
                    
                    # Create instance
                    instance = model_class(**deserialized_data)
                    session.add(instance)
                    imported_count += 1
                
                session.commit()
                counts[table_name] = imported_count
                logger.info(f"Imported {imported_count} records to {table_name}")
            
            logger.info(f"Import completed to {target_url}")
            return counts
            
        except Exception as e:
            session.rollback()
            raise MigrationError(f"Import failed: {e}")
        finally:
            session.close()
            engine.dispose()
    
    def migrate(self, source_url: str, target_url: str, 
               temp_file: Optional[str] = None) -> Dict[str, int]:
        """
        Direct migration from source to target database
        
        Args:
            source_url: Source database URL
            target_url: Target database URL
            temp_file: Temporary file for data (optional, auto-generated if not provided)
            
        Returns:
            Dict mapping table names to migrated row counts
        """
        import tempfile
        import os
        
        # 标记是否由本方法创建的临时文件
        auto_created = False
        
        if not temp_file:
            # 使用系统临时目录，避免 Windows 路径编码问题
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"langit_migration_{timestamp}.json")
            auto_created = True
        
        try:
            # Export
            logger.info(f"Starting export from: {source_url}")
            export_counts = self.export_data(source_url, temp_file)
            logger.info(f"Exported {sum(export_counts.values())} total records")
            
            # Import
            logger.info(f"Starting import to: {target_url}")
            import_counts = self.import_data(target_url, temp_file, clear_existing=True)
            logger.info(f"Imported {sum(import_counts.values())} total records")
            
            return import_counts
            
        except Exception as e:
            import traceback
            logger.error(f"Migration failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise MigrationError(f"Migration failed: {e}")
        finally:
            # 清理临时文件（仅在自动创建时）
            if auto_created and temp_file and Path(temp_file).exists():
                try:
                    Path(temp_file).unlink()
                    logger.info(f"临时文件已清理: {temp_file}")
                except Exception as cleanup_error:
                    logger.warning(f"清理临时文件失败: {cleanup_error}")


def main():
    """Command line interface for migration tool"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="Database migration tool for LanGit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export from SQLite
  python -m utils.migration export sqlite:///./langit.db export.json
  
  # Import to PostgreSQL
  python -m utils.migration import postgresql://user:pass@localhost/dbname export.json
  
  # Direct migration (SQLite to PostgreSQL)
  python -m utils.migration migrate sqlite:///./langit.db postgresql://user:pass@localhost/dbname
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export data from database")
    export_parser.add_argument("source", help="Source database URL")
    export_parser.add_argument("output", help="Output JSON file")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import data to database")
    import_parser.add_argument("target", help="Target database URL")
    import_parser.add_argument("input", help="Input JSON file")
    import_parser.add_argument("--clear", action="store_true", 
                              help="Clear existing data before import")
    
    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Direct migration")
    migrate_parser.add_argument("source", help="Source database URL")
    migrate_parser.add_argument("target", help="Target database URL")
    migrate_parser.add_argument("--keep-temp", action="store_true",
                               help="Keep temporary export file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    migrator = DatabaseMigration()
    
    try:
        if args.command == "export":
            counts = migrator.export_data(args.source, args.output)
            print("\nExport Summary:")
            for table, count in counts.items():
                print(f"  {table}: {count} records")
                
        elif args.command == "import":
            counts = migrator.import_data(args.target, args.input, args.clear)
            print("\nImport Summary:")
            for table, count in counts.items():
                print(f"  {table}: {count} records")
                
        elif args.command == "migrate":
            temp_file = None if args.keep_temp else ""
            counts = migrator.migrate(args.source, args.target, temp_file)
            print("\nMigration Summary:")
            for table, count in counts.items():
                print(f"  {table}: {count} records")
                
    except MigrationError as e:
        logger.error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
