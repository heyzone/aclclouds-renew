import os
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    raw_cookies = os.environ.get('ACL_COOKIES', '')
    if not raw_cookies:
        print("错误: 未找到 ACL_COOKIES 环境变量。")
        browser.close()
        return

    # 解析 Cookie
    cookies = []
    for item in raw_cookies.split(';'):
        item = item.strip()
        if '=' in item:
            name, value = item.split('=', 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": "dash.aclclouds.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
            })

    print(f"解析到 {len(cookies)} 个 Cookie")

    page = context.new_page()

    try:
        # ✅ 关键修复：先访问域名根页面，让浏览器完成初始化
        print("预热：访问主域名...")
        page.goto("https://dash.aclclouds.com/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        # ✅ 在页面已加载后注入 Cookie
        context.add_cookies(cookies)
        print("Cookie 注入完成")

        # ✅ 带着 Cookie 重新访问目标页
        print("正在访问项目面板...")
        page.goto("https://dash.aclclouds.com/projects", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)

        # 检查是否真的登录成功（如果又回到了 /login 说明 Cookie 还是无效）
        current_url = page.url
        print(f"当前页面 URL: {current_url}")
        if "login" in current_url or "signin" in current_url:
            print("❌ Cookie 未生效，仍被重定向到登录页！请重新获取 Cookie。")
            page.screenshot(path="debug_page.png", full_page=True)
            return

        print("✅ 登录成功，已进入项目面板")
        page.screenshot(path="debug_page.png", full_page=True)

        # 查找续期按钮（兼容多语言）
        renew_locators = [
            "text='Renouveler'",   # 法语
            "text='Renew'",        # 英语
            "text='续期'",
        ]

        renew_buttons = None
        for loc in renew_locators:
            candidate = page.locator(loc)
            if candidate.count() > 0:
                renew_buttons = candidate
                print(f"找到续期按钮，使用定位器: {loc}")
                break

        if renew_buttons is None or renew_buttons.count() == 0:
            print("未找到任何续期按钮，请查看截图确认页面内容。")
        else:
            count = renew_buttons.count()
            print(f"共找到 {count} 个续期按钮，开始点击...")
            for i in range(count):
                button = renew_buttons.nth(i)
                if button.is_visible():
                    button.scroll_into_view_if_needed()
                    button.click()
                    print(f"✅ 已点击第 {i+1} 个续期按钮")
                    page.wait_for_timeout(3000)

            page.screenshot(path="debug_page_after_click.png", full_page=True)
            print("续期操作完成，结果截图已保存。")

        print("任务执行完毕。")

    except Exception as e:
        print(f"执行过程中发生错误: {e}")
        page.screenshot(path="error_page.png", full_page=True)
    finally:
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
