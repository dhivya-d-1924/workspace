import { useState } from 'react';
import { aiApi } from '../api/endpoints';
import { extractErrorMessage } from '../api/client';
import { SeverityBadge } from './Widgets.jsx';
import QualityGauge from './QualityGauge.jsx';

const FILE_FEATURES = [
  { key: 'explain', label: 'Explain code', call: aiApi.explain },
  { key: 'findBugs', label: 'Find bugs', call: aiApi.findBugs },
  { key: 'fixBugs', label: 'Fix bugs', call: aiApi.fixBugs },
  { key: 'optimize', label: 'Optimize', call: aiApi.optimize },
  { key: 'generateComments', label: 'Add comments', call: aiApi.generateComments },
  { key: 'generateDocs', label: 'Generate docs', call: aiApi.generateDocs },
  { key: 'generateTests', label: 'Generate tests', call: aiApi.generateTests },
  { key: 'securityScan', label: 'Security scan', call: aiApi.securityScan },
  { key: 'qualityScore', label: 'Quality score', call: aiApi.qualityScore },
  { key: 'complexity', label: 'Complexity', call: aiApi.complexity },
  { key: 'codeReview', label: 'Full AI review', call: aiApi.codeReview },
];

export default function AIPanel({ code, language, projectId, fileId, onApplyFix }) {
  const [mode, setMode] = useState('analyze'); // 'analyze' | 'tools'
  const [activeFeature, setActiveFeature] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const runFeature = async (feature) => {
    if (!code.trim()) {
      setError('Add some code to the editor first.');
      return;
    }
    setActiveFeature(feature.key);
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await feature.call({ code, language, project_id: projectId, file_id: fileId });
      setResult({ feature: feature.key, ...res.data });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-panel-col">
      <div className="file-tree-header">
        <span className="text-sm" style={{ fontWeight: 700 }}>AI Assistant</span>
        <div className="flex gap-8">
          <button className={`btn btn-sm ${mode === 'analyze' ? 'btn-primary' : ''}`} onClick={() => setMode('analyze')}>Analyze</button>
          <button className={`btn btn-sm ${mode === 'tools' ? 'btn-primary' : ''}`} onClick={() => setMode('tools')}>Tools</button>
        </div>
      </div>

      {mode === 'analyze' ? (
        <>
          <div className="ai-feature-grid">
            {FILE_FEATURES.map((f) => (
              <button
                key={f.key}
                className={`ai-feature-btn ${activeFeature === f.key ? 'active' : ''}`}
                onClick={() => runFeature(f)}
                disabled={loading}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="ai-result-panel">
            {loading && <div className="spinner" />}
            {error && <div className="alert alert-error">{error}</div>}
            {!loading && result && <FeatureResult result={result} onApplyFix={onApplyFix} />}
            {!loading && !result && !error && (
              <p className="text-muted text-sm">
                Choose a feature above to analyze the current file. Results include real static-analysis
                findings (bug patterns, complexity, security heuristics) — optionally enriched with an LLM
                narrative if an API key is configured server-side.
              </p>
            )}
          </div>
        </>
      ) : (
        <ToolsPanel language={language} />
      )}
    </div>
  );
}

function FeatureResult({ result, onApplyFix }) {
  const r = result.result || {};

  if (result.feature === 'explain') {
    return (
      <div>
        <p>{r.summary}</p>
        {r.details?.length > 0 && (
          <ul style={{ paddingLeft: 18 }}>
            {r.details.map((d, i) => <li key={i} className="text-muted text-sm mb-8">{d}</li>)}
          </ul>
        )}
        {r.ai_narrative && <AINarrative text={r.ai_narrative} />}
      </div>
    );
  }

  if (result.feature === 'findBugs' || result.feature === 'securityScan') {
    const items = r.bugs || r.issues || [];
    return (
      <div>
        <p className="text-muted text-sm mb-8">{items.length} finding(s)</p>
        {items.map((b, i) => (
          <div key={i} className="bug-item">
            <div className="flex items-center gap-8 mb-8">
              <SeverityBadge severity={b.severity} />
              {b.line != null && <span className="bug-line">line {b.line}</span>}
            </div>
            <div className="text-sm">{b.message}</div>
            {b.snippet && <pre className="mono">{b.snippet}</pre>}
          </div>
        ))}
        {r.ai_narrative && <AINarrative text={r.ai_narrative} />}
      </div>
    );
  }

  if (result.feature === 'fixBugs') {
    return (
      <div>
        <ul style={{ paddingLeft: 18 }}>
          {r.changes?.map((c, i) => <li key={i} className="text-muted text-sm mb-8">{c}</li>)}
        </ul>
        <p className="text-sm">Bugs before: {r.bugs_before} → after: {r.bugs_after}</p>
        <pre>{r.fixed_code}</pre>
        {onApplyFix && <button className="btn btn-primary btn-sm mt-8" onClick={() => onApplyFix(r.fixed_code)}>Apply to editor</button>}
      </div>
    );
  }

  if (result.feature === 'optimize') {
    return (
      <div>
        {r.suggestions?.map((s, i) => (
          <div key={i} className="bug-item">
            <div className="text-sm" style={{ fontWeight: 600 }}>{s.type}</div>
            <div className="text-muted text-sm">{s.message}</div>
          </div>
        ))}
        {r.ai_narrative && <AINarrative text={r.ai_narrative} />}
      </div>
    );
  }

  if (['generateComments'].includes(result.feature)) {
    return <pre>{r.commented_code}</pre>;
  }
  if (result.feature === 'generateDocs') {
    return <pre style={{ whiteSpace: 'pre-wrap' }}>{r.markdown}</pre>;
  }
  if (result.feature === 'generateTests') {
    return <pre>{r.tests}</pre>;
  }

  if (result.feature === 'qualityScore') {
    return (
      <div>
        <QualityGauge score={r.score} label={`Grade ${r.grade}`} />
        <div className="grid grid-cols-2 gap-8 mt-16">
          {Object.entries(r.breakdown || {}).map(([k, v]) => (
            <div key={k} className="text-sm text-muted">{k.replace(/_/g, ' ')}: <strong style={{ color: 'var(--text)' }}>{v}</strong></div>
          ))}
        </div>
        <ul style={{ paddingLeft: 18, marginTop: 12 }}>
          {r.notes?.map((n, i) => <li key={i} className="text-muted text-sm mb-8">{n}</li>)}
        </ul>
      </div>
    );
  }

  if (result.feature === 'complexity') {
    return (
      <div>
        <p className="text-sm mb-8">Average complexity: <strong>{r.average_complexity}</strong> · Max: <strong>{r.max_complexity}</strong></p>
        {r.functions?.map((f, i) => (
          <div key={i} className="flex items-center justify-between text-sm mb-8">
            <span className="mono">{f.name}()</span>
            <span className={`badge badge-${f.rating === 'simple' ? 'success' : f.rating === 'moderate' ? 'medium' : 'high'}`}>
              {f.complexity} · {f.rating}
            </span>
          </div>
        ))}
      </div>
    );
  }

  if (result.feature === 'codeReview') {
    return (
      <div>
        <QualityGauge score={r.quality_score} label={`Grade ${r.grade}`} />
        <p className="text-sm mt-16">{r.explanation}</p>
        <div className="grid grid-cols-2 gap-8 mt-16 text-sm">
          <div>Bugs found: <strong>{r.bugs?.length || 0}</strong></div>
          <div>Security issues: <strong>{r.security_issues?.length || 0}</strong></div>
        </div>
        {r.ai_narrative && <AINarrative text={r.ai_narrative} />}
        {r.summary?.length > 0 && (
          <ul style={{ paddingLeft: 18, marginTop: 12 }}>
            {r.summary.map((n, i) => <li key={i} className="text-muted text-sm mb-8">{n}</li>)}
          </ul>
        )}
      </div>
    );
  }

  return <pre>{JSON.stringify(r, null, 2)}</pre>;
}

function AINarrative({ text }) {
  return (
    <div className="alert alert-info mt-16" style={{ whiteSpace: 'pre-wrap' }}>
      <strong>AI narrative:</strong><br />{text}
    </div>
  );
}

function ToolsPanel({ language }) {
  const [tool, setTool] = useState('generate');
  return (
    <div className="ai-result-panel">
      <div className="flex gap-8 mb-16" style={{ flexWrap: 'wrap' }}>
        {[
          ['generate', 'Generate code'],
          ['convert', 'Convert language'],
          ['sql', 'Generate SQL'],
          ['error', 'Explain error'],
        ].map(([key, label]) => (
          <button key={key} className={`btn btn-sm ${tool === key ? 'btn-primary' : ''}`} onClick={() => setTool(key)}>{label}</button>
        ))}
      </div>
      {tool === 'generate' && <GenerateCodeTool defaultLanguage={language} />}
      {tool === 'convert' && <ConvertCodeTool defaultLanguage={language} />}
      {tool === 'sql' && <GenerateSqlTool />}
      {tool === 'error' && <ExplainErrorTool defaultLanguage={language} />}
    </div>
  );
}

function GenerateCodeTool({ defaultLanguage }) {
  const [prompt, setPrompt] = useState('');
  const [lang, setLang] = useState(defaultLanguage || 'python');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true); setError(''); setResult(null);
    try {
      const res = await aiApi.generateCode({ prompt, language: lang });
      setResult(res.data.result);
    } catch (err) { setError(extractErrorMessage(err)); } finally { setLoading(false); }
  };

  return (
    <form onSubmit={submit}>
      <div className="field">
        <label>Describe what to generate</label>
        <textarea className="textarea" required placeholder="e.g. a REST API endpoint for products" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
      </div>
      <div className="field">
        <label>Language</label>
        <select className="select" value={lang} onChange={(e) => setLang(e.target.value)}>
          <option value="python">python</option>
          <option value="javascript">javascript</option>
        </select>
      </div>
      <button className="btn btn-primary btn-sm" disabled={loading}>{loading ? 'Generating…' : 'Generate'}</button>
      {error && <div className="alert alert-error mt-16">{error}</div>}
      {result && <pre className="mt-16">{result.code}</pre>}
    </form>
  );
}

function ConvertCodeTool({ defaultLanguage }) {
  const [code, setCode] = useState('');
  const [source, setSource] = useState(defaultLanguage || 'python');
  const [target, setTarget] = useState(defaultLanguage === 'python' ? 'javascript' : 'python');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true); setError(''); setResult(null);
    try {
      const res = await aiApi.convert({ code, source_language: source, target_language: target });
      setResult(res.data.result);
    } catch (err) { setError(extractErrorMessage(err)); } finally { setLoading(false); }
  };

  return (
    <form onSubmit={submit}>
      <div className="field">
        <label>Code to convert</label>
        <textarea className="textarea" required value={code} onChange={(e) => setCode(e.target.value)} />
      </div>
      <div className="grid grid-cols-2 gap-8">
        <div className="field">
          <label>From</label>
          <select className="select" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="python">python</option>
            <option value="javascript">javascript</option>
          </select>
        </div>
        <div className="field">
          <label>To</label>
          <select className="select" value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="javascript">javascript</option>
            <option value="python">python</option>
          </select>
        </div>
      </div>
      <button className="btn btn-primary btn-sm" disabled={loading}>{loading ? 'Converting…' : 'Convert'}</button>
      {error && <div className="alert alert-error mt-16">{error}</div>}
      {result && <><p className="text-muted text-sm mt-16">{result.note}</p><pre>{result.converted_code}</pre></>}
    </form>
  );
}

