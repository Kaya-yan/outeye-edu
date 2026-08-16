"use client";

export interface Evidence {
  source_type: "wiki" | "rag";
  title: string;
  relevance: number;
  content: string;
}

export interface Blueprint {
  title: string;
  text_level: string;
  student_level: string;
  gap: string;
  gap_description: string;
  objectives: { activity: string; objective: string }[];
  stages: { stage: string; activities: string[] }[];
  time_budget: {
    total_minutes: number;
    activities: { name: string; minutes: number }[];
  };
  evaluation_points: string[];
  evidence_types: { theory: number; resource: number };
  theory_foundations: { title: string; relevance: number }[];
  activity_count: number;
}

export interface TeachingContext {
  courseType: string;
  durationMinutes: number;
  classSize: number;
  studentLevel: string;
  mode: "basic" | "enhanced";
}
