"""Research module database models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for research models."""

    pass


class Project(Base):
    """Research project information."""

    __tablename__ = "research_projects"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    canonical_title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_title: Mapped[Optional[str]] = mapped_column(String(500))
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(50))
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wikidata_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    imdb_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    episodes: Mapped[list["Episode"]] = relationship("Episode", back_populates="project", cascade="all, delete-orphan")
    actors: Mapped[list["Actor"]] = relationship("Actor", back_populates="project", cascade="all, delete-orphan")
    characters: Mapped[list["Character"]] = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    sources: Mapped[list["Source"]] = relationship("Source", back_populates="project", cascade="all, delete-orphan")
    evidence: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="project", cascade="all, delete-orphan")
    relationships: Mapped[list["Relationship"]] = relationship("Relationship", back_populates="project", cascade="all, delete-orphan")
    jobs: Mapped[list["ResearchJob"]] = relationship("ResearchJob", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_research_projects_canonical_title", "canonical_title"),
        Index("ix_research_projects_year", "year"),
    )


class Episode(Base):
    """Episode information."""

    __tablename__ = "research_episodes"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_projects.id"), nullable=False, )
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    episode: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    original_title: Mapped[Optional[str]] = mapped_column(String(500))
    air_date: Mapped[Optional[str]] = mapped_column(String(50))
    runtime: Mapped[Optional[int]] = mapped_column(Integer)
    overview: Mapped[Optional[str]] = mapped_column(Text)
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, )
    wikidata_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="episodes")
    appearances: Mapped[list["Appearance"]] = relationship("Appearance", back_populates="episode", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_research_episodes_project_id", "project_id"),
        Index("ix_research_episodes_season_episode", "season", "episode"),
        UniqueConstraint("project_id", "season", "episode", name="uq_research_episodes_season_episode"),
    )


class Actor(Base):
    """Actor information."""

    __tablename__ = "research_actors"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_projects.id"), nullable=False, )
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[Optional[str]] = mapped_column(String(500))
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, )
    wikidata_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    imdb_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    birth_date: Mapped[Optional[str]] = mapped_column(String(50))
    profile_path: Mapped[Optional[str]] = mapped_column(String(500))
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="actors")
    characters: Mapped[list["Character"]] = relationship("Character", back_populates="actor", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_research_actors_project_id", "project_id"),
        Index("ix_research_actors_canonical_name", "canonical_name"),
    )


class Character(Base):
    """Character information."""

    __tablename__ = "research_characters"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_projects.id"), nullable=False, )
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[Optional[str]] = mapped_column(String(500))
    actor_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("research_actors.id"), nullable=True, )
    character_type: Mapped[Optional[str]] = mapped_column(String(50))  # main, recurring, guest, etc.
    description: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="characters")
    actor: Mapped[Optional["Actor"]] = relationship("Actor", back_populates="characters")
    aliases: Mapped[list["CharacterAlias"]] = relationship("CharacterAlias", back_populates="character", cascade="all, delete-orphan")
    appearances: Mapped[list["Appearance"]] = relationship("Appearance", back_populates="character", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_research_characters_project_id", "project_id"),
        Index("ix_research_characters_canonical_name", "canonical_name"),
        Index("ix_research_characters_actor_id", "actor_id"),
    )


class CharacterAlias(Base):
    """Character aliases."""

    __tablename__ = "research_character_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_characters.id"), nullable=False, )
    alias: Mapped[str] = mapped_column(String(500), nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(10))
    source_id: Mapped[Optional[str]] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relationships
    character: Mapped["Character"] = relationship("Character", back_populates="aliases")

    __table_args__ = (
        Index("ix_research_character_aliases_character_id", "character_id"),
    )


class Appearance(Base):
    """Character appearance in episodes."""

    __tablename__ = "research_appearances"

    character_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_characters.id"), nullable=False, primary_key=True)
    episode_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_episodes.id"), nullable=False, primary_key=True)
    appearance_type: Mapped[str] = mapped_column(String(50), nullable=False, )  # main, recurring, guest, mentioned
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lines_count: Mapped[Optional[int]] = mapped_column(Integer)
    screen_time_seconds: Mapped[Optional[float]] = mapped_column(Float)

    # Relationships
    character: Mapped["Character"] = relationship("Character", back_populates="appearances")
    episode: Mapped["Episode"] = relationship("Episode", back_populates="appearances")

    __table_args__ = (
        Index("ix_research_appearances_character_id", "character_id"),
        Index("ix_research_appearances_episode_id", "episode_id"),
        Index("ix_research_appearances_type", "appearance_type"),
    )


class Relationship(Base):
    """Character relationships."""

    __tablename__ = "research_relationships"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_projects.id"), nullable=False, )
    subject_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_characters.id"), nullable=False, )
    relation: Mapped[str] = mapped_column(String(100), nullable=False, )  # spouse, parent, friend, etc.
    object_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_characters.id"), nullable=False, )
    valid_from_episode_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("research_episodes.id"))
    valid_to_episode_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("research_episodes.id"))
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_ids: Mapped[Optional[str]] = mapped_column(Text)  # JSON array of evidence IDs
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="relationships")

    __table_args__ = (
        Index("ix_research_relationships_project_id", "project_id"),
        Index("ix_research_relationships_subject_id", "subject_id"),
        Index("ix_research_relationships_object_id", "object_id"),
        Index("ix_research_relationships_relation", "relation"),
    )


class Source(Base):
    """Research sources."""

    __tablename__ = "research_sources"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_projects.id"), nullable=False, )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, )  # tmdb, wikidata, wikipedia, web, etc.
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))
    reliability: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")  # pending, success, failed
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="sources")
    evidence: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_research_sources_project_id", "project_id"),
        Index("ix_research_sources_type", "source_type"),
        Index("ix_research_sources_status", "status"),
    )


class Evidence(Base):
    """Evidence facts."""

    __tablename__ = "research_evidence"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_projects.id"), nullable=False, )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, )  # project, episode, actor, character
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, )
    predicate: Mapped[str] = mapped_column(String(100), nullable=False, )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_sources.id"), nullable=False, )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="evidence")
    source: Mapped["Source"] = relationship("Source", back_populates="evidence")

    __table_args__ = (
        Index("ix_research_evidence_project_id", "project_id"),
        Index("ix_research_evidence_entity", "entity_type", "entity_id"),
        Index("ix_research_evidence_predicate", "predicate"),
        Index("ix_research_evidence_source_id", "source_id"),
    )


class ResearchJob(Base):
    """Research job tracking."""

    __tablename__ = "research_jobs"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("research_projects.id"), nullable=False, )
    step: Mapped[str] = mapped_column(String(50), nullable=False, )  # identity, tmdb, wikidata, web, extraction, resolution, verification, manifest
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="QUEUED", )  # QUEUED, RUNNING, SUCCESS, SUCCESS_WITH_WARNINGS, FAILED, SKIPPED
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    output_data: Mapped[Optional[str]] = mapped_column(Text)  # JSON output
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="jobs")

    __table_args__ = (
        Index("ix_research_jobs_project_id", "project_id"),
        Index("ix_research_jobs_step", "step"),
        Index("ix_research_jobs_status", "status"),
    )
