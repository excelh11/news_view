import { useMemo, useState } from 'react';
import styled from 'styled-components';

const Wrap = styled.div`
  box-sizing: border-box;
  width: 768px;
  margin: 0 auto;
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  background: #fff;

  @media screen and (max-width: 768px) {
    width: 100%;
    padding-left: 1rem;
    padding-right: 1rem;
    border-left: 0;
    border-right: 0;
    border-radius: 0;
  }
`;

const Title = styled.div`
  font-weight: 700;
  font-size: 1.05rem;
  margin-bottom: 0.75rem;
`;

const Row = styled.div`
  display: flex;
  gap: 0.5rem;
  align-items: center;
`;

const Input = styled.input`
  flex: 1;
  padding: 0.75rem 0.9rem;
  border: 1px solid #dee2e6;
  border-radius: 10px;
  outline: none;
  font-size: 0.95rem;

  &:focus {
    border-color: #228be6;
    box-shadow: 0 0 0 3px rgba(34, 139, 230, 0.12);
  }
`;

const Button = styled.button`
  padding: 0.75rem 0.9rem;
  border: 0;
  border-radius: 10px;
  background: #228be6;
  color: white;
  font-weight: 700;
  cursor: pointer;

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

const Meta = styled.div`
  margin-top: 0.6rem;
  font-size: 0.85rem;
  color: #495057;
`;

const List = styled.ul`
  margin: 0.75rem 0 0;
  padding-left: 1.2rem;
`;

const Item = styled.li`
  margin: 0.45rem 0;
  line-height: 1.3;

  a {
    color: #1c7ed6;
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
`;

async function postJson(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return await res.json();
}

const ChatbotNewsSearch = () => {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [translated, setTranslated] = useState('');
  const [articles, setArticles] = useState([]);
  const [error, setError] = useState('');

  const canSubmit = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);

  const onSubmit = async () => {
    const message = input.trim();
    if (!message) return;
    setLoading(true);
    setError('');
    try {
      const data = await postJson('/api/chat-search', { message, max_results: 3 });
      setTranslated(data.translated_en || '');
      setArticles((data.articles || []).slice(0, 3));
    } catch (e) {
      setError(e?.message || '요청에 실패했습니다.');
      setTranslated('');
      setArticles([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Wrap>
      <Title>AI 뉴스 검색 (한글 → 번역 → 기사 찾기)</Title>
      <Row>
        <Input
          value={input}
          placeholder="예) 한국 반도체 수출 전망, AI 규제 동향, 애플 신제품 루머…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') onSubmit();
          }}
        />
        <Button onClick={onSubmit} disabled={!canSubmit}>
          {loading ? '검색중…' : '검색'}
        </Button>
      </Row>
      {error ? <Meta style={{ color: '#e03131' }}>{error}</Meta> : null}
      {translated ? <Meta>번역된 검색어: {translated}</Meta> : null}
      {articles?.length ? (
        <List>
          {articles.map((a) => (
            <Item key={a.url}>
              <a href={a.url} target="_blank" rel="noreferrer">
                {a.title}
              </a>{' '}
              <span style={{ color: '#868e96' }}>({a.source}{a.published_at ? `, ${a.published_at}` : ''})</span>
            </Item>
          ))}
        </List>
      ) : null}
    </Wrap>
  );
};

export default ChatbotNewsSearch;

