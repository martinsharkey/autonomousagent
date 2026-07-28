from tools.request_batcher import RequestBatcher

# Initialize request batcher
request_batcher = RequestBatcher(max_batch_size=5, max_wait_time=1.0, cache_ttl=300.0)

# Modify the request processing loop to use batching
def process_requests(requests):
    batched_requests = request_batcher.batch_requests(requests)
    results = request_batcher.execute_batched_requests(api_router, batched_requests)
    return results