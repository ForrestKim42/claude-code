'use client';

import { useEffect, useState } from 'react';

interface ColInfo { column_name: string; data_type: string }
interface Session  { [key: string]: unknown }
interface ApiData  { columns: ColInfo[]; sessions: Session[] }

interface Message { role: string; content: string }

// 채팅 메시지가 담긴 컬럼 이름 후보들
const MSG_COL_CANDIDATES = ['messages', 'chat_messages', 'chat_data', 'conversation', 'session_data'];

function parseMessages(val: unknown): Message[] | null {
  if (!val) return null;
  try {
    const arr = typeof val === 'string' ? JSON.parse(val) : val;
    if (Array.isArray(arr) && arr.length && arr[0].role !== undefined) return arr as Message[];
    // session_data 같은 wrapper 구조: { messages: [...] }
    if (arr && typeof arr === 'object' && !Array.isArray(arr)) {
      const inner = (arr as Record<string, unknown>).messages ?? (arr as Record<string, unknown>).conversation;
      if (Array.isArray(inner)) return inner as Message[];
    }
  } catch { /* ignore */ }
  return null;
}

const ACCOUNTS: Record<string, string> = {
  'xeo.yuunny':    '서윤',
  'ha_n_a0.6':     '하나',
  'esther_ffff':   '에스더',
  'thinxoyoon':    '신소윤',
  'caiime_pretty': '지여닝',
};

function fmtKst(iso: string) {
  return new Date(iso).toLocaleString('ko-KR', {
    timeZone: 'Asia/Seoul',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

function ChatBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-1.5`}>
      <div className={`max-w-[75%] px-3 py-2 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
        isUser
          ? 'bg-blue-600 text-white rounded-br-sm'
          : 'bg-gray-700 text-gray-100 rounded-bl-sm'
      }`}>
        {msg.content}
      </div>
    </div>
  );
}

function SessionCard({
  session, msgCol, idx,
}: {
  session: Session; msgCol: string | null; idx: number
}) {
  const [open, setOpen] = useState(idx < 3); // 처음 3개는 펼침
  const referral = session.referral_code as string ?? '';
  const name = ACCOUNTS[referral] ?? referral;
  const createdAt = session.created_at as string ?? '';
  const messages = msgCol ? parseMessages(session[msgCol]) : null;
  const chatCount = session.chat_count as number ?? 0;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* 헤더 */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-800/50 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-white">{name}</span>
          <span className="text-xs text-gray-400">@{referral}</span>
          <span className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full">
            채팅 {chatCount}회
          </span>
          <span className="text-xs bg-emerald-900/60 text-emerald-400 px-2 py-0.5 rounded-full">
            전화 제출 ✓
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">{fmtKst(createdAt)}</span>
          <span className="text-gray-500 text-lg">{open ? '▲' : '▼'}</span>
        </div>
      </button>

      {/* 채팅 내용 */}
      {open && (
        <div className="border-t border-gray-800 px-4 py-4">
          {messages && messages.length > 0 ? (
            <div className="space-y-0">
              {messages.map((m, i) => <ChatBubble key={i} msg={m} />)}
            </div>
          ) : (
            // 메시지 컬럼 없거나 파싱 실패 → 가용 컬럼 표시
            <div className="text-xs text-gray-400 space-y-1">
              {Object.entries(session).map(([k, v]) => (
                <div key={k} className="flex gap-2">
                  <span className="text-gray-500 w-40 shrink-0">{k}</span>
                  <span className="text-gray-300 break-all">
                    {v == null ? '—' : typeof v === 'object' ? JSON.stringify(v) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function LeadsPage() {
  const [data, setData] = useState<ApiData | null>(null);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetch('/api/leads')
      .then(r => r.json())
      .then(setData)
      .catch(e => setError(String(e)));
  }, []);

  if (error) return (
    <div className="min-h-screen bg-gray-950 text-red-400 p-8">{error}</div>
  );
  if (!data) return (
    <div className="min-h-screen bg-gray-950 text-gray-400 p-8">불러오는 중...</div>
  );

  // 채팅 메시지 컬럼 자동 감지
  const colNames = data.columns.map(c => c.column_name);
  const msgCol = MSG_COL_CANDIDATES.find(c => colNames.includes(c)) ?? null;

  const codes = Object.keys(ACCOUNTS);
  const filtered = filter === 'all'
    ? data.sessions
    : data.sessions.filter(s => s.referral_code === filter);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="max-w-3xl mx-auto px-4 py-8">
        {/* 헤더 */}
        <div className="mb-6">
          <a href="/" className="text-sm text-gray-500 hover:text-gray-300 mb-3 inline-block">← 대시보드</a>
          <h1 className="text-2xl font-bold text-white">전화 제출 채팅 전체</h1>
          <p className="text-sm text-gray-400 mt-1">
            전화번호 입력까지 완료된 세션 {data.sessions.length}건
          </p>
        </div>

        {/* 필터 */}
        <div className="flex flex-wrap gap-2 mb-6">
          {['all', ...codes].map(code => (
            <button
              key={code}
              onClick={() => setFilter(code)}
              className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                filter === code
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {code === 'all' ? `전체 (${data.sessions.length})` : `${ACCOUNTS[code]} (${
                data.sessions.filter(s => s.referral_code === code).length
              })`}
            </button>
          ))}
        </div>

        {/* 메시지 컬럼 없을 때 안내 */}
        {!msgCol && (
          <div className="mb-4 px-4 py-3 bg-yellow-900/30 border border-yellow-700/50 rounded-lg text-sm text-yellow-400">
            채팅 메시지 컬럼을 찾지 못했습니다 (감지 대상: {MSG_COL_CANDIDATES.join(', ')}).
            아래는 세션 원본 데이터입니다.
          </div>
        )}

        {/* 세션 목록 */}
        <div className="space-y-3">
          {filtered.length === 0 && (
            <div className="text-center py-12 text-gray-500">해당 계정의 전화 제출 세션이 없습니다</div>
          )}
          {filtered.map((s, i) => (
            <SessionCard key={String(s.id ?? i)} session={s} msgCol={msgCol} idx={i} />
          ))}
        </div>
      </div>
    </div>
  );
}
