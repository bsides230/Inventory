import json
from pathlib import Path


def test_manifest_contains_required_pwa_fields_and_icons():
    manifest = json.loads(Path('web/manifest.json').read_text(encoding='utf-8'))

    assert manifest['display'] == 'standalone'
    assert manifest['scope'] == '/'
    assert manifest['start_url'].startswith('/')

    icon_sources = {icon['src'] for icon in manifest['icons']}
    assert '/assets/icon-192.png' in icon_sources
    assert '/assets/icon-512.png' in icon_sources


def test_service_worker_uses_expected_cache_strategies():
    sw_text = Path('web/sw.js').read_text(encoding='utf-8')

    assert 'STATIC_CACHE' in sw_text
    assert 'API_CACHE' in sw_text
    assert "requestUrl.pathname.startsWith('/api/')" in sw_text
    assert 'const cached = await caches.match(request);' in sw_text
    assert 'return cached || offlineApiResponse();' in sw_text


def test_frontend_includes_install_offline_and_update_prompts():
    app_text = Path('web/app.js').read_text(encoding='utf-8')
    index_text = Path('web/index.html').read_text(encoding='utf-8')

    assert 'beforeinstallprompt' in app_text
    assert 'offlineBanner' in app_text
    assert 'updateBanner' in app_text
    assert "postMessage({ type: 'SKIP_WAITING' })" in app_text

    assert 'id="installBanner"' in index_text
    assert 'id="iosInstallBanner"' in index_text
    assert 'id="updateBanner"' in index_text
