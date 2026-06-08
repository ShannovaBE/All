// components/StatusText.tsx
"use client";

interface StatusTextProps {
  status: string;
}

export default function StatusText({ status }: StatusTextProps) {
  const getStatusClass = () => {
    if (status.includes("failed")) return "status-text error";
    if (status.includes("complete")) return "status-text success";
    if (status.includes("Uploading")) return "status-text loading";
    return "status-text";
  };

  return <p className={getStatusClass()}>{status}</p>;
}
