-- OutEye Edu 数据库初始化脚本

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 1. 用户与认证表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    avatar_url TEXT,
    institution VARCHAR(200),
    title VARCHAR(50),
    bio TEXT,
    preferences JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    is_admin BOOLEAN DEFAULT false,
    total_projects INTEGER DEFAULT 0,
    total_ai_generations INTEGER DEFAULT 0,
    time_saved_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);

-- 2. 项目管理表
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    course_type VARCHAR(50) NOT NULL,
    student_level VARCHAR(10) NOT NULL,
    duration_minutes INTEGER NOT NULL,
    source_text TEXT NOT NULL,
    source_type VARCHAR(20) DEFAULT 'text',
    analysis_result JSONB,
    analysis_status VARCHAR(20) DEFAULT 'pending',
    workflow JSONB,
    workflow_version INTEGER DEFAULT 1,
    template_id VARCHAR(50),
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[] DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'draft',
    is_deleted BOOLEAN DEFAULT false,
    is_shared BOOLEAN DEFAULT false,
    share_code VARCHAR(20) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_edited_at TIMESTAMP DEFAULT NOW()
);

-- 3. Workflow版本历史表
CREATE TABLE workflow_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    workflow_data JSONB NOT NULL,
    changed_by UUID REFERENCES users(id),
    change_description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, version)
);

-- 4. 协作者与分享表
CREATE TABLE project_collaborators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission VARCHAR(20) NOT NULL,
    invited_by UUID REFERENCES users(id),
    last_viewed_at TIMESTAMP,
    edit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, user_id)
);

-- 5. 评论与批注表
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    block_id VARCHAR(100),
    content TEXT NOT NULL,
    parent_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    is_resolved BOOLEAN DEFAULT false,
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 6. 资源库表
CREATE TABLE resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    content JSONB,
    category VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    source VARCHAR(200),
    author VARCHAR(200),
    author_title VARCHAR(100),
    quality_score DECIMAL(3,2) DEFAULT 0.00,
    verified BOOLEAN DEFAULT false,
    view_count INTEGER DEFAULT 0,
    use_count INTEGER DEFAULT 0,
    favorite_count INTEGER DEFAULT 0,
    visibility VARCHAR(20) DEFAULT 'public',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 7. RAG知识单元表
CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type VARCHAR(50),
    source_id UUID,
    content TEXT NOT NULL,
    content_type VARCHAR(50),
    vector_id VARCHAR(100) UNIQUE NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    quality_score DECIMAL(3,2) DEFAULT 0.00,
    verified BOOLEAN DEFAULT false,
    retrieval_count INTEGER DEFAULT 0,
    usefulness_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 8. Skill模板市场表
CREATE TABLE skill_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    prompt_chain JSONB NOT NULL,
    few_shot_corpus JSONB,
    theory_weights JSONB,
    output_format JSONB,
    category VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    author_id UUID REFERENCES users(id),
    download_count INTEGER DEFAULT 0,
    rating_avg DECIMAL(2,1) DEFAULT 0.0,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 9. 用户反馈与评分表
CREATE TABLE user_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    feedback_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(100) NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- 10. 系统日志与审计表
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    activity_type VARCHAR(50) NOT NULL,
    details JSONB,
    duration_ms INTEGER,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 11. 通知系统表
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    link VARCHAR(500),
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 12. 文件与对象存储索引表
CREATE TABLE file_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    project_id UUID REFERENCES projects(id),
    filename VARCHAR(255) NOT NULL,
    storage_key VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size BIGINT,
    mime_type VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_institution ON users(institution);
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_course_type ON projects(course_type);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX idx_projects_tags ON projects USING GIN(tags);
CREATE INDEX idx_projects_analysis_result ON projects USING GIN(analysis_result);
CREATE INDEX idx_knowledge_chunks_vector_id ON knowledge_chunks(vector_id);
CREATE INDEX idx_knowledge_chunks_source_type ON knowledge_chunks(source_type);
CREATE INDEX idx_resources_type ON resources(type);
CREATE INDEX idx_resources_category ON resources(category);
CREATE INDEX idx_resources_tags ON resources USING GIN(tags);
CREATE INDEX idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at DESC);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);

-- 插入默认管理员用户
INSERT INTO users (email, password_hash, full_name, is_admin, is_verified)
VALUES (
    'admin@outeye.edu',
    '$2b$12$LJ3m4ys3Lz0YBNOBRpCqOe2k3G3J3Z3Z3Z3Z3Z3Z3Z3Z3Z3Z3Z',  -- 默认密码: admin123
    '系统管理员',
    true,
    true
);

-- 插入示例资源
INSERT INTO resources (type, title, description, category, tags, author, quality_score, verified)
VALUES
    ('theory', 'Krashen输入假说', 'Krashen的i+1输入假说是二语习得理论的核心', '二语习得', ARRAY['krashen', 'i+1', 'acquisition'], 'Stephen Krashen', 0.95, true),
    ('theory', 'Bloom认知分类学', '认知层级从记忆到创造的六级分类', '教育心理学', ARRAY['bloom', 'taxonomy', 'cognition'], 'Benjamin Bloom', 0.95, true),
    ('theory', 'CEFR框架', '欧洲语言共同参考框架，A1-C2六级分类', '语言评估', ARRAY['cefr', 'assessment', 'levels'], 'Council of Europe', 0.95, true);