// components/UploadArea.tsx
"use client";
import { useEffect, useRef, useState } from "react";
import "@/styles/UploadArea.css";
import StatusText from "@/components/StatusText";

interface UploadAreaProps {
  apiUrl: string;
}

export default function UploadArea({ apiUrl }: UploadAreaProps) {
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState("");
  const [status, setStatus] = useState("No file selected");
  const [apiStatus, setApiStatus] = useState("Checking backend...");
  const [isDragging, setIsDragging] = useState(false);
  const [category, setCategory] = useState("general");
  const [description, setDescription] = useState("");
  const [askPrice, setAskPrice] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const descriptionLimit = 500;

  useEffect(() => {
    let cancelled = false;
    async function checkBackend() {
      try {
        const res = await fetch(`${apiUrl}/metadata`);
        if (!cancelled) {
          setApiStatus(res.ok ? "Backend reachable" : `Backend error (${res.status})`);
        }
      } catch {
        if (!cancelled) {
          setApiStatus("Backend unreachable");
        }
      }
    }
    checkBackend();
    return () => {
      cancelled = true;
    };
  }, [apiUrl]);

  const formatFileSize = (size: number) => {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`;
    return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (file) {
      setStatus("Remove the current file to choose another.");
      return;
    }
    if (e.target.files?.length) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setFileName(selectedFile.name);
      setStatus("Ready to upload");
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (file) return;
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (file) {
      setStatus("Remove the current file to choose another.");
      return;
    }
    if (e.dataTransfer.files?.length) {
      const droppedFile = e.dataTransfer.files[0];
      setFile(droppedFile);
      setFileName(droppedFile.name);
      setStatus("Ready to upload");
    }
  };

  const handleRemoveFile = () => {
    setFile(null);
    setFileName("");
    setStatus("No file selected");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setStatus("Please select or drop a file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("category", category);
    const trimmedDescription = description.trim();
    if (trimmedDescription.length > 0) {
      formData.append("description", trimmedDescription);
    }
    const trimmedAskPrice = askPrice.trim();
    if (trimmedAskPrice.length > 0) {
      const parsedAskPrice = Number(trimmedAskPrice);
      if (Number.isNaN(parsedAskPrice) || parsedAskPrice < 0) {
        setStatus("Ask price must be a valid number greater than or equal to 0.");
        return;
      }
      formData.append("ask_price_usd", parsedAskPrice.toFixed(2));
    }

    // Attach user_id from localStorage (if logged in)
    let userId: string | null = null;
    if (typeof window !== "undefined") {
      const raw =
        localStorage.getItem("shannova_user") ||
        localStorage.getItem("shanova_user");
      if (raw) {
        try {
          const user = JSON.parse(raw) as { id: string };
          userId = user.id;
        } catch {
          // ignore bad data
        }
      }
    }
    if (userId) {
      formData.append("user_id", userId);
    }

    setStatus("Uploading...");

    try {
      const response = await fetch(`${apiUrl}/upload`, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        setStatus("Upload complete!");
      } else {
        const detail = await response.json().catch(async () => {
          const text = await response.text().catch(() => "");
          return text ? { detail: text } : {};
        });
        const message =
          detail?.detail ||
          `Upload failed (status ${response.status}).`;
        setStatus(message);
      }
    } catch {
      setStatus("Upload failed - could not reach the server.");
    }
  };

  return (
    <div className="upload-container">
      <h1>List Your Dataset</h1>

      <div className="category-wrapper">
        <label className="category-label">Select Data Category</label>
        <select
          className="category-select"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="medical">Medical</option>
          <option value="finance">Finance</option>
          <option value="retail">Retail</option>
          <option value="text">Text / NLP</option>
          <option value="images">Images</option>
          <option value="geospatial">Geospatial</option>
          <option value="general">General</option>
        </select>
      </div>

      <div className="description-wrapper">
        <label className="description-label" htmlFor="dataset-description">
          Description (optional)
        </label>
        <textarea
          id="dataset-description"
          className="description-input"
          placeholder="Short summary of the dataset, contents, and usage notes."
          value={description}
          maxLength={descriptionLimit}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
        />
        <div className="description-counter">
          {description.length}/{descriptionLimit}
        </div>
      </div>

      <div className="price-wrapper">
        <label className="description-label" htmlFor="dataset-ask-price">
          Ask price in USD (optional)
        </label>
        <div className="price-input-row">
          <span className="price-prefix">$</span>
          <input
            id="dataset-ask-price"
            className="price-input"
            type="number"
            min="0"
            step="0.01"
            placeholder="49.00"
            value={askPrice}
            onChange={(e) => setAskPrice(e.target.value)}
          />
        </div>
      </div>

      {!file ? (
        <div
          className={`upload-area ${isDragging ? "dragover" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <p>Drag and drop your file here</p>
          <p className="or-text">or</p>
          <label className="upload-label">
            Choose file
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileChange}
              hidden
            />
          </label>
          <p className="upload-helper">Only one file can be selected.</p>
        </div>
      ) : (
        <div className="selected-file">
          <div className="selected-file-info">
            <span className="selected-file-name">{fileName}</span>
            <span className="selected-file-size">{formatFileSize(file.size)}</span>
          </div>
          <button
            type="button"
            className="selected-file-remove"
            onClick={handleRemoveFile}
          >
            Remove
          </button>
        </div>
      )}

      <button onClick={handleUpload}>List dataset</button>
      <p className="status-text">{apiStatus}</p>
      <StatusText status={status} />
    </div>
  );
}
