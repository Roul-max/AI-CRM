import { useState } from 'react';
import { useDispatch } from 'react-redux';
import { setInteractionData, InteractionData } from '../store/interactionSlice';
import { addToast, setExtracting } from '../store/slices/uiSlice';
import { AppDispatch } from '../store/index';

export type StreamPhase = 'idle' | 'thinking' | 'tool' | 'extracting' | 'streaming';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
}

const TOOL_LABELS: Record<string, string> = {
  log_interaction: 'Extracting interaction details',
  edit_interaction: 'Applying corrections',
  search_hcp: 'Searching HCP records',
  meeting_summary: 'Generating meeting summary',
  follow_up_recommendation: 'Generating follow-up recommendations',
};

export const useChatStream = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content:
        'Hello! I am your AI HCP CRM Assistant.\n\nDescribe your meeting with a Healthcare Professional and I will extract all the details automatically.\n\nYou can also ask me to:\n• Search for an HCP\n• Generate a meeting summary\n• Get follow-up recommendations\n• Correct any extracted details',
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [phase, setPhase] = useState<StreamPhase>('idle');
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const dispatch = useDispatch<AppDispatch>();

  const sendMessage = async (messageContent: string) => {
    if (!messageContent.trim()) return;

    setIsLoading(true);
    setPhase('thinking');
    setActiveTool(null);
    setError(null);

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageContent,
    };

    const assistantMessageId = (Date.now() + 1).toString();

    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantMessageId, role: 'assistant', content: '', isStreaming: true },
    ]);

    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageContent, history }),
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      const reader = response.body?.getReader();
      if (!reader) throw new Error('Failed to get stream reader');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.substring(6));

            if (data.type === 'token') {
              setPhase('streaming');
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, content: msg.content + data.content }
                    : msg
                )
              );
            } else if (data.type === 'tool_start') {
              const isExtraction = data.name === 'log_interaction' || data.name === 'edit_interaction';
              setPhase(isExtraction ? 'extracting' : 'tool');
              setActiveTool(data.name);
              if (isExtraction) dispatch(setExtracting(true));
              const label = TOOL_LABELS[data.name] ?? `Running ${data.name}`;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId ? { ...msg, content: label + '…' } : msg
                )
              );
            } else if (data.type === 'tool_end') {
              const toolName: string = data.name;
              const output = data.output;
              setActiveTool(null);
              dispatch(setExtracting(false));

              if ((toolName === 'log_interaction' || toolName === 'edit_interaction') && output) {
                try {
                  const parsed: InteractionData =
                    typeof output === 'string' ? JSON.parse(output) : output;
                  dispatch(setInteractionData(parsed));
                  dispatch(addToast({ type: 'success', message: toolName === 'log_interaction' ? 'Interaction extracted and populated.' : 'Corrections applied.' }));
                  const confirmMsg =
                    toolName === 'log_interaction'
                      ? '✅ Interaction details extracted and populated in the form on the left.'
                      : '✅ Interaction updated with your corrections.';
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMessageId ? { ...msg, content: confirmMsg } : msg
                    )
                  );
                } catch {
                  // output was not valid JSON — leave as-is
                }
              } else if (toolName === 'search_hcp' && output) {
                try {
                  const results = typeof output === 'string' ? JSON.parse(output) : output;
                  const text =
                    Array.isArray(results) && results.length > 0
                      ? `🔎 Found ${results.length} HCP(s):\n` +
                        results.map((r: any) => `• ${r.name} (${r.specialty ?? 'N/A'}) — ${r.interactions?.length ?? 0} past interaction(s)`).join('\n')
                      : '🔎 No HCPs found matching your search.';
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMessageId ? { ...msg, content: text } : msg
                    )
                  );
                } catch { /* ignore */ }
              } else if (toolName === 'meeting_summary' && output) {
                try {
                  const s = typeof output === 'string' ? JSON.parse(output) : output;
                  const concernsLine = s.concerns_raised?.length
                    ? `\nConcerns Raised:\n${s.concerns_raised.map((c: string) => `• ${c}`).join('\n')}`
                    : '';
                  const followUpLine = s.follow_up ? `\n\nFollow-up: ${s.follow_up}` : '';
                  const text =
                    `📋 Meeting Summary\n` +
                    `HCP: ${s.hcp ?? 'N/A'}\n` +
                    `Objective: ${s.objective ?? 'N/A'}\n\n` +
                    `Discussion Points:\n${(s.discussion_points ?? []).map((p: string) => `• ${p}`).join('\n')}\n\n` +
                    `Products Discussed: ${(s.products_discussed ?? []).join(', ') || 'None'}` +
                    concernsLine +
                    `\n\nOutcomes: ${s.outcomes ?? 'N/A'}\n\n` +
                    `Action Items:\n${(s.action_items ?? []).map((a: string) => `• ${a}`).join('\n')}` +
                    followUpLine;
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMessageId ? { ...msg, content: text } : msg
                    )
                  );
                } catch { /* ignore */ }
              } else if (toolName === 'follow_up_recommendation' && output) {
                try {
                  const rec = typeof output === 'string' ? JSON.parse(output) : output;
                  const materialsLine = rec.materials_to_send?.length
                    ? `\nMaterials to Send:\n${rec.materials_to_send.map((m: string) => `• ${m}`).join('\n')}`
                    : '';
                  const text =
                    `📅 Follow-Up Recommendation\n` +
                    `Priority: ${rec.priority ?? 'N/A'} | Risk: ${rec.risk_level ?? 'N/A'} | Samples: ${rec.samples_required === true ? 'Yes' : rec.samples_required === false ? 'No' : 'N/A'}\n` +
                    `Suggested Date: ${rec.suggested_follow_up_date ?? 'N/A'}\n\n` +
                    `Discussion Topics:\n${(rec.discussion_topics ?? []).map((t: string) => `• ${t}`).join('\n')}` +
                    materialsLine +
                    `\n\nReasoning: ${rec.reasoning ?? ''}`;
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMessageId ? { ...msg, content: text } : msg
                    )
                  );
                } catch { /* ignore */ }
              }
            }
          } catch {
            // skip malformed SSE lines
          }
        }
      }
    } catch (e: any) {
      const errMsg = e.message || 'Failed to connect to AI backend';
      setError(errMsg);
      dispatch(addToast({ type: 'error', message: errMsg }));
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, content: `❌ Error: ${errMsg}`, isStreaming: false }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
      setPhase('idle');
      setActiveTool(null);
      dispatch(setExtracting(false));
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
        )
      );
    }
  };

  return { messages, isLoading, phase, activeTool, error, sendMessage };
};
