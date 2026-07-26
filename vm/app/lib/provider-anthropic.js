// Anthropic (Claude) provider.
// Uses the official SDK, claude-opus-5 by default, with server-side refusal
// fallbacks enabled so a safety-classifier decline is transparently re-served
// by Anthropic's recommended fallback model instead of failing the request.
"use strict";

const Anthropic = require("@anthropic-ai/sdk");

module.exports = function anthropicProvider(config) {
  const client = new Anthropic({ apiKey: config.apiKey });
  const model = config.model || "claude-opus-5";

  return {
    name: "anthropic",
    model,
    async chat({ system, messages, tools, maxTokens = 16000 }) {
      const response = await client.beta.messages.create({
        model,
        max_tokens: maxTokens,
        betas: ["server-side-fallback-2026-07-01"],
        fallbacks: "default",
        system,
        messages,
        tools,
      });
      return {
        content: response.content,
        stopReason: response.stop_reason,
        stopDetails: response.stop_details || null,
        model: response.model,
        usage: response.usage,
      };
    },
  };
};
