from tools.request_batcher import RequestBatcher

# Initialize request batcher in planning module
request_batcher = RequestBatcher(max_batch_size=5, max_wait_time=1.0, cache_ttl=300.0)

# Modify tool execution to use batching
def execute_tool_calls(tool_calls):
    batched_calls = request_batcher.batch_requests(tool_calls)
    results = request_batcher.execute_batched_requests(api_router, batched_calls)
    return results