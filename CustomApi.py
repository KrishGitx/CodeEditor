from playwright.sync_api import sync_playwright, expect

import time

def send_msg(textbox):

    msg = input("Enter msg: ")

    textbox.fill(msg)

    textbox.press("Enter")

with sync_playwright() as p :

    browser = p.chromium.launch(headless=False)

    context = browser.new_context(

        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",

        viewport={"width": 1920, "height": 1080},

        locale="en-US",

        timezone_id="Asia/Kolkata"

    )

    page = context.new_page()

    page.goto("https://chatgpt.com/", wait_until="domcontentloaded")

    print(page.title())

    print(page.url)

    textbox = page.get_by_role("textbox", name="Chat with ChatGPT")

    resCount = 1;

    while(1):

        send_msg(textbox)

        stay_logged_out = page.locator('a[href="#"]', has_text="Stay logged out")

        if stay_logged_out.count() > 0:
            stay_logged_out.click()
            
        stable_time = 0
        previous = ""
        
        while True:    
            messages = page.locator('[data-message-role="assistant"], [data-message-author-role="assistant"]')
            
            res = messages.last
            
            try:
                markdown = res.locator(".markdown")

                if markdown.count() > 0:
                    current = markdown.inner_text()
                else:
                    current = res.locator("[data-assistant-markdown]").inner_text()
            except:
                current = ""

            
            if current and current == previous:
                stable_time += 300
            else:
                stable_time = 0

            if current and stable_time >= 1200:
                break

            previous = current
            page.wait_for_timeout(300)
        
        print("Response:", current)
    

    browser.close()