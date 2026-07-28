def get_provider(provider_name):
  if provider_name == 'google_cloud':
    return GoogleCloudProvider()
  # ... existing code