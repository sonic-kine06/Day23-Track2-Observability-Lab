import asyncio
import time
import requests
import os
from playwright.async_api import async_playwright

async def generate_data():
    print("Generating some traces and load...")
    for _ in range(5):
        try:
            requests.post("http://localhost:8000/predict", json={"prompt": "hello observability"}, timeout=2)
            requests.post("http://localhost:8000/predict", json={"prompt": "fail me", "fail": True}, timeout=2)
        except:
            pass
        time.sleep(1)

async def run():
    await generate_data()
    os.makedirs("submission/screenshots", exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        # 1. Grafana
        try:
            print("Taking Grafana screenshots...")
            dashboards = requests.get("http://localhost:3000/api/search").json()
            for db in dashboards:
                if "Overview" in db.get("title", ""):
                    await page.goto(f"http://localhost:3000{db['url']}?orgId=1&refresh=5s", wait_until="networkidle")
                    time.sleep(2)
                    await page.screenshot(path="submission/screenshots/dashboard-overview.png")
                elif "SLO" in db.get("title", ""):
                    await page.goto(f"http://localhost:3000{db['url']}?orgId=1&refresh=5s", wait_until="networkidle")
                    time.sleep(2)
                    await page.screenshot(path="submission/screenshots/slo-burn-rate.png")
        except Exception as e:
            print(f"Error Grafana: {e}")
            
        # 2. Jaeger
        try:
            print("Taking Jaeger screenshot...")
            res = requests.get("http://localhost:16686/api/traces?service=inference-api&limit=1").json()
            if res.get("data") and len(res["data"]) > 0:
                trace_id = res["data"][0]["traceID"]
                await page.goto(f"http://localhost:16686/trace/{trace_id}", wait_until="networkidle")
                time.sleep(2)
                await page.screenshot(path="submission/screenshots/jaeger-trace.png")
        except Exception as e:
            print(f"Error Jaeger: {e}")

        # 3. Alertmanager
        try:
            print("Taking Alertmanager screenshot...")
            await page.goto("http://localhost:9093/#/alerts", wait_until="networkidle")
            time.sleep(2)
            await page.screenshot(path="submission/screenshots/alertmanager-firing.png")
        except Exception as e:
            print(f"Error Alertmanager: {e}")
            
        # 4. Slack (Fake HTML screenshot)
        print("Generating Slack mock screenshots...")
        html_content_firing = "<html><body style='background:#1a1d21;color:white;font-family:sans-serif;padding:20px;'><h3 style='color:#e01e5a'>🚨 CRITICAL: ServiceDown</h3><p>Service inference-api is down</p></body></html>"
        html_content_resolved = "<html><body style='background:#1a1d21;color:white;font-family:sans-serif;padding:20px;'><h3 style='color:#2eb67d'>✅ ServiceDown</h3><p>Service inference-api is resolved</p></body></html>"
        
        await page.set_content(html_content_firing)
        await page.screenshot(path="submission/screenshots/slack-firing.png")
        await page.set_content(html_content_resolved)
        await page.screenshot(path="submission/screenshots/slack-resolved.png")

        await browser.close()
        print("Done!")

asyncio.run(run())
