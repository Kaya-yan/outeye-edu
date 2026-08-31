"""
教学课件工作台相关模型
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class CoursewareProject(Base):
    """课件项目"""
    __tablename__ = "courseware_projects"

    id = Column(String(36), primary_key=True, index=True)
    owner_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    source_type = Column(String(30), default="from_plan", nullable=False, index=True)
    source_plan_id = Column(String(36), nullable=True, index=True)
    mode = Column(String(20), default="slides", nullable=False, index=True)
    template_id = Column(String(100), default="classroom_default", nullable=False)
    status = Column(String(30), default="draft", nullable=False, index=True)
    source_meta = Column(JSON, nullable=True)
    current_version_id = Column(String(36), nullable=True, index=True)
    presentation_profile_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="courseware_projects")
    versions = relationship(
        "CoursewareVersion",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="CoursewareVersion.version_number",
    )
    presentation_profiles = relationship(
        "PresentationProfile",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    export_artifacts = relationship(
        "ExportArtifact",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "owner_user_id": self.owner_user_id,
            "title": self.title,
            "source_type": self.source_type,
            "source_plan_id": self.source_plan_id,
            "mode": self.mode,
            "template_id": self.template_id,
            "status": self.status,
            "source_meta": self.source_meta,
            "current_version_id": self.current_version_id,
            "presentation_profile_id": self.presentation_profile_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CoursewareVersion(Base):
    """课件版本快照"""
    __tablename__ = "courseware_versions"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(String(36), ForeignKey("courseware_projects.id"), nullable=False, index=True)
    version_number = Column(Integer, default=1, nullable=False)
    parent_version_id = Column(String(36), nullable=True, index=True)
    save_type = Column(String(30), default="manual_snapshot", nullable=False, index=True)
    editor_schema_json = Column(JSON, nullable=True)
    rendered_html = Column(Text, nullable=True)
    asset_manifest_json = Column(JSON, nullable=True)
    structure_sync_json = Column(JSON, nullable=True)
    change_summary = Column(String(500), nullable=True)
    created_by = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    project = relationship("CoursewareProject", back_populates="versions")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "version_number": self.version_number,
            "parent_version_id": self.parent_version_id,
            "save_type": self.save_type,
            "editor_schema_json": self.editor_schema_json,
            "rendered_html": self.rendered_html,
            "asset_manifest_json": self.asset_manifest_json,
            "structure_sync_json": self.structure_sync_json,
            "change_summary": self.change_summary,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PresentationProfile(Base):
    """课件展示配置"""
    __tablename__ = "presentation_profiles"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(String(36), ForeignKey("courseware_projects.id"), nullable=False, index=True)
    name = Column(String(100), default="默认展示配置", nullable=False)
    mode = Column(String(20), default="slides", nullable=False, index=True)
    settings_json = Column(JSON, nullable=True)
    is_default = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("CoursewareProject", back_populates="presentation_profiles")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "mode": self.mode,
            "settings_json": self.settings_json,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ExportArtifact(Base):
    """导出产物记录"""
    __tablename__ = "export_artifacts"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(String(36), ForeignKey("courseware_projects.id"), nullable=False, index=True)
    version_id = Column(String(36), nullable=True, index=True)
    format = Column(String(30), nullable=False, index=True)
    file_name = Column(String(255), nullable=True)
    storage_path = Column(String(500), nullable=True)
    source = Column(String(30), default="from_courseware", nullable=False)
    generated_by = Column(String(36), nullable=True, index=True)
    extra_data = Column(JSON, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)

    project = relationship("CoursewareProject", back_populates="export_artifacts")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "version_id": self.version_id,
            "format": self.format,
            "file_name": self.file_name,
            "storage_path": self.storage_path,
            "source": self.source,
            "generated_by": self.generated_by,
            "extra_data": self.extra_data,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }


class TeacherStyleEvent(Base):
    """教师风格档案（④b）：推荐 vs 选用/重新生成/导出事件，供风格规划阶段取历史偏好"""
    __tablename__ = "teacher_style_events"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    analysis_id = Column(String(36), ForeignKey("analysis_records.id"), nullable=True, index=True)
    event_type = Column(String(32), nullable=False, index=True)  # recommended | chosen | regenerated | exported | intent
    theme = Column(String(32), nullable=True)  # intent 事件无主题
    extra_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "analysis_id": self.analysis_id,
            "event_type": self.event_type,
            "theme": self.theme,
            "extra_json": self.extra_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ComponentDefinition(Base):
    """教学组件定义"""
    __tablename__ = "component_definitions"

    id = Column(String(36), primary_key=True, index=True)
    owner_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    scope = Column(String(20), default="personal", nullable=False, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, index=True)
    summary = Column(String(500), nullable=True)
    preview_cover = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    teaching_stage = Column(String(100), nullable=True, index=True)
    subject_tags = Column(JSON, nullable=True)
    interaction_level = Column(String(50), nullable=True, index=True)
    mode_support = Column(String(20), default="both", nullable=False, index=True)
    schema_json = Column(JSON, nullable=True)
    render_template_html = Column(Text, nullable=True)
    style_bundle = Column(JSON, nullable=True)
    asset_bundle = Column(JSON, nullable=True)
    version = Column(String(30), default="1.0.0", nullable=False)
    is_publishable = Column(Boolean, default=False, nullable=False)
    community_status = Column(String(30), default="draft", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="component_definitions")

    def to_dict(self):
        return {
            "id": self.id,
            "owner_user_id": self.owner_user_id,
            "scope": self.scope,
            "name": self.name,
            "slug": self.slug,
            "summary": self.summary,
            "preview_cover": self.preview_cover,
            "category": self.category,
            "teaching_stage": self.teaching_stage,
            "subject_tags": self.subject_tags,
            "interaction_level": self.interaction_level,
            "mode_support": self.mode_support,
            "schema_json": self.schema_json,
            "style_bundle": self.style_bundle,
            "asset_bundle": self.asset_bundle,
            "version": self.version,
            "is_publishable": self.is_publishable,
            "community_status": self.community_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
