import json
import urllib.parse
from datetime import datetime
from typing import Dict, Any

def generate_vless_link(uuid: str, base_host: str, port: int, email: str, stream_settings_str: str) -> str:
    """
    Consolidated logic for generating a VLESS Reality link.
    """
    stream_settings = json.loads(stream_settings_str or '{}')
    reality_settings = stream_settings.get('realitySettings', {})
    pbk = reality_settings.get('settings', {}).get('publicKey', '')
    sid = reality_settings.get('shortIds', [''])[0] 
    fp = reality_settings.get('settings', {}).get('fingerprint', 'random')
    spx = reality_settings.get('settings', {}).get('spiderX', '/')
    sni = reality_settings.get('serverNames', [''])[0]
    
    name_encoded = urllib.parse.quote(f"🇩🇪 reality-{email}") 
    
    vless_link = (
        f"vless://{uuid}@{base_host}:{port}?"
        f"type=tcp&encryption=none&security=reality&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&spx={spx}&flow=xtls-rprx-vision"
        f"#{name_encoded}"
    )
    return vless_link

def get_subscription_link(base_host: str, email: str) -> str:
    """
    Generates the subscription link.
    """
    return f"https://{base_host}/egcPsGWuDm/{email}"
