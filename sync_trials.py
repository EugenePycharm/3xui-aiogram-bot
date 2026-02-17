import asyncio
import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import selectinload

sys.path.append(os.getcwd())
load_dotenv()

from app.database.models import async_session, Subscription, Server, Plan
from app.api.three_x_ui import ThreeXUIClient

async def sync_trials():
    print("Starting trial synchronization...")
    
    async with async_session() as session:
        # 1. Fetch Active Server
        server = await session.scalar(select(Server).where(Server.is_active == True))
        if not server:
            print("No active server found.")
            return

        print(f"Connecting to server {server.api_url}...")
        client = ThreeXUIClient(server.api_url, server.username, server.password)
        
        if not await client.login():
            print("Login failed.")
            await client.close()
            return

        # 2. Fetch Trial Plan to know limits
        stmt_plan = select(Plan).where(Plan.price == 0)
        trial_plan = await session.scalar(stmt_plan)
        if not trial_plan:
             print("Trial plan not found in DB.")
             await client.close()
             return

        # 3. Fetch All Trial Subscriptions
        stmt = select(Subscription).options(selectinload(Subscription.plan)).where(Subscription.plan_id == trial_plan.id)
        result = await session.execute(stmt)
        subs = result.scalars().all()
        
        print(f"Found {len(subs)} trial subscriptions to sync.")
        
        updated_count = 0
        
        for sub in subs:
            print(f"Updating trial sub {sub.id} ({sub.email})...")
            
            # Calculate expiry (from sub.expires_at or now if missing)
            if not sub.expires_at:
                sub.expires_at = datetime.now() + timedelta(days=7)
                
            expiry_time = int(sub.expires_at.timestamp() * 1000)
            limit_gb = trial_plan.data_limit_gb
            
            # Update Client in 3x-ui
            success = await client.update_client(
                inbound_id=sub.inbound_id,
                client_uuid=sub.uuid,
                email=sub.email,
                total_gb=limit_gb,
                expiry_time=expiry_time,
                enable=True,
                sub_id=sub.email
            )
            
            if success:
                print(f"  Success.")
                updated_count += 1
            else:
                print(f"  Failed.")

        await session.commit()
        await client.close()
        print(f"Successfully synced {updated_count} trial subscriptions.")

if __name__ == "__main__":
    asyncio.run(sync_trials())
