'use client';

import React from 'react';

interface CodeViewerProps {
  code: string;
  language: 'python' | 'agent' | 'curl' | 'opencypher';
}

function highlightPython(line: string) {
  // Check for full line comments
  if (line.trim().startsWith('#')) {
    return <span className="text-slate-500 italic font-mono">{line}</span>;
  }

  // Handle inline comments
  let inlineComment = '';
  let mainLine = line;
  const hashIdx = line.indexOf('#');
  if (hashIdx !== -1 && !line.slice(0, hashIdx).includes('"')) {
    inlineComment = line.slice(hashIdx);
    mainLine = line.slice(0, hashIdx);
  }

  // Tokens regex for python
  const parts: React.ReactNode[] = [];
  const regex = /(@\w+)|(["'].*?["'])|(\b(?:from|import|def|return|if|else|elif|print|as)\b)|(\b(?:MemoryGraph|tool|str|int|float|bool|dict|list)\b)|(\b(?:user_id|messages|api_url|query|role|content|answer|confidence|abstained)\b=)|(\b\d+(?:\.\d+)?\b)|([a-zA-Z_]\w*(?=\()|\w+|[^\s\w]+|\s+)/g;

  let match;
  let lastIndex = 0;

  while ((match = regex.exec(mainLine)) !== null) {
    const [full, decorator, stringLiteral, keyword, typeOrClass, paramAssign, numberLit, other] = match;

    if (decorator) {
      parts.push(<span key={match.index} className="text-amber-400 font-bold">{decorator}</span>);
    } else if (stringLiteral) {
      parts.push(<span key={match.index} className="text-emerald-400 font-medium">{stringLiteral}</span>);
    } else if (keyword) {
      parts.push(<span key={match.index} className="text-purple-400 font-bold">{keyword}</span>);
    } else if (typeOrClass) {
      parts.push(<span key={match.index} className="text-sky-400 font-bold">{typeOrClass}</span>);
    } else if (paramAssign) {
      parts.push(<span key={match.index} className="text-cyan-300 font-semibold">{paramAssign}</span>);
    } else if (numberLit) {
      parts.push(<span key={match.index} className="text-amber-300 font-bold">{numberLit}</span>);
    } else if (other) {
      if (['query', 'add_session', 'recall_user_memory'].includes(other)) {
        parts.push(<span key={match.index} className="text-sky-300 font-semibold">{other}</span>);
      } else if (['res', 'memory', 'result'].includes(other)) {
        parts.push(<span key={match.index} className="text-indigo-200">{other}</span>);
      } else if (['(', ')', '{', '}', '[', ']', ':', ',', '.'].includes(other)) {
        parts.push(<span key={match.index} className="text-slate-400">{other}</span>);
      } else {
        parts.push(<span key={match.index} className="text-slate-200">{other}</span>);
      }
    }
  }

  return (
    <>
      {parts}
      {inlineComment && <span className="text-slate-500 italic font-mono">{inlineComment}</span>}
    </>
  );
}

function highlightCurl(line: string) {
  const parts: React.ReactNode[] = [];
  const regex = /(curl|-X|-H|-d|\bPOST\b)|(["'].*?["'])|(\bhttps?:\/\/[^\s\\]+|\b[a-zA-Z_]\w*\b|[^\s\w]+|\s+)/g;

  let match;
  while ((match = regex.exec(line)) !== null) {
    const [full, keyword, stringLiteral, other] = match;

    if (keyword) {
      parts.push(<span key={match.index} className="text-pink-400 font-bold">{keyword}</span>);
    } else if (stringLiteral) {
      parts.push(<span key={match.index} className="text-emerald-400 font-medium">{stringLiteral}</span>);
    } else if (other?.startsWith('http')) {
      parts.push(<span key={match.index} className="text-cyan-300 underline underline-offset-2">{other}</span>);
    } else if (other === '\\') {
      parts.push(<span key={match.index} className="text-slate-500">{other}</span>);
    } else {
      parts.push(<span key={match.index} className="text-slate-200">{other}</span>);
    }
  }

  return <>{parts}</>;
}

function highlightOpenCypher(line: string) {
  if (line.trim().startsWith('//')) {
    return <span className="text-slate-500 italic font-mono">{line}</span>;
  }

  const parts: React.ReactNode[] = [];
  const regex = /(\b(?:MATCH|WHERE|RETURN|AND|OR|NOT|AS|ORDER\s+BY|DESC|ASC|true|false)\b)|(["'].*?["'])|(:[A-Z]\w+)|(\b[a-zA-Z_]\w*\b|[^\s\w]+|\s+)/g;

  let match;
  while ((match = regex.exec(line)) !== null) {
    const [full, keyword, stringLiteral, labelType, other] = match;

    if (keyword) {
      parts.push(<span key={match.index} className="text-purple-400 font-bold">{keyword}</span>);
    } else if (stringLiteral) {
      parts.push(<span key={match.index} className="text-emerald-400 font-medium">{stringLiteral}</span>);
    } else if (labelType) {
      parts.push(<span key={match.index} className="text-sky-400 font-bold">{labelType}</span>);
    } else if (['SUPERSEDES', 'INVALIDATED_BY', 'MENTIONS'].includes(other)) {
      parts.push(<span key={match.index} className="text-amber-400 font-bold">{other}</span>);
    } else if (['active_fact', 'score', 'timestamp', 'name', 'is_current', 'confidence', 'created_at'].includes(other)) {
      parts.push(<span key={match.index} className="text-cyan-300 font-semibold">{other}</span>);
    } else {
      parts.push(<span key={match.index} className="text-slate-200">{other}</span>);
    }
  }

  return <>{parts}</>;
}

export function CodeViewer({ code, language }: CodeViewerProps) {
  const lines = code.trim().split('\n');

  return (
    <div className="flex font-mono text-xs sm:text-[13px] leading-relaxed select-text">
      {/* Line Numbers */}
      <div className="py-5 pl-4 pr-3 text-right text-slate-600 select-none border-r border-slate-800/80 bg-[#070b14]/50 flex flex-col font-mono text-[11px]">
        {lines.map((_, i) => (
          <span key={i} className="leading-relaxed">
            {String(i + 1).padStart(2, '0')}
          </span>
        ))}
      </div>

      {/* Formatted Code Lines */}
      <div className="p-5 overflow-x-auto flex-1 bg-[#090d18]">
        {lines.map((line, i) => (
          <div key={i} className="whitespace-pre">
            {language === 'curl'
              ? highlightCurl(line)
              : language === 'opencypher'
              ? highlightOpenCypher(line)
              : highlightPython(line)}
          </div>
        ))}
      </div>
    </div>
  );
}
