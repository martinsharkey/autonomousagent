#!/usr/bin/env python3
"""Multi-provider health check and automatic failover tool."""
import asyncio
import json
import logging
import os
from typing import Dict, List

import aiohttp
import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = os.getenv('PROVIDERS_CONFIG_PATH', 'providers.yaml')


async def check_provider(session: aiohttp.ClientSession, name: str, config: dict) -> dict:
    """Check a single provider's health by sending a minimal test request."""
    endpoint = config.get('health_endpoint') or config.get('base_url', '').rstrip('/') + '/v1/models'
    api_key = config.get('api_key', '')
    headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        async with session.get(endpoint, headers=headers, timeout=timeout) as resp:
            if resp.status < 500:
                return {'provider': name, 'healthy': True, 'status': resp.status}
            else:
                return {'provider': name, 'healthy': False, 'status': resp.status}
    except Exception as e:
        logger.warning(f'Health check failed for {name}: {e}')
        return {'provider': name, 'healthy': False, 'status': -1}


async def run_health_checks() -> List[dict]:
    """Run health checks on all providers defined in providers.yaml."""
    if not os.path.exists(CONFIG_PATH):
        logger.error(f'Provider config not found: {CONFIG_PATH}')
        return []
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    providers = config.get('providers', {})
    if not providers:
        logger.warning('No providers defined in config.')
        return []
    async with aiohttp.ClientSession() as session:
        tasks = [check_provider(session, name, cfg) for name, cfg in providers.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    healthy_results = []
    for r in results:
        if isinstance(r, dict):
            healthy_results.append(r)
        else:
            logger.error(f'Unexpected health check result: {r}')
    return healthy_results


def update_provider_routing(results: List[dict]):
    """Update provider routing table to mark unhealthy providers as disabled."""
    if not os.path.exists(CONFIG_PATH):
        return
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    changed = False
    for r in results:
        name = r['provider']
        healthy = r['healthy']
        if name in config.get('providers', {}):
            current_status = config['providers'][name].get('status', 'active')
            if healthy and current_status != 'active':
                config['providers'][name]['status'] = 'active'
                changed = True
                logger.info(f'Provider {name} marked active.')
            elif not healthy and current_status != 'disabled':
                config['providers'][name]['status'] = 'disabled'
                changed = True
                logger.info(f'Provider {name} marked disabled due to health check failure.')
    if changed:
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        logger.info('Provider routing table updated.')


async def main():
    """Main entry point for the health check tool."""
    results = await run_health_checks()
    update_provider_routing(results)
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
