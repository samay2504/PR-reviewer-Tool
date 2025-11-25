import React from 'react';

export default function Spinner({ text = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2">
      <div className="spinner"></div>
      {text && <p className="text-muted">{text}</p>}
    </div>
  );
}
