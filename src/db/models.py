from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False, index=True)
    url_hash = Column(String(32), unique=True, nullable=False, index=True)
    source = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text)
    summary = Column(Text)
    category = Column(String)
    language = Column(String(2), default="ko")
    region = Column(String, default="korean")
    published_at = Column(DateTime, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    score = Column(Float, default=0.0)
    status = Column(String, default="new", index=True)
    # status: new | selected | generated | published | failed | skipped


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True, index=True)
    account_handle = Column(String, nullable=True, index=True)
    content_type = Column(String, default="news", index=True)
    demographic = Column(String, nullable=True)
    research_topic = Column(Text, nullable=True)
    slides_json = Column(Text)
    caption = Column(Text)
    hashtags = Column(Text)
    output_dir = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime)
    status = Column(String, default="pending", index=True)
    # status: pending | rendered | uploaded | published | failed
    error_log = Column(Text)


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False, index=True)
    url_hash = Column(String(32), unique=True, nullable=False, index=True)
    source_name = Column(String, nullable=False)
    site = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text)
    top_comments = Column(Text)
    likes = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    views = Column(Integer, default=0)
    category = Column(String)
    published_at = Column(DateTime, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    score = Column(Float, default=0.0)
    status = Column(String, default="new", index=True)


class RunLog(Base):
    __tablename__ = "run_logs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    phase = Column(String)
    success = Column(Boolean, default=False)
    detail = Column(Text)
