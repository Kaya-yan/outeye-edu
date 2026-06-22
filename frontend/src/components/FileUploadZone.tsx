"use client";

import { useState, useRef, useCallback } from "react";
import { apiUpload } from "@/lib/api";
import PageRangeSelector from "./PageRangeSelector";
import OCRPreview from "./OCRPreview";

interface FileInfo {
  text: string;
  filename: string;
  total_pages: number;
  file_type: string;
  word_count: number;
}

interface OCRResult {
  text: string;
  confidence: number;
  engine: string;
}

interface FileUploadZoneProps {
  onTextExtracted: (text: string) => void;
  onFilename?: (filename: string) => void;
}

const FILE_ACCEPT = ".pdf,.docx,.txt,.md";
const IMAGE_ACCEPT = "image/jpeg,image/png,image/webp";

export default function FileUploadZone({ onTextExtracted, onFilename }: FileUploadZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // 文件解析状态
  const [fileInfo, setFileInfo] = useState<FileInfo | null>(null);
  const [showPageSelector, setShowPageSelector] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  // OCR 状态
  const [ocrResult, setOcrResult] = useState<OCRResult | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [pendingImages, setPendingImages] = useState<File[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  const isImage = (name: string) => /\.(jpg|jpeg|png|webp)$/i.test(name);
  const isPDF = (name: string) => /\.pdf$/i.test(name);

  // 处理文件选择
  const handleFiles = useCallback(async (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    if (fileArray.length === 0) return;

    setError("");
    const file = fileArray[0];

    if (isImage(file.name)) {
      // 图片走 OCR
      await handleImageOCR(fileArray);
    } else {
      // 文档走解析
      await handleFileParse(file);
    }
  }, []);

  // 解析文档文件
  const handleFileParse = async (file: File, pageFrom?: number, pageTo?: number) => {
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (pageFrom) formData.append("page_from", String(pageFrom));
      if (pageTo) formData.append("page_to", String(pageTo));

      const result = await apiUpload<FileInfo>("/analysis/parse-file", formData);
      setFileInfo(result);
      setPendingFile(file);

      if (isPDF(file.name) && result.total_pages > 1 && !pageFrom) {
        // 多页 PDF 且未指定范围，显示页码选择器
        setShowPageSelector(true);
      } else {
        // 单页、非 PDF、或已指定范围，直接填入
        onTextExtracted(result.text);
        if (onFilename) onFilename(result.filename);
        setShowPageSelector(false);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "文件解析失败");
    } finally {
      setLoading(false);
    }
  };

  // PDF 页码确认
  const handlePageConfirm = async (pageFrom: number, pageTo: number) => {
    if (!pendingFile) return;
    // 重新请求，带页码范围
    await handleFileParse(pendingFile, pageFrom, pageTo);
  };

  // OCR 识别图片
  const handleImageOCR = async (files: File[], engine: "aliyun" | "llm" = "aliyun") => {
    setOcrLoading(true);
    setError("");
    setPendingImages(Array.from(files));

    try {
      const allTexts: string[] = [];
      let lastResult: OCRResult = { text: "", confidence: 0, engine };

      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("engine", engine);

        const result = await apiUpload<OCRResult>("/analysis/ocr-image", formData);
        allTexts.push(result.text);
        lastResult = result;
      }

      const combinedText = allTexts.join("\n\n");
      setOcrResult({
        text: combinedText,
        confidence: lastResult.confidence,
        engine: lastResult.engine,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "OCR 识别失败");
    } finally {
      setOcrLoading(false);
    }
  };

  // OCR 确认使用
  const handleOCRConfirm = (text: string) => {
    onTextExtracted(text);
    setOcrResult(null);
    setPendingImages([]);
  };

  // OCR 重新识别
  const handleOCRRetry = (engine: "aliyun" | "llm") => {
    if (pendingImages.length > 0) {
      handleImageOCR(pendingImages, engine);
    }
  };

  // 拖拽处理
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  }, [handleFiles]);

  // 清除状态
  const handleClear = () => {
    setFileInfo(null);
    setShowPageSelector(false);
    setOcrResult(null);
    setPendingImages([]);
    setPendingFile(null);
    setError("");
  };

  return (
    <div className="space-y-3">
      {/* 拖拽上传区域 */}
      {!fileInfo && !ocrResult && (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
            dragOver
              ? "border-primary bg-primary/5"
              : "border-gray-300 hover:border-primary/50 hover:bg-gray-50"
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="text-3xl mb-2">📎</div>
          <p className="text-sm font-medium text-gray-700">
            {loading ? "解析中..." : "拖拽文件到此处或点击上传"}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            支持 PDF / DOCX / TXT / MD 文件，或拍照上传（JPG / PNG / WebP）
          </p>

          {/* 拍照按钮 */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              imageInputRef.current?.click();
            }}
            className="mt-3 px-4 py-1.5 text-xs font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            📷 上传照片
          </button>
        </div>
      )}

      {/* 隐藏的文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        accept={FILE_ACCEPT}
        className="hidden"
        onChange={(e) => e.target.files && handleFiles(e.target.files)}
      />
      <input
        ref={imageInputRef}
        type="file"
        accept={IMAGE_ACCEPT}
        multiple
        className="hidden"
        onChange={(e) => e.target.files && handleFiles(e.target.files)}
      />

      {/* 错误提示 */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError("")} className="text-red-500 hover:text-red-700">✕</button>
        </div>
      )}

      {/* PDF 页码选择器 */}
      {showPageSelector && fileInfo && (
        <PageRangeSelector
          filename={fileInfo.filename}
          totalPages={fileInfo.total_pages}
          onConfirm={handlePageConfirm}
          loading={loading}
        />
      )}

      {/* OCR 结果预览 */}
      {ocrResult && (
        <OCRPreview
          text={ocrResult.text}
          confidence={ocrResult.confidence}
          engine={ocrResult.engine}
          onConfirm={handleOCRConfirm}
          onRetry={handleOCRRetry}
          loading={ocrLoading}
        />
      )}

      {/* 已解析的文件信息 */}
      {fileInfo && !showPageSelector && !ocrResult && (
        <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
          <span className="text-sm text-green-700">✅</span>
          <span className="text-sm text-green-700 font-medium">{fileInfo.filename}</span>
          <span className="text-xs text-green-600">
            {fileInfo.total_pages > 0 ? `${fileInfo.total_pages} 页 · ` : ""}{fileInfo.word_count} 词
          </span>
          <button
            onClick={handleClear}
            className="ml-auto text-xs text-green-600 hover:text-green-800"
          >
            重新上传
          </button>
        </div>
      )}
    </div>
  );
}