function GenerateSqlTool() {
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true); setError(''); setResult(null);
    try {
      const res = await aiApi.generateSql({ prompt });
      setResult(res.data.result);
    } catch (err) { setError(extractErrorMessage(err)); } finally { setLoading(false); }
  };

  return (
    <form onSubmit={submit}>
      <div className="field">
        <label>Describe the query</label>
        <textarea className="textarea" required placeholder="e.g. get the top 10 orders sorted by total desc" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
      </div>
      <button className="btn btn-primary btn-sm" disabled={loading}>{loading ? 'Generating…' : 'Generate SQL'}</button>
      {error && <div className="alert alert-error mt-16">{error}</div>}
      {result && <pre className="mt-16">{result.sql}</pre>}
    </form>
  );
}

function ExplainErrorTool({ defaultLanguage }) {
  const [errorMessage, setErrorMessage] = useState('');
  const [lang, setLang] = useState(defaultLanguage || 'python');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true); setError(''); setResult(null);
    try {
      const res = await aiApi.explainError({ error_message: errorMessage, language: lang });
      setResult(res.data.result);
    } catch (err) { setError(extractErrorMessage(err)); } finally { setLoading(false); }
  };

  return (
    <form onSubmit={submit}>
      <div className="field">
        <label>Paste the error / traceback</label>
        <textarea className="textarea" required value={errorMessage} onChange={(e) => setErrorMessage(e.target.value)} />
      </div>
      <button className="btn btn-primary btn-sm" disabled={loading}>{loading ? 'Explaining…' : 'Explain error'}</button>
      {error && <div className="alert alert-error mt-16">{error}</div>}
      {result && (
        <div className="mt-16">
          <p>{result.explanation}</p>
          <ul style={{ paddingLeft: 18 }}>
            {result.suggested_fixes?.map((f, i) => <li key={i} className="text-muted text-sm mb-8">{f}</li>)}
          </ul>
        </div>
      )}
    </form>
  );
}
