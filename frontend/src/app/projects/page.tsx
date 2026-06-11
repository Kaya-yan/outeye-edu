"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";

interface Project {
  id: string;
  title: string;
  course_type: string;
  student_level: string;
  duration_minutes: number;
  analysis_status: string;
  status: string;
  created_at: string;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const response = await fetch("/api/v1/projects/");
      if (response.ok) {
        const data = await response.json();
        setProjects(data);
      } else {
        setError("加载项目列表失败");
      }
    } catch {
      setError("网络错误，请检查后端服务是否运行");
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800";
      case "processing":
        return "bg-yellow-100 text-yellow-800";
      case "pending":
        return "bg-gray-100 text-gray-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "completed":
        return "已完成";
      case "processing":
        return "分析中";
      case "pending":
        return "待分析";
      default:
        return status;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">项目管理</h1>
              <p className="text-gray-600 mt-1">管理您的课文分析项目</p>
            </div>
            <Link
              href="/analysis"
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
            >
              新建分析
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">加载中...</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-500 text-lg">暂无项目</p>
            <p className="text-gray-400 mt-2">
              点击"新建分析"开始您的第一个课文分析
            </p>
          </div>
        ) : (
          <div className="grid gap-6">
            {projects.map((project) => (
              <div
                key={project.id}
                className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">
                      {project.title}
                    </h2>
                    <div className="flex items-center space-x-4 mt-2 text-sm text-gray-600">
                      <span>课程类型: {project.course_type}</span>
                      <span>学生水平: {project.student_level}</span>
                      <span>时长: {project.duration_minutes}分钟</span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(
                        project.analysis_status
                      )}`}
                    >
                      {getStatusText(project.analysis_status)}
                    </span>
                  </div>
                </div>
                <div className="mt-4 text-sm text-gray-500">
                  创建时间: {new Date(project.created_at).toLocaleString("zh-CN")}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
