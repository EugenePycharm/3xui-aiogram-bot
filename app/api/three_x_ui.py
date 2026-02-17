import aiohttp
import json
import uuid
from typing import Optional, Dict, Any, Tuple

class ThreeXUIClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        if not self.session:
            # Use unsafe=True to accept cookies from IP addresses
            jar = aiohttp.CookieJar(unsafe=True)
            self.session = aiohttp.ClientSession(cookie_jar=jar)

    async def login(self) -> bool:
        """
        Authenticate with the 3x-ui panel.
        Returns True if successful, False otherwise.
        """
        await self._ensure_session()
        payload = {
            "username": self.username,
            "password": self.password
        }
        try:
            async with self.session.post(f"{self.base_url}/login", data=payload) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        if data.get('success'):
                            return True
                    except aiohttp.ContentTypeError:
                        pass
                    
                    cookies = self.session.cookie_jar.filter_cookies(self.base_url)
                    if len(cookies) > 0:
                        return True
                
                return False
        except Exception as e:
            print(f"Login exception: {e}")
            return False

    async def get_inbounds(self) -> Dict[str, Any]:
        """
        Fetch list of inbounds.
        """
        await self._ensure_session()
        # Correct path found via debugging: /panel/api/inbounds/list (plural 'inbounds')
        url = f"{self.base_url}/panel/api/inbounds/list"
        
        async with self.session.get(url) as resp:
            try:
                if resp.status != 200:
                     return {"success": False, "msg": f"Status {resp.status}"}
                return await resp.json()
            except aiohttp.ContentTypeError:
                return {"success": False, "msg": f"Invalid Content-Type at {url}. Status: {resp.status}"}

    async def add_client(self, inbound_id: int, email: str, total_gb: int = 0, expiry_time: int = 0, enable: bool = True, sub_id: str = "") -> Tuple[bool, str, str]:
        """
        Add a new client to the specified inbound.
        Refined in debug: The main path is /panel/api/inbounds/addClient (plural 'inbounds')
        """
        await self._ensure_session()
        
        client_uuid = str(uuid.uuid4())
        
        # 3x-ui client structure
        client_data = {
            "id": client_uuid,
            "flow": "xtls-rprx-vision", 
            "email": email,
            "limitIp": 0,
            "totalGB": int(total_gb * 1024 * 1024 * 1024),
            "expiryTime": expiry_time,
            "enable": enable,
            "tgId": "",
            "subId": sub_id
        }

        settings = json.dumps({
            "clients": [client_data]
        })
        
        payload = {
            "id": inbound_id,
            "settings": settings
        }

        # Try plural 'inbounds' path first as listing worked with plural
        url = f"{self.base_url}/panel/api/inbounds/addClient"
        
        try:
            async with self.session.post(url, json=payload) as resp:
                if resp.status == 404:
                    # Fallback to singular
                    url = f"{self.base_url}/panel/api/inbound/addClient"
                    async with self.session.post(url, json=payload) as resp2:
                         try:
                            data = await resp2.json()
                            return data.get('success', False), data.get('msg', ''), client_uuid
                         except:
                            return False, f"Status {resp2.status} at {url}", client_uuid

                try:
                    data = await resp.json()
                    success = data.get('success', False)
                    msg = data.get('msg', '')
                    return success, msg, client_uuid
                except:
                     return False, f"Invalid JSON. Status {resp.status}", client_uuid

        except Exception as e:
            return False, str(e), client_uuid

    async def update_client(self, inbound_id: int, client_uuid: str, email: str, total_gb: int, expiry_time: int, enable: bool, sub_id: str) -> bool:
        """
        Update an existing client.
        Path: /panel/api/inbounds/updateClient/{client_uuid}
        """
        await self._ensure_session()
        
        client_data = {
            "id": client_uuid,
            "flow": "xtls-rprx-vision",
            "email": email,
            "limitIp": 0,
            "totalGB": int(total_gb * 1024 * 1024 * 1024),
            "expiryTime": expiry_time,
            "enable": enable,
            "tgId": "",
            "subId": sub_id
        }
        
        settings = json.dumps({
            "clients": [client_data]
        })
        
        payload = {
            "id": inbound_id,
            "settings": settings
        }
        
        url = f"{self.base_url}/panel/api/inbounds/updateClient/{client_uuid}"
        
        try:
            async with self.session.post(url, json=payload) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        return data.get('success', False)
                    except: pass
        except Exception as e:
            print(f"Update client exception: {e}")
            pass
            
        return False

    async def delete_client(self, inbound_id: int, client_uuid: str) -> bool:
        """
        Delete a client from an inbound.
        Tries multiple paths for compatibility.
        """
        await self._ensure_session()
        
        # Path 1: /panel/api/inbounds/{inbound_id}/delClient/{client_uuid}
        url = f"{self.base_url}/panel/api/inbounds/{inbound_id}/delClient/{client_uuid}"
        try:
            async with self.session.post(url) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        if data.get('success'): return True
                    except: pass
        except: pass
        
        # Path 2: /panel/api/inbound/delClient/{inbound_id}/client/{client_uuid} (Some versions)
        # Not implementing complex fallback yet, usually path 1 works for 3x-ui
        return False


    async def close(self):
        if self.session:
            await self.session.close()
