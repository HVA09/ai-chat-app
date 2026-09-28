import React from "react";

const paths = {
  plus: "M12 5v14M5 12h14",
  search: "m21 21-4.35-4.35m2.35-5.65a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z",
  menu: "M4 6h16M4 12h16M4 18h16",
  close: "M6 6l12 12M18 6 6 18",
  chevronDown: "m6 9 6 6 6-6",
  chevronRight: "m9 18 6-6-6-6",
  chat: "M7 18 3 21l1.5-5.5A8 8 0 1 1 20 13.5 8 8 0 0 1 12 21c-1.9 0-3.65-.66-5-1.75Z",
  archive: "M3 8h18M5 5h14v15H5zM9 12h6",
  trash: "M4 7h16M10 11v6M14 11v6M6 7l1 14h10l1-14M9 7V4h6v3",
  folder: "M3 7h7l2 2h9v10H3z",
  project: "M4 6h16v12H4zM8 10h8M8 14h5",
  tag: "m20 13-7 7-10-10V4h6zM7.5 8.5h.01",
  bookmark: "M6 4h12v16l-6-3-6 3z",
  robot: "M8 8h8a4 4 0 0 1 4 4v5H4v-5a4 4 0 0 1 4-4ZM12 4v4M9 13h.01M15 13h.01",
  settings: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-1.42 1.42-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.02 1.56V20h-2v-.08a1.7 1.7 0 0 0-1.02-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-1.42-1.42.06-.06A1.7 1.7 0 0 0 9.4 15a1.7 1.7 0 0 0-1.56-1.02H7v-2h.84A1.7 1.7 0 0 0 9.4 11a1.7 1.7 0 0 0-.34-1.88L9 9.06l1.42-1.42.06.06A1.7 1.7 0 0 0 12.36 8a1.7 1.7 0 0 0 1.02-1.56V6h2v.44A1.7 1.7 0 0 0 16.4 8a1.7 1.7 0 0 0 1.88-.34l.06-.06 1.42 1.42-.06.06A1.7 1.7 0 0 0 19.4 11c.25.61.84 1.02 1.5 1.02H21v2h-.1c-.66 0-1.25.4-1.5.98Z",
  more: "M6 12h.01M12 12h.01M18 12h.01",
  pin: "M8 4h8l-1 6 3 3v2h-6v5l-1 1-1-1v-5H4v-2l3-3z",
  edit: "M4 20h4l10-10-4-4L4 16zM13 5l2 2",
  copy: "M8 8h10v10H8zM6 6h10",
  link: "M10 13a5 5 0 0 1 0-7l1-1a5 5 0 0 1 7 7l-1 1M14 11a5 5 0 0 1 0 7l-1 1a5 5 0 0 1-7-7l1-1",
};

export default function Icon({ name, size = 18, strokeWidth = 1.8, className = "" }) {
  const d = paths[name] || paths.more;
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d={d} />
    </svg>
  );
}
