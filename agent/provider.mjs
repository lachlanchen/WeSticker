const ENDPOINT = 'https://api.deepseek.com/v1/chat/completions';

export async function boundedJSON(response, maxBytes = 65536) {
  const chunks = [];
  let total = 0;
  if (!response.body) throw new Error('PROVIDER_INVALID');
  for await (const chunk of response.body) {
    total += chunk.length;
    if (total > maxBytes) throw new Error('PROVIDER_INVALID');
    chunks.push(Buffer.from(chunk));
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

// DeepSeek explicitly supports JSON-object mode. AgInTi validates the resulting
// proposal against the closed schema; it is not claimed as provider JSON Schema.
export function deepseekProvider(config, transport = fetch) {
  if (!['deepseek-flash', 'deepseek-v4-flash', 'deepseek-v4-pro'].includes(config.model) ||
      typeof config.apiKey !== 'string' || config.apiKey.length < 20) throw new Error('CONFIG_INVALID');
  return {supportsImages: false, async complete(request, {signal}) {
    if (request.tools.length) throw new Error('TOOLS_DISABLED');
    const messages = request.messages.map(message => ({role: message.role,
      content: typeof message.content === 'string' ? message.content : message.content.map(part => {
        if (part.type !== 'text') throw new Error('TEXT_ONLY');
        return part.text;
      }).join('\n')}));
    const response = await transport(ENDPOINT, {method: 'POST', redirect: 'error', signal,
      headers: {'Authorization': `Bearer ${config.apiKey}`, 'Content-Type': 'application/json'},
      body: JSON.stringify({model: config.model, messages, stream: false,
        thinking: {type: 'disabled'}, max_tokens: request.maxOutputTokens,
        response_format: {type: 'json_object'}})});
    if (!response.ok) { await response.body?.cancel(); throw new Error('PROVIDER_UNAVAILABLE'); }
    const data = await boundedJSON(response);
    const choice = data.choices?.[0];
    if (data.choices?.length !== 1 || choice.finish_reason !== 'stop' ||
        choice.message?.role !== 'assistant' || choice.message.tool_calls?.length ||
        choice.message.refusal || typeof choice.message.content !== 'string') throw new Error('PROVIDER_INVALID');
    return {type: 'final', value: JSON.parse(choice.message.content)};
  }};
}
