#!/usr/bin/env python3
"""
이미지 컬럼 추가 마이그레이션 스크립트
"""

import sys
import os
from pathlib import Path

# 현재 스크립트의 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from sqlalchemy import create_engine, text
from app.utils.config import DATABASE_URL

def run_migration():
    """이미지 컬럼 추가 마이그레이션 실행"""
    try:
        # 데이터베이스 연결
        engine = create_engine(DATABASE_URL)
        
        print("🔄 이미지 컬럼 추가 마이그레이션 시작...")
        
        # 마이그레이션 SQL 파일 읽기
        migration_file = current_dir / "migrations" / "add_image_to_messages.sql"
        
        if not migration_file.exists():
            print(f"❌ 마이그레이션 파일을 찾을 수 없습니다: {migration_file}")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # SQL 실행
        with engine.connect() as connection:
            # 트랜잭션 시작
            trans = connection.begin()
            try:
                # 컬럼이 이미 존재하는지 확인
                result = connection.execute(text("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.columns 
                    WHERE table_name = 'messages' 
                    AND column_name = 'image'
                    AND table_schema = DATABASE()
                """))
                
                column_exists = result.fetchone()[0] > 0
                
                if column_exists:
                    print("✅ image 컬럼이 이미 존재합니다. 마이그레이션을 건너뜁니다.")
                else:
                    # 마이그레이션 실행
                    connection.execute(text("ALTER TABLE messages ADD COLUMN image TEXT NULL COMMENT '이미지 URL 저장'"))
                    print("✅ image 컬럼이 성공적으로 추가되었습니다.")
                
                trans.commit()
                print("✅ 마이그레이션이 완료되었습니다.")
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"❌ 마이그레이션 실행 중 오류 발생: {e}")
                return False
                
    except Exception as e:
        print(f"❌ 데이터베이스 연결 오류: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("이미지 컬럼 추가 마이그레이션")
    print("=" * 50)
    
    success = run_migration()
    
    if success:
        print("\n🎉 마이그레이션이 성공적으로 완료되었습니다!")
    else:
        print("\n💥 마이그레이션이 실패했습니다.")
        sys.exit(1)
