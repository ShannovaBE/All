// app/upload/page.tsx
"use client";
import UploadArea from "@/components/UploadArea";

export default function UploadPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  return (
    <>
      <div>
        <UploadArea apiUrl={apiUrl} />
      </div>
    </>
  );
}
