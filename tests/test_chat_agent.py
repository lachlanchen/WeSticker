import json

import pytest

from server import chat_agent
from test_app import setup, signup, call, draft


def configure(app, tmp_path):
    token = tmp_path / 'agent-token'
    token.write_text('a' * 64)
    token.chmod(0o600)
    app.config['WESTICKER'].update(chat_provider='aginti', chat_agent_qualified=True,
        chat_agent_url='http://127.0.0.1:18646', chat_agent_token_file=str(token))


def test_agent_chat_is_authenticated_scoped_and_idempotent(setup, tmp_path, monkeypatch):
    app, _ = setup
    configure(app, tmp_path)
    seen = []
    def invoke(cfg, pack, rows, text, maximum, history, request_id):
        seen.append((pack['user_id'], maximum, history, request_id))
        return {'engine': 'aginti-deepseek', 'model': 'deepseek-flash', 'proposal': {
            'reply': 'A happy greeting', 'items': [{'id': None, 'label': 'Hello', 'action': 'Wave twice'}]}}
    monkeypatch.setattr(chat_agent, 'propose', invoke)
    c = app.test_client()
    signup(c)
    id, _ = draft(c)
    before = c.get('/api/workspace').json
    body = {'text': 'Suggest one greeting', 'attempt': 'agent-once-test-123456'}
    result = call(c, f'/api/packs/{id}/chat', body)
    assert result.status_code == 200
    assert result.json['result']['engine'] == 'aginti-deepseek'
    assert call(c, f'/api/packs/{id}/chat', body).json == result.json
    assert len(seen) == 1 and seen[0][1] == 1 and len(seen[0][3]) == 64
    assert c.get('/api/workspace').json['packs'] == before['packs']
    assert c.get('/api/workspace').json['jobs'] == []
    other = app.test_client()
    signup(other, 'outsider@example.com')
    assert call(other, f'/api/packs/{id}/chat', body).status_code == 404
    assert call(app.test_client(), f'/api/packs/{id}/chat', body).status_code == 401
    assert len(seen) == 1


def test_unqualified_agent_does_not_fallback_to_ambient_key(setup, tmp_path):
    app, _ = setup
    configure(app, tmp_path)
    app.config['WESTICKER'].update(chat_agent_qualified=False, chat_api_key='unused')
    c = app.test_client()
    signup(c)
    id, _ = draft(c)
    assert c.get('/api/bootstrap').json['capabilities']['chat'] is False
    assert call(c, f'/api/packs/{id}/chat', {'text': 'Hi', 'attempt': 'disabled-agent-123456'}).status_code == 502


def test_transport_uses_only_bounded_authorized_text(tmp_path, monkeypatch):
    token = tmp_path / 'agent-token'
    token.write_text('a' * 64)
    token.chmod(0o600)
    cfg = dict(chat_provider='aginti', chat_agent_qualified=True, chat_agent_url='http://agent:8001', chat_agent_token_file=str(token))
    request_id = 'b' * 64
    sent = []
    class Response:
        status_code = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, _):
            yield json.dumps({'id': request_id, 'engine': 'aginti-deepseek', 'proposal': {'reply': 'Hi', 'items': None}}).encode()
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kw):
            assert self.trust_env is False
            sent.append((url, kw))
            return Response()
    monkeypatch.setattr(chat_agent.requests, 'Session', Session)
    result = chat_agent.propose(cfg, {'title': 'Test', 'language': 'en'},
        [{'id': 'c'*32, 'label': 'Hi', 'action': 'Wave', 'asset': '/private.png', 'approved': True}],
        'hello', 1, [{'text': 'question', 'result': json.dumps({'reply': 'answer', 'items': [{'asset': '/private2.png'}]})}], request_id)
    assert result['engine'] == 'aginti-deepseek'
    assert sent[0][0] == 'http://agent:8001/propose'
    assert sent[0][1]['allow_redirects'] is False
    assert '/private' not in json.dumps(sent[0][1]['json'])
    with pytest.raises(ValueError):
        chat_agent.propose(cfg | {'chat_agent_url': 'http://untrusted.example'}, {}, [], 'hi', 1, [], request_id)
