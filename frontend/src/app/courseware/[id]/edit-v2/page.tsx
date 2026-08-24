"use client";

import { useParams } from "next/navigation";
import V2Editor from "@/components/v2editor/V2Editor";

export default function CoursewareEditV2Page() {
  const params = useParams();
  const projectId = params?.id as string;
  if (!projectId) return null;
  return <V2Editor projectId={projectId} />;
}
