"""데이터 모델 정의"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import date


@dataclass
class Actress:
    name: str                          # 주 표기 이름
    javdb_id: str                      # JavDB 내부 ID (URL slug)
    name_ja: Optional[str] = None      # 일본어 이름
    name_en: Optional[str] = None      # 영문 이름
    aliases: list[str] = field(default_factory=list)
    avatar_url: Optional[str] = None
    db_id: Optional[int] = None        # SQLite rowid


@dataclass
class Video:
    code: str                          # 품번 (예: ABC-123)
    title: Optional[str] = None
    release_date: Optional[str] = None # YYYY-MM-DD
    duration: Optional[int] = None     # 분
    cover_url: Optional[str] = None
    javdb_id: Optional[str] = None     # JavDB video slug
    db_id: Optional[int] = None
