// Pluggable LLM provider layer. Providers implement:
//   chat({system, messages, tools, maxTokens}) -> {content, stopReason, model}
// Start with Anthropic (Claude); add others by dropping in a new provider
// module and setting config.provider.
"use strict";

function getProvider(config) {
  const name = (config.provider || "anthropic").toLowerCase();
  if (name === "anthropic") {
    return require("./provider-anthropic")(config);
  }
  throw new Error(`Unknown LLM provider: ${name}`);
}

module.exports = { getProvider };
