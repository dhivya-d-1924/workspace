import { useRef } from 'react';

export default function CodeEditor({ value, onChange, readOnly }) {
  const lineCount = Math.max(1, (value.match(/\n/g) || []).length + 1);
  const gutterRef = useRef(null);
  const textareaRef = useRef(null);

  const syncScroll = () => {
    if (gutterRef.current && textareaRef.current) {
      gutterRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  return (
    <div className="editor-body">
      <div className="editor-gutter" ref={gutterRef}>
        {Array.from({ length: lineCount }, (_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>
      <textarea
        ref={textareaRef}
        className="editor-textarea"
        spellCheck={false}
        value={value}
        readOnly={readOnly}
        onScroll={syncScroll}
        onChange={(e) => onChange(e.target.value)}
        placeholder="// Select or create a file to start editing"
      />
    </div>
  );
}
