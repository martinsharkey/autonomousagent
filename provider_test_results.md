# LLM Provider Gateway Test Results

**Test Date:** 2026-07-27T07:27:12.785037

## Summary

- Total providers: 21
- Successful: 2
- Failed: 1
- Skipped: 16
- Rate Limited: 1
- Timeout: 0
- Error: 1

## Working Providers

- **deepseek** (deepseek-chat) - 0.95s
- **groq** (llama-3.1-8b-instant) - 0.18s

## Failed Providers

- **local-ollama**: Ollama not running: All connection attempts failed
- **huggingface**: [Errno 11001] getaddrinfo failed

## Skipped Providers (No API Key)

- deepinfra: No API key (DEEPINFRA_API_KEY)
- togetherai: No API key (TOGETHER_API_KEY)
- aihubmix: No API key (AIHUBMIX_API_KEY)
- bigmodel: No API key (BIGMODEL_API_KEY)
- cerebras: No API key (CEREBRAS_API_KEY)
- cloudflare-workers-ai: No API key (CLOUDFLARE_WORKERS_AI_API_KEY)
- cohere: No API key (COHERE_API_KEY)
- github-models: No API key (GITHUB_TOKEN)
- google-ai-studio: No API key (GOOGLE_API_KEY)
- mistral: No API key (MISTRAL_API_KEY)
- ovh-ai: No API key (OVH_AI_API_KEY)
- modelscope: No API key (MODELSCOPE_API_KEY)
- nvidia-nim: No API key (NVIDIA_NIM_API_KEY)
- ollama-cloud: No API key (OLLAMA_API_KEY)
- sambanova: No API key (SAMBANOVA_API_KEY)
- siliconflow: No API key (SILICONFLOW_API_KEY)

## Detailed Results

### openrouter
- Status: RATE_LIMITED
- Response Time: 0.76s
- Reason: HTTP 429

### deepseek
- Status: SUCCESS
- Model: deepseek-chat
- Response Time: 0.95s

### groq
- Status: SUCCESS
- Model: llama-3.1-8b-instant
- Response Time: 0.18s

### deepinfra
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (DEEPINFRA_API_KEY)

### togetherai
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (TOGETHER_API_KEY)

### huggingface
- Status: ERROR
- Response Time: 0.03s
- Reason: [Errno 11001] getaddrinfo failed

### aihubmix
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (AIHUBMIX_API_KEY)

### bigmodel
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (BIGMODEL_API_KEY)

### cerebras
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (CEREBRAS_API_KEY)

### cloudflare-workers-ai
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (CLOUDFLARE_WORKERS_AI_API_KEY)

### cohere
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (COHERE_API_KEY)

### github-models
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (GITHUB_TOKEN)

### google-ai-studio
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (GOOGLE_API_KEY)

### mistral
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (MISTRAL_API_KEY)

### ovh-ai
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (OVH_AI_API_KEY)

### modelscope
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (MODELSCOPE_API_KEY)

### nvidia-nim
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (NVIDIA_NIM_API_KEY)

### ollama-cloud
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (OLLAMA_API_KEY)

### sambanova
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (SAMBANOVA_API_KEY)

### siliconflow
- Status: SKIPPED
- Response Time: 0.00s
- Reason: No API key (SILICONFLOW_API_KEY)

### local-ollama
- Status: FAILED
- Response Time: 0.00s
- Reason: Ollama not running: All connection attempts failed

