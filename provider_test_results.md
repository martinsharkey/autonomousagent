# LLM Provider Gateway Test Results

**Test Date:** 2026-07-26T10:47:24.993946

## Summary

- Total providers: 20
- Successful: 3
- Failed: 1
- Skipped: 15
- Rate Limited: 0
- Timeout: 0
- Error: 1

## Working Providers

- **openrouter** (google/gemma-4-31b-it:free) - 1.29s
- **deepseek** (deepseek-chat) - 0.93s
- **groq** (llama-3.1-8b-instant) - 0.10s

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
- modelscope: No API key (MODELSCOPE_API_KEY)
- nvidia-nim: No API key (NVIDIA_NIM_API_KEY)
- ollama-cloud: No API key (OLLAMA_API_KEY)
- sambanova: No API key (SAMBANOVA_API_KEY)
- siliconflow: No API key (SILICONFLOW_API_KEY)

## Detailed Results

### openrouter
- Status: SUCCESS
- Model: google/gemma-4-31b-it:free
- Response Time: 1.29s

### deepseek
- Status: SUCCESS
- Model: deepseek-chat
- Response Time: 0.93s

### groq
- Status: SUCCESS
- Model: llama-3.1-8b-instant
- Response Time: 0.10s

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
- Response Time: 0.02s
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

